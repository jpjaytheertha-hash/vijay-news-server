"""Vijay News music v2 – high-energy Indian TV-news style (original composition).
Fast 140 BPM, pounding toms + kick, staccato string ostinato, brass stabs, big impacts,
whooshes, tension pad. Outputs intro.wav, sting.wav, bed.wav, outro.wav into given dir."""
import numpy as np, sys, os
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100; rng = np.random.default_rng(11)
OUT = sys.argv[1] if len(sys.argv) > 1 else "audio"; os.makedirs(OUT, exist_ok=True)
BPM = 140; B = 60 / BPM; S16 = B / 4

def t(d): return np.arange(int(d * SR)) / SR
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def lp(x, f, o=2): return sosfilt(butter(o, min(f, 20000), 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)
def env(n, a=0.003, r=0.2):
    e = np.exp(-np.arange(n) / (r * SR)); A = max(1, int(a * SR)); e[:A] *= np.linspace(0, 1, A); return e
def saw(f, d, det=(0,)):
    x = t(d); return sum(2 * ((x * f * 2 ** (c / 1200) + rng.random()) % 1) - 1 for c in det) / len(det)
def place(buf, s, at, g=1.0):
    i = int(at * SR)
    if i >= len(buf): return
    j = min(len(buf), i + len(s)); buf[i:j] += s[:j - i] * g

def kick(d=0.5):
    x = t(d); f = 45 + 120 * np.exp(-x * 30); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.5 * np.sin(ph) * np.exp(-x * 7)) + lp(rng.standard_normal(len(x)), 4000) * np.exp(-x * 90) * .3
def tom(m, d=0.45):
    x = t(d); f = hz(m) * (1 + 0.6 * np.exp(-x * 25)); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.8 * np.sin(ph) * np.exp(-x * 7.5)) + bp(rng.standard_normal(len(x)), 200, 2000) * np.exp(-x * 40) * .25
def snare(d=0.3):
    x = t(d); return bp(rng.standard_normal(len(x)), 1200, 9000) * np.exp(-x * 18) * .8 + np.sin(2 * np.pi * 190 * x) * np.exp(-x * 25) * .5
def hat(d=0.06):
    x = t(d); return hp(rng.standard_normal(len(x)), 8000) * np.exp(-x * 90)
def impact(d=3.0):
    x = t(d); f = 30 + 90 * np.exp(-x * 9); ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * np.exp(-x * 1.6)
    n = rng.standard_normal(len(x)); boom = lp(n, 900) * np.exp(-x * 3) * .9
    crash = hp(n, 4000) * np.exp(-x * 1.8) * .35
    return np.tanh(1.6 * (sub + boom)) + crash
def whoosh(d=1.0, up=True):
    x = t(d); n = rng.standard_normal(len(x)); out = np.zeros_like(x); seg = 1024
    for i in range(0, len(x), seg):
        p = i / len(x); p = p if up else 1 - p
        c = 400 + 9000 * p ** 2; out[i:i + seg] = bp(n[i:i + seg], c * .6, min(c * 1.6, 19000))
    shape = (x / d) ** 2.2 if up else np.exp(-x * 4)
    return out * shape
def string_stab(midis, d):  # staccato ensemble
    s = sum(saw(hz(m), d, (-9, 0, 8)) for m in midis) / len(midis)
    return lp(s, 3200) * env(len(s), 0.004, d * 0.45)
def brass(midis, d):
    x = t(d); s = sum(saw(hz(m), d, (-6, 6)) for m in midis) / len(midis)
    cut = 600 + 3500 * np.exp(-x * 6)
    out = np.zeros_like(s); seg = 512
    for i in range(0, len(s), seg): out[i:i + seg] = lp(s[i:i + seg], cut[i])
    return np.tanh(2 * out) * env(len(s), 0.01, d * 0.6)
def pad(midis, d, f=1500):
    x = t(d); s = sum(saw(hz(m), d, (-12, 0, 11)) for m in midis) / len(midis)
    return lp(s, f) * np.minimum(1, x / .3) * np.clip((d - x) / .4, 0, 1)
def bell(m, d=1.2):
    x = t(d); f = hz(m); return np.sin(2 * np.pi * f * x + 2 * np.sin(2 * np.pi * f * 3.5 * x) * np.exp(-x * 4)) * env(len(x), .002, .4)

IR = None
def verb(x, wet=.22):
    global IR
    if IR is None:
        n = int(1.6 * SR); IR = lp(rng.standard_normal(n), 5000) * np.exp(-np.arange(n) / SR * 3.5); IR /= np.abs(IR).sum() / 7
    return x + wet * fftconvolve(x, IR)[:len(x)]
def st(m, w=.35):
    d = int(.011 * SR); r = np.concatenate([np.zeros(d), m])[:len(m)]; return np.stack([m, m * (1 - w) + r * w], 1)
def write(n, x): x = x / (np.abs(x).max() + 1e-9) * .9; wavfile.write(os.path.join(OUT, n), SR, (x * 32767).astype(np.int16))

