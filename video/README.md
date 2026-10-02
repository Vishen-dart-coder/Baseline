# technomadenviro — brand film

A 49-second, 2560×1440 / 60 fps film for [technomadenviro.com](https://technomadenviro.com/), built from the site itself.

## Built from the site

| Area | Source |
|---|---|
| **Copy** | Every on-screen line comes verbatim from `index.html` and `script.js` on the live site: hero, ZLD/MEP trust cards, capability carousel, consultancy services, design scope, systems in scope, project support and the footer CTA. |
| **Colours** | The site's `:root` tokens only: `#0f2f63` brand-deep, `#2563c9` brand, `#5790e6` brand-light, `#0b6e97` teal, `#f4f4f4` surface, `#0a0a0a` ink, `#717784` ink-soft, plus the ghost and hairline greys. |
| **Type** | Onest 400/500, the site's font. Uppercase hero and ghost headlines, sentence-case `h-stack`s, tracking and radii as in `style.css`. |
| **Footage** | The site's own 4K drone hero loop and its photography (`assets/`). |
| **Motion** | The site's own motion system: loader wipe-up, clip reveals on `cubic-bezier(.16,1,.3,1)`, `mkSpring` tension/friction pairs solved in closed form, word fades, and scroll-style section changes. |

## Pipeline

```
scene.html   timeline: seek(t) renders any instant deterministically
render.py    Chromium @ 2560x1440, 6 sub-frames per frame over a 180° shutter -> real motion blur
audio.py     voiceover chain + music bed (ducked under voice) + UI sound design -> -14 LUFS mix
mux.sh       picture + mix -> out/technomadenviro-film-2k60.mp4
tts/         offline narration: Kokoro-82M fp32, American female voice (af_heart)
```

```bash
pip install playwright pillow numpy scipy soundfile pyloudnorm
# hero frames from the site's 4K loop
curl -o out/technomad-hero-4k.mp4 https://technomadenviro.com/assets/video/technomad-hero-4k.mp4
ffmpeg -i out/technomad-hero-4k.mp4 -t 13.4 -vf scale=2560:-2:flags=lanczos -q:v 2 out/hero/f_%04d.jpg

python3 render.py --stills 5,14.5,36   # quick previews
python3 render.py                      # full render (sub-frames: --sub 6)
python3 audio.py
./mux.sh
```

## Sound effects

All SFX are synthesized in `audio.py`. To use a licensed pack (for example Apple sounds you have rights to), drop WAVs into `sfx/` with these names; each one replaces its synthesized version automatically:

`tick` · `pop` · `click` · `whoosh` · `swish` · `boom` · `chime` · `riser` · `shimmer`

## Voice

`tts/generate.mjs` runs Kokoro-82M (fp32 ONNX) through `kokoro-js` with no network access. It refuses any voice that is not American female (`af_*`). The script is in `tts/script.json`. Change a line there, regenerate, then adjust `VO_STARTS` in `audio.py` if a line's length changes.
