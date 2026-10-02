"""Sound for the 30 s technomadenviro ad -> ../out/ad_mix.wav (48 kHz stereo, -14 LUFS).

Reuses the synths in ../audio.py; WAVs dropped in ../sfx/ still override each sound.
"""
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import audio as A  # noqa: E402

SR, DUR = A.SR, 30.0
A.DUR = DUR
VO_STARTS = [0.0, 2.5, 10.05, 16.2, 22.4]          # file starts; speech begins ~0.3 s in
T = A.t_


def music():
    n = int(DUR * SR)
    out = np.zeros((n, 2))
    bpm = 104; beat = 60 / bpm; bar = beat * 4
    chords = [[50, 57, 61, 64, 69], [47, 54, 62, 64, 69], [43, 50, 59, 62, 66], [45, 52, 59, 61, 64]]
    k, t0 = 0, 0.0
    while t0 < DUR:
        ch = chords[k % 4]; d = min(bar * 2 + 1.5, DUR - t0)
        s = sum(A.pad_voice(A.note(m), d) * (.5 if m < 52 else .28) for m in ch)
        s = A.lp(s, 1600, 2) * np.minimum(1, T(d) / .8) * np.minimum(1, (d - T(d)) / 1.2)
        i = int(t0 * SR); out[i:i + len(s), 0] += s; out[i:i + len(s), 1] += np.roll(s, 41)
        t0 += bar * 2; k += 1
    # driving 16th pluck from the first cut, kick on the beat, a lift into the CTA
    i, tt = 0, 2.72
    while tt < 29.2:
        ch = chords[int(tt // (bar * 2)) % 4]; m = ch[[1, 3, 4, 2][i % 4]] + 12
        x = (signal.square(2 * np.pi * A.note(m) * T(.3), .3) * .35 + np.sin(2 * np.pi * A.note(m) * T(.3))) * A.env(int(.3 * SR), .002, .07)
        x = A.lp(x, 3000); a = int(tt * SR); pan = .5 + .35 * np.sin(i * .9)
        out[a:a + len(x), 0] += x * .14 * (1 - pan); out[a:a + len(x), 1] += x * .14 * pan
        tt += beat / 2; i += 1
    for b in np.arange(2.72, 29.0, beat):
        kk = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-T(.35) * 30)) / SR) * A.env(int(.35 * SR), .002, .16)
        a = int(b * SR); out[a:a + len(kk)] += (kk * .4)[:, None]
    tail = T(DUR - 22.4)
    fin = sum(A.pad_voice(A.note(m), len(tail) / SR) for m in [38, 50, 57, 64, 66, 69]) / 4
    out[int(22.4 * SR):] += (A.lp(fin, 2000) * np.minimum(1, tail / .05) * np.exp(-tail * .25))[:, None] * .7
    out = A.verb(out, .3)
    out *= np.minimum(1, (DUR - np.arange(n) / SR) / .6)[:, None]
    return A.norm(out, .5)


def voice():
    n = int(DUR * SR); out = np.zeros(n)
    for i, st in enumerate(VO_STARTS):
        x, sr = sf.read(HERE / "vo" / f"{i:02d}.wav")
        x = signal.resample_poly(x, SR, sr)
        x = A.hp(x, 75, 2); x = x + .25 * A.bp(x, 2500, 6000, 1) + .12 * A.hp(x, 9000, 1)
        e = A.lp(np.abs(x), 12); x = A.norm(x / (1 + 2.5 * np.maximum(0, e - .12)), .9)
        a = int(st * SR); out[a:a + len(x)] += x[: n - a]
    return out


def sfx():
    b = np.zeros((int(DUR * SR), 2))
    tick, pop, click, swish = A.load("tick"), A.load("pop"), A.load("click"), A.load("swish")
    whoosh, boom, shimmer = A.load("whoosh"), A.load("boom"), A.load("shimmer")
    P = A.place
    P(b, swish, .3, .3); P(b, boom, .38, .45); P(b, boom, 1.72, .75); P(b, tick, 1.72, .4)
    for s in (2.72, 9.92, 15.95, 22.15): P(b, whoosh, s - .08, .55)
    for i, (s, m) in enumerate(zip([4.42, 5.27, 6.02, 8.3], [74, 78, 81, 86])):
        P(b, tick, s, .4, (-.4, -.15, .15, .4)[i]); P(b, A.load("chime", f0=A.note(m)), s, .2, (-.4, -.15, .15, .4)[i])
    for i, s in enumerate([12.0, 12.55, 13.32, 14.66]): P(b, tick, s, .42, (-.3, -.1, .1, .3)[i])
    P(b, swish, 10.4, .3, .4)
    for i, s in enumerate([18.1, 18.72, 19.5, 20.3]): P(b, swish, s - .05, .25, (-.3, -.1, .1, .3)[i]); P(b, pop, s + .12, .3)
    P(b, boom, 22.4, .6); P(b, shimmer, 22.45, .35)
    for s in (22.72, 24.45): P(b, tick, s, .3)
    P(b, pop, 26.05, .4); P(b, tick, 27.08, .3); P(b, click, 28.1, .5)
    return A.verb(b, .16)


def limit(x, ceil, look=0.005, release=0.08):
    """Look-ahead peak limiter: gain follows the upcoming peak, recovers smoothly."""
    la = int(look * SR)
    pk = np.max(np.abs(x), 1)
    pk = np.lib.stride_tricks.sliding_window_view(np.r_[pk, np.zeros(la)], la + 1).max(1)   # peak over the next `look`
    g = np.minimum(1, ceil / np.maximum(pk, 1e-9))
    a = np.exp(-1 / (release * SR))
    out = np.empty_like(g); cur = 1.0
    for i, v in enumerate(g):              # instant attack, exponential release
        cur = v if v < cur else a * cur + (1 - a) * v
        out[i] = cur
    return x * out[:, None]


def main():
    v, m, fx = voice(), music(), sfx()
    ve = A.lp(np.abs(v), 6)
    duck = A.lp(1 - .55 * np.clip(ve / (ve.max() * .25), 0, 1), 4)
    mix = A.verb(v, .07) + m * duck[:, None] * .6 + fx * .8
    meter = pyln.Meter(SR)
    for _ in range(4):                     # loudness-normalize, then limit; repeat until it settles at -14
        mix = pyln.normalize.loudness(mix, meter.integrated_loudness(mix), -14.0)
        mix = limit(mix, .89)
    sf.write(HERE.parent / "out" / "ad_mix.wav", mix.astype(np.float32), SR, subtype="FLOAT")
    print("loudness", round(meter.integrated_loudness(mix), 2), "LUFS, peak", round(float(np.max(np.abs(mix))), 3),
          "duration", len(mix) / SR)


if __name__ == "__main__":
    main()