# harmony: C minor tension – Cm, Ab, Bb, G(sus) ; ostinato on C
OST = [60, 60, 72, 60, 67, 60, 70, 60]  # 16th string ostinato pattern
CH = [[48, 55, 60, 63], [44, 51, 56, 60], [46, 53, 58, 62], [43, 50, 55, 59]]

def drums(buf, at, bars, dense=True, g=1.0):
    for b in range(bars):
        o = at + b * 4 * B
        for k in range(16):
            tt = o + k * S16
            if k in (0, 6, 10) or (dense and k == 14): place(buf, kick(), tt, .9 * g)
            if k in (4, 12): place(buf, snare(), tt, .55 * g)
            place(buf, hat(), tt, (.16 if k % 2 else .1) * g)
        if dense:  # tom fill on last beat
            for i, m in enumerate([50, 47, 43, 40]): place(buf, tom(m), o + 3 * B + i * S16, .55 * g)
        else:
            for k in (2, 7, 11): place(buf, tom(45), o + k * S16, .35 * g)

def ostinato(buf, at, bars, root_shift, g=.32):
    for b in range(bars):
        sh = root_shift[b % len(root_shift)]
        for k in range(16):
            m = OST[k % 8] + sh; place(buf, string_stab([m, m + 12], S16 * .9), at + b * 4 * B + k * S16, g)

def intro():
    d = 11.0; buf = np.zeros(int(d * SR))
    place(buf, whoosh(1.2), 0, .7)
    for i, m in enumerate([36, 36, 36]): place(buf, tom(m + 7, .5), .2 + i * B * .5, .5)
    place(buf, impact(), 1.2, 1.0)
    place(buf, brass([60, 63, 67, 72], 1.0), 1.2, .55)
    ostinato(buf, 1.2, 4, [0, -4, -2, -5])
    drums(buf, 1.2, 4, True, .9)
    for i, c in enumerate(CH): place(buf, pad(c, 4 * B), 1.2 + i * 4 * B, .35)
    for i, c in enumerate(CH):  # brass stabs on 1 and the "and" of 2
        place(buf, brass([m + 12 for m in c[1:]], .35), 1.2 + i * 4 * B, .5)
        place(buf, brass([m + 12 for m in c[1:]], .3), 1.2 + i * 4 * B + 1.5 * B, .4)
    end = 1.2 + 16 * B
    place(buf, whoosh(.6), end - .6, .6)
    place(buf, impact(3.5), end, 1.15)
    place(buf, brass([48, 55, 60, 63, 67, 72], 2.0), end, .7)
    place(buf, bell(84, 2), end, .25)
    return st(verb(buf, .25))

def sting():
    d = 2.6; buf = np.zeros(int(d * SR))
    place(buf, whoosh(.65), 0, .9)
    for i, m in enumerate([52, 48, 45]): place(buf, tom(m), .65 - 3 * S16 + i * S16, .6)
    place(buf, impact(1.9), .65, 1.0)
    place(buf, brass([60, 63, 67, 72], .9), .65, .6)
    place(buf, string_stab([72, 84], .2), .65, .4); place(buf, string_stab([75, 87], .2), .65 + S16 * 2, .35)
    place(buf, bell(84), .65, .2)
    return st(verb(buf, .25))

def bed():
    bars = 8; d = bars * 4 * B; buf = np.zeros(int(d * SR))
    for b in range(bars):
        sh = [0, -4, -2, -5][(b // 2) % 4]; o = b * 4 * B
        for k in range(16):
            m = OST[k % 8] + sh - 12; place(buf, lp(string_stab([m], S16 * .8), 1400), o + k * S16, .25)
            place(buf, hat(), o + k * S16, .05 if k % 2 else .03)
        for k in (0, 10): place(buf, kick(.4), o + k * S16, .35)
        place(buf, pad([c - 12 for c in CH[(b // 2) % 4]], 4 * B, 900), o, .22)
    tail = verb(buf, .2)
    return st(tail)

def outro():
    d = 7.5; buf = np.zeros(int(d * SR))
    ostinato(buf, 0, 2, [-4, -2], .3)
    drums(buf, 0, 2, True, .85)
    place(buf, pad(CH[1], 4 * B), 0, .35); place(buf, pad(CH[2], 4 * B), 4 * B, .35)
    end = 8 * B
    place(buf, whoosh(.5), end - .5, .6)
    place(buf, impact(4), end, 1.15)
    place(buf, brass([48, 55, 60, 63, 67, 72], 3.0), end, .7)
    place(buf, pad([48, 55, 60, 63, 67], 3.5, 1800), end, .3)
    x = np.arange(len(buf)) / SR; buf *= np.clip((d - x) / 2.0, 0, 1)
    return st(verb(buf, .3))

for n, fn in [("intro.wav", intro), ("sting.wav", sting), ("bed.wav", bed), ("outro.wav", outro)]:
    write(n, fn()); print("wrote", n)
