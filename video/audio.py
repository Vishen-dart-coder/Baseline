"""Sound for the technomadenviro film: voiceover, music bed and UI sound design.

Every SFX is synthesized here, but any file dropped into sfx/ with the same name
(tick.wav, pop.wav, whoosh.wav, swish.wav, boom.wav, click.wav, chime.wav,
riser.wav, shimmer.wav) replaces the synthesized one, so licensed SFX packs
slot straight in.

  python3 audio.py   -> out/mix.wav (48 kHz stereo, -14 LUFS, -1 dBTP)
"""
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
SR = 48000
DUR = 49.0
rng = np.random.default_rng(7)

# Voiceover lines (vo/NN.wav) and where they start, in seconds — matches scene.html.
VO_STARTS = [0.45, 3.1, 12.5, 16.0, 22.8, 26.9, 31.5, 37.5, 41.9]


def t_(d):
    return np.arange(int(d * SR)) / SR


def env(n, a, r, shape=4.0):
    """Fast attack, exponential release."""
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-shape * np.maximum(0, t - a) / max(r, 1e-4))


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "high", fs=SR, output="sos"), x)


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def reverb_ir(seconds=2.2, decay=3.2, bright=6000):
    n = int(seconds * SR)
    ir = rng.standard_normal((n, 2)) * np.exp(-decay * np.arange(n) / SR)[:, None]
    ir = np.stack([lp(ir[:, c], bright) for c in range(2)], 1)
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))[:, None]   # pre-delay feel
    return ir / np.sqrt(np.sum(ir ** 2))


IR = reverb_ir()


def verb(x, wet=0.25):
    x2 = x if x.ndim == 2 else np.stack([x, x], 1)
    w = np.stack([signal.fftconvolve(x2[:, c], IR[:, c])[: len(x2)] for c in range(2)], 1)
    return x2 * (1 - wet) + w * wet


# ---------------------------------------------------------------- synthesized SFX
def s_tick():       # crisp glassy UI tick
    t = t_(0.09)
    x = (np.sin(2 * np.pi * 3100 * t) + .5 * np.sin(2 * np.pi * 4650 * t)) * env(len(t), .0006, .018)
    x += bp(rng.standard_normal(len(t)), 2500, 9000) * env(len(t), .0003, .004) * .5
    return norm(x, .5)


def s_pop():        # soft bubble pop for spring entrances
    t = t_(0.14)
    f = 520 + 520 * (1 - np.exp(-t * 60))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), .002, .045)
    return norm(x, .55)


def s_click():      # button press
    t = t_(0.06)
    x = bp(rng.standard_normal(len(t)), 1200, 6000) * env(len(t), .0004, .006)
    x += np.sin(2 * np.pi * 180 * t) * env(len(t), .001, .02) * .8
    return norm(x, .6)


def s_whoosh(d=0.95, lo=250, hi=5000, peak=0.6):   # filtered-air sweep for scroll moves
    n = int(d * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    hop = 512
    for i in range(0, n, hop):                       # time-varying band-pass
        p = i / n
        fc = lo * (hi / lo) ** np.sin(np.pi * min(1, p / peak) / 2) if p < peak else hi * (lo / hi) ** ((p - peak) / (1 - peak))
        seg = noise[i:i + hop * 4]
        y = bp(seg, max(40, fc * .55), min(SR / 2 - 100, fc * 1.6), 1)[:hop]
        out[i:i + len(y)] += y
    p = np.arange(n) / n
    shape = np.where(p < peak, np.sin(np.pi / 2 * np.minimum(p / peak, 1)) ** 2,
                     np.clip(np.cos(np.pi / 2 * np.clip((p - peak) / (1 - peak), 0, 1)), 0, 1) ** 1.5)
    return norm(out * shape, .7)


def s_swish():
    return s_whoosh(0.45, 600, 7000, .4) * .7


def s_boom():       # sub hit with a soft transient
    t = t_(2.2)
    f = 38 + 60 * np.exp(-t * 9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), .004, 1.4, 3.2)
    x += lp(rng.standard_normal(len(t)), 900) * env(len(t), .001, .05) * .25
    return norm(x, .95)


def s_chime(f0=880.0):   # glassy bell (inharmonic partials)
    t = t_(2.4)
    x = sum(a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t * d) for r, a, d in
            [(1, 1, 2.2), (2.76, .45, 4), (5.4, .2, 7), (8.93, .1, 10)])
    return norm(x * env(len(t), .002, 9), .6)


