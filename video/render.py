"""Render scene.html to a 2560x1440 / 60fps video with true sub-frame motion blur.

Each output frame averages SUBFRAMES screenshots spread across a 180-degree shutter,
so fast moves (whip pans, the ball, the odometer) smear exactly like camera blur.

  python3 render.py --stills 1.5,5,9.9          # quick PNG previews
  python3 render.py                             # full render -> out/video_only.mp4
"""
import argparse, io, os, subprocess, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FPS, W, H = 60, 2560, 1440
SCALE = W / 1920            # scene is laid out at 1920x1080 CSS px
SHUTTER = 0.5               # 180-degree shutter
CHROMIUM = os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def open_page(p):
    browser = p.chromium.launch(executable_path=CHROMIUM if Path(CHROMIUM).exists() else None,
                                args=["--force-color-profile=srgb", "--font-render-hinting=none"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=SCALE)
    page.goto((HERE / "scene.html").as_uri())
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(400)  # let optional assets/ images settle
    return browser, page


def grab(page, t):
    page.evaluate(f"seek({t:.6f})")
    png = page.screenshot(type="png", animations="disabled", caret="hide")
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))


def render_chunk(args):
    idx, f0, f1, sub = args
    seg = OUT / f"seg_{idx:02d}.mp4"
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "12",
         "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(seg)],
        stdin=subprocess.PIPE)
    with sync_playwright() as p:
        browser, page = open_page(p)
        for f in range(f0, f1):
            acc = np.zeros((H, W, 3), np.float32)
            for s in range(sub):
                # sample the open-shutter interval centred on the frame time
                t = max(0.0, (f + ((s + 0.5) / sub - 0.5) * SHUTTER) / FPS)
                acc += grab(page, t)
            frame = acc / sub
            # light ordered dither so averaged gradients don't band
            frame += np.random.default_rng(f).uniform(-0.5, 0.5, frame.shape).astype(np.float32)
            enc.stdin.write(np.clip(frame + 0.5, 0, 255).astype(np.uint8).tobytes())
            if (f - f0) % 60 == 0:
                print(f"[w{idx}] frame {f}/{f1}", flush=True)
        browser.close()
    enc.stdin.close(); enc.wait()
    return seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", help="comma-separated times to preview as PNG")
    ap.add_argument("--sub", type=int, default=6, help="motion-blur subframes per frame")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    if a.stills:
        with sync_playwright() as p:
            browser, page = open_page(p)
            for t in a.stills.split(","):
                Image.fromarray(grab(page, float(t))).save(OUT / f"still_{float(t):06.2f}.png")
            browser.close()
        return

    with sync_playwright() as p:
        browser, page = open_page(p)
        dur = page.evaluate("DURATION")
        browser.close()
    f0, f1 = int(a.start * FPS), int((a.end or dur) * FPS)
    n = a.workers
    bounds = [f0 + (f1 - f0) * i // n for i in range(n + 1)]
    with Pool(n) as pool:
        segs = pool.map(render_chunk, [(i, bounds[i], bounds[i + 1], a.sub) for i in range(n)])
    (OUT / "segs.txt").write_text("".join(f"file '{s.name}'\n" for s in segs))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "segs.txt"),
                    "-c", "copy", str(OUT / "video_only.mp4")], check=True)
    for s in segs:
        s.unlink()
    print("wrote", OUT / "video_only.mp4")


if __name__ == "__main__":
    sys.exit(main())
