"""Render an HTML timeline (seek(t) + DURATION) to video with true sub-frame motion blur.

Each output frame averages --sub screenshots spread across a 180-degree shutter, so fast
moves smear like camera blur. Work is split into short chunks pulled from a shared queue:
every chunk is finalized to its own file the moment it finishes (written to a temp name,
then renamed), finished chunks are skipped on a rerun, and the final join checks that every
frame is present exactly once.

  python3 render.py ad/ad.html --stills 1.5,5,9.9          # PNG previews
  python3 render.py ad/ad.html --width 960 --sub 2         # fast draft
  python3 render.py ad/ad.html                             # final, 2560x1440 @ 60fps
"""
import argparse, io, os, subprocess, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FPS = 60
SHUTTER = 0.5               # 180-degree shutter
CHROMIUM = os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def open_page(p, scene, width):
    browser = p.chromium.launch(executable_path=CHROMIUM if Path(CHROMIUM).exists() else None,
                                args=["--force-color-profile=srgb", "--font-render-hinting=none"])
    # scenes are laid out at 1920x1080 CSS px and scaled to the output width
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=width / 1920)
    page.goto(Path(scene).resolve().as_uri())
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(400)
    return browser, page


def grab(page, t):
    page.evaluate(f"seek({t:.6f})")          # seek() returns a promise for pending image decodes
    png = page.screenshot(type="png", animations="disabled", caret="hide")
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))


def count_frames(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v",
                          "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True)
    return int(out.stdout.strip() or 0)


def render_chunk(job):
    scene, width, sub, f0, f1, path, crf = job
    w, h = width, width * 9 // 16
    tmp = path.with_suffix(".part.mp4")
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
         "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(tmp)],
        stdin=subprocess.PIPE)
    with sync_playwright() as p:
        browser, page = open_page(p, scene, width)
        for f in range(f0, f1):
            acc = np.zeros((h, w, 3), np.float32)
            for s in range(sub):
                t = max(0.0, (f + ((s + 0.5) / sub - 0.5) * SHUTTER) / FPS)
                acc += grab(page, t)
            frame = acc / sub + np.random.default_rng(f).uniform(-0.5, 0.5, (h, w, 3)).astype(np.float32)
            enc.stdin.write(np.clip(frame + 0.5, 0, 255).astype(np.uint8).tobytes())
        browser.close()
    enc.stdin.close()
    if enc.wait() != 0 or count_frames(tmp) != f1 - f0:
        raise RuntimeError(f"chunk {f0}-{f1} failed")
    tmp.rename(path)
    return f0, f1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene", nargs="?", default=str(HERE / "scene.html"))
    ap.add_argument("--stills", help="comma-separated times to preview as PNG")
    ap.add_argument("--width", type=int, default=2560, help="output width (16:9); 2560 = 2K")
    ap.add_argument("--sub", type=int, default=6, help="motion-blur subframes per frame")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--chunk", type=int, default=30, help="frames per chunk")
    ap.add_argument("--crf", type=int, default=12)
    ap.add_argument("--name", help="output name (default: scene name + size)")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    scene = str(Path(a.scene).resolve())
    name = a.name or f"{Path(scene).stem}_{a.width}"

    if a.stills:
        with sync_playwright() as p:
            browser, page = open_page(p, scene, a.width)
            for t in a.stills.split(","):
                Image.fromarray(grab(page, float(t))).save(OUT / f"{Path(scene).stem}_still_{float(t):06.2f}.png")
            browser.close()
        return

    with sync_playwright() as p:
        browser, page = open_page(p, scene, a.width)
        total = round(page.evaluate("DURATION") * FPS)
        browser.close()

    chunks = OUT / f"{name}_chunks"
    chunks.mkdir(exist_ok=True)
    jobs = []
    for f0 in range(0, total, a.chunk):
        f1 = min(total, f0 + a.chunk)
        path = chunks / f"{f0:05d}-{f1:05d}.mp4"
        if not (path.exists() and count_frames(path) == f1 - f0):
            jobs.append((scene, a.width, a.sub, f0, f1, path, a.crf))
    print(f"{total} frames, {len(jobs)} chunks to render", flush=True)
    with Pool(a.workers) as pool:
        for i, (f0, f1) in enumerate(pool.imap_unordered(render_chunk, jobs), 1):
            print(f"chunk {i}/{len(jobs)} done ({f0}-{f1})", flush=True)

    parts = sorted(chunks.glob("*-*.mp4"), key=lambda q: int(q.name.split("-")[0]))
    parts = [q for q in parts if not q.name.endswith(".part.mp4")]
    cur = 0
    for q in parts:
        f0, f1 = (int(x) for x in q.stem.split("-"))
        assert f0 == cur, f"gap or overlap at frame {cur} ({q.name})"
        cur = f1
    assert cur == total, f"covered {cur} of {total} frames"
    (chunks / "list.txt").write_text("".join(f"file '{q.name}'\n" for q in parts))
    video = OUT / f"{name}_video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(chunks / "list.txt"),
                    "-c", "copy", str(video)], check=True)
    n = count_frames(video)
    assert n == total, f"joined video has {n} frames, expected {total}"
    print(f"wrote {video} ({n} frames)")


if __name__ == "__main__":
    sys.exit(main())