def s_riser(d=1.5):
    n = int(d * SR); p = np.arange(n) / n
    x = hp(rng.standard_normal(n), 1500) * p ** 2.2
    x += np.sin(2 * np.pi * np.cumsum(300 + 900 * p ** 2) / SR) * p ** 3 * .25
    return norm(x * (1 - np.clip((p - .97) / .03, 0, 1)), .5)


def s_shimmer():
    t = t_(3.0)
    x = np.zeros(len(t))
    for i, f in enumerate([1174.66, 1479.98, 1760.0, 2217.46, 2637.02]):   # D major add9 sparkle
        o = int(i * .045 * SR)
        x[o:] += np.sin(2 * np.pi * f * t[: len(t) - o]) * np.exp(-t[: len(t) - o] * 2.1) * (0.8 ** i)
    return norm(x * env(len(t), .01, 9), .5)


SYNTH = dict(tick=s_tick, pop=s_pop, click=s_click, whoosh=s_whoosh, swish=s_swish,
             boom=s_boom, chime=s_chime, riser=s_riser, shimmer=s_shimmer)


def load(name, **kw):
    f = HERE / "sfx" / f"{name}.wav"
    if f.exists():
        x, sr = sf.read(f, always_2d=True)
        x = x.mean(1)
        if sr != SR:
            x = signal.resample_poly(x, SR, sr)
        return x
    return SYNTH[name](**kw)


# ---------------------------------------------------------------- music bed
def note(m):
    return 440 * 2 ** ((m - 69) / 12)


def pad_voice(f, d):
    t = t_(d)
    x = sum(signal.sawtooth(2 * np.pi * f * (1 + dt) * t + rng.uniform(0, 6)) for dt in (-.004, 0, .0035))
    return x / 3


def music():
    n = int(DUR * SR)
    out = np.zeros((n, 2))
    # D major, slow and open: Dmaj9 | Bm11 | Gmaj9 | Aadd9 , 6 s each
    chords = [[50, 57, 61, 64, 69], [47, 54, 62, 64, 69], [43, 50, 59, 62, 66], [45, 52, 59, 61, 64]]
    bar = 6.0
    t0 = 0.0
    k = 0
    while t0 < DUR:
        ch = chords[k % 4]
        d = min(bar + 2.5, DUR - t0)
        seg = sum(pad_voice(note(m), d) * (.55 if m < 52 else .3) for m in ch)
        seg = lp(seg, 1400 + 600 * np.sin(k), 2)
        e = np.minimum(1, t_(d) / 1.6) * np.minimum(1, (d - t_(d)) / 2.2)
        i = int(t0 * SR)
        out[i:i + len(seg), 0] += seg * e
        out[i:i + len(seg), 1] += np.roll(seg, 37) * e
        t0 += bar; k += 1
    # muted pluck arpeggio from the hero reveal, out before the end card
    arp_t, step = 2.2, 0.25
    i = 0
    while arp_t < 46.2:
        ch = chords[int(arp_t // bar) % 4]
        m = ch[[1, 3, 4, 2][i % 4]] + 12
        t = t_(.5)
        x = (signal.square(2 * np.pi * note(m) * t, .3) * .4 + np.sin(2 * np.pi * note(m) * t)) * env(len(t), .002, .12)
        x = lp(x, 2600)
        a = int(arp_t * SR); pan = .5 + .3 * np.sin(i * .7)
        out[a:a + len(x), 0] += x * .16 * (1 - pan); out[a:a + len(x), 1] += x * .16 * pan
        arp_t += step; i += 1
    # soft pulse kick on the beat through the body of the film
    for b in np.arange(12.0, 46.0, .75):
        t = t_(.35)
        k_ = np.sin(2 * np.pi * np.cumsum(45 + 80 * np.exp(-t * 30)) / SR) * env(len(t), .002, .18)
        a = int(b * SR); out[a:a + len(k_)] += (k_ * .35)[:, None]
    # final resolve on the logo
    t = t_(DUR - 46.55)
    fin = sum(pad_voice(note(m), len(t) / SR) for m in [38, 50, 57, 64, 66, 69]) / 4
    fin = lp(fin, 1800) * np.minimum(1, t / .05) * np.exp(-t * .55)
    out[int(46.55 * SR):, :] += fin[:, None] * .9
    out = verb(out, .35)
    out *= np.minimum(1, (DUR - np.arange(n) / SR) / 1.0)[:, None]      # tail fade
    return norm(out, .5)


# ---------------------------------------------------------------- voice
def voice():
    n = int(DUR * SR)
    out = np.zeros(n)
    for i, st in enumerate(VO_STARTS):
        x, sr = sf.read(HERE / "vo" / f"{i:02d}.wav")
        x = signal.resample_poly(x, SR, sr)
        x = hp(x, 75, 2)
        # gentle presence + air
        x = x + .25 * bp(x, 2500, 6000, 1) + .12 * hp(x, 9000, 1)
        # soft-knee leveling
        e = lp(np.abs(x), 12)
        g = 1 / (1 + 2.5 * np.maximum(0, e - .12))
        x = norm(x * g, .9)
        a = int(st * SR)
        out[a:a + len(x)] += x[: n - a]
    return out


def place(buf, x, at, gain=1.0, pan=0.0):
    a = int(at * SR)
    if a >= len(buf):
        return
    x = x[: len(buf) - a]
    buf[a:a + len(x), 0] += x * gain * (1 - max(0, pan))
    buf[a:a + len(x), 1] += x * gain * (1 + min(0, pan))


def sfx():
    n = int(DUR * SR)
    b = np.zeros((n, 2))
    tick, pop, click, swish = load("tick"), load("pop"), load("click"), load("swish")
    whoosh, boom, riser, shimmer = load("whoosh"), load("boom"), load("riser"), load("shimmer")
    # loader
    place(b, pop, .1, .35)
    place(b, riser, .3, .22)
    place(b, whoosh, 1.75, .55)
    place(b, boom, 2.05, .55)
    for i in range(2): place(b, tick, 1.95 + i * .14, .35, (-.3, .3)[i])
    place(b, pop, 2.6, .3, .4)
    for s in (6.3, 9.1): place(b, swish, s, .25, .4); place(b, tick, s + .28, .25, .4)
    # section scrolls
    for s in (11.9, 22.25, 26.3, 31.1, 37.05, 41.3): place(b, whoosh, s - .05, .5)
    # trust
    place(b, pop, 12.45, .35, -.4); place(b, pop, 12.57, .3, .4)
    for i in range(4): place(b, tick, 12.95 + i * .07, .22, (-.4, .4, -.2, .2)[i])
    place(b, swish, 13.1, .3)
    place(b, click, 18.93, .5, .1)
    for i in range(4): place(b, tick, 19.35 + i * .07, .22, (-.4, .4, -.2, .2)[i])
    place(b, swish, 19.3, .2)
    # services
    for i in range(2): place(b, tick, 22.75 + i * .12, .3)
    for i in range(3): place(b, pop, 23.35 + i * .09, .22, .2)
    for i in range(3): place(b, tick, 24.2 + i * .25, .14, .5)
    # scope
    place(b, pop, 26.75, .3, -.3)
    for i in range(3): place(b, tick, 26.95 + i * .12, .28, -.2)
    place(b, swish, 27.1, .3, .3); place(b, swish, 27.24, .25, .5)
    # systems — rising glass notes on each system
    place(b, tick, 31.55, .3); place(b, tick, 31.67, .3)
    for i, (s, m) in enumerate(zip([31.75, 32.55, 33.35, 35.15], [74, 78, 81, 86])):
        place(b, load("chime", f0=note(m)), s, .22, (-.45, -.15, .15, .45)[i])
    # project support — one beat per word
    for s in (37.55, 38.4, 39.2): place(b, tick, s, .45); place(b, pop, s + .02, .18)
    for i in range(3): place(b, swish, 38.0 + i * .12, .16, (-.4, 0, .4)[i])
    # CTA + logo
    for i in range(2): place(b, tick, 41.95 + i * .12, .3)
    place(b, pop, 42.3, .35, .4)
    place(b, click, 44.4, .5, .4)
    place(b, swish, 46.2, .3)
    place(b, boom, 46.5, .7)
    place(b, shimmer, 46.55, .35)
    return verb(b, .18)


def main():
    v = voice()
    m = music()
    fx = sfx()
    # duck the music under the voice (sidechain)
    ve = lp(np.abs(v), 6)
    duck = 1 - .55 * np.clip(ve / (ve.max() * .25), 0, 1)
    duck = lp(duck, 4)
    vs = verb(v, .08)
    mix = vs * 1.0 + m * duck[:, None] * .55 + fx * .8
    meter = pyln.Meter(SR)
    mix = pyln.normalize.loudness(mix, meter.integrated_loudness(mix), -14.0)
    peak = np.max(np.abs(mix))
    if peak > .89:                                                   # keep true-peak headroom
        mix = np.tanh(mix / .89 * 1.0) * .89 if peak > 1.2 else mix * (.89 / peak)
    (HERE / "out").mkdir(exist_ok=True)
    sf.write(HERE / "out" / "mix.wav", mix.astype(np.float32), SR, subtype="FLOAT")
    print("loudness", round(meter.integrated_loudness(mix), 2), "LUFS, peak", round(float(np.max(np.abs(mix))), 3))


if __name__ == "__main__":
    main()
