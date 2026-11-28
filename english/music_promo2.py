"""Vijay News English – positive, premium news theme for the 15 s 'behind the scenes' promo (original composition).
D major, 120 BPM: bright pluck arpeggios, warm pad, piano chords, four-on-the-floor kick + claps, rising
whoosh into a final brass-and-cymbal hit.   python3 music_promo2.py audio2/positive.wav [seconds]"""
import numpy as np, sys
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100; rng = np.random.default_rng(28)
OUT = sys.argv[1] if len(sys.argv) > 1 else "positive.wav"
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0
BPM = 120; B = 60 / BPM

def t(d): return np.arange(int(d * SR)) / SR
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def lp(x, f): return sosfilt(butter(2, min(f, 20000), 'low', fs=SR, output='sos'), x)
def hp(x, f): return sosfilt(butter(2, f, 'high', fs=SR, output='sos'), x)
def env(n, a=0.005, r=0.3):
    e = np.exp(-np.arange(n) / (r * SR)); A = max(1, int(a * SR)); e[:A] *= np.linspace(0, 1, A); return e
def place(buf, s, at, g=1.0):
    i = int(at * SR)
    if i >= len(buf): return
    j = min(len(buf), i + len(s)); buf[i:j] += s[:j - i] * g

def pluck(m, d=0.35):
    x = t(d); f = hz(m)
    s = np.sin(2 * np.pi * f * x) + 0.5 * np.sin(4 * np.pi * f * x) + 0.25 * np.sin(6 * np.pi * f * x)
    return lp(s * env(len(x), 0.002, 0.12), 6000)
def piano(m, d=1.8):
    x = t(d); f = hz(m)
    s = sum(a * np.sin(2 * np.pi * f * k * x) * np.exp(-x * (1.2 + k * 0.8)) for k, a in ((1, 1), (2, .45), (3, .2), (4, .1)))
    return s * env(len(x), 0.004, 1.2)
def pad(ms, d):
    x = t(d); s = sum(np.sin(2 * np.pi * hz(m) * x * (1 + c)) for m in ms for c in (-0.003, 0.003))
    e = np.minimum(1, x / 0.6) * np.minimum(1, (d - x) / 0.6); return lp(s * e, 2500) / (2 * len(ms))
def kick():
    x = t(0.4); f = 50 + 110 * np.exp(-x * 35); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2 * np.sin(ph) * np.exp(-x * 9))
def clap():
    x = t(0.25); n = hp(rng.standard_normal(len(x)), 1200)
    return n * (np.exp(-x * 30) + 0.6 * np.exp(-np.maximum(0, x - 0.012) * 30) * (x > 0.012))
def hat():
    x = t(0.08); return hp(rng.standard_normal(len(x)), 7000) * np.exp(-x * 60)
def whoosh(d=1.6):
    x = t(d); n = rng.standard_normal(len(x)); out = np.zeros_like(n)
    for k in range(0, len(x), 2205):   # rising filter sweep
        fc = 300 + 8000 * (k / len(x)) ** 2; seg = slice(k, k + 2205); out[seg] = lp(n[seg], fc)
    return out * (x / d) ** 2
def hit():
    x = t(2.6); f = hz(50)
    brass = sum(np.sign(np.sin(2 * np.pi * hz(m) * x)) * 0.25 for m in (62, 66, 69, 74))
    cym = hp(rng.standard_normal(len(x)), 5000) * np.exp(-x * 1.6) * 0.5
    boom = np.sin(2 * np.pi * f * x * (1 + np.exp(-x * 8))) * np.exp(-x * 2.5)
    return lp(brass, 3500) * np.exp(-x * 1.4) + cym + boom * 1.2

L = int((DUR + 3) * SR); mix = np.zeros(L)
# I – V – vi – IV in D major (D A Bm G), one chord per bar, uplifting
CH = [(62, 66, 69), (61, 64, 69), (59, 62, 66), (59, 62, 67)]
ARP = [[62, 66, 69, 74], [61, 64, 69, 73], [59, 62, 66, 71], [59, 62, 67, 71]]
bars = int(DUR / (4 * B)) + 1
end = DUR - 2.4                                   # final hit lands here
for b in range(bars):
    t0 = b * 4 * B
    if t0 >= end: break
    c = b % 4
    place(mix, pad(CH[c], 4 * B + 0.3), t0, 0.9)
    place(mix, sum(piano(m) for m in CH[c]) / 3, t0, 0.55)
    for k in range(16):                           # 16th-note pluck arpeggio, brighter from bar 2
        at = t0 + k * B / 4
        if at < end: place(mix, pluck(ARP[c][k % 4] + (12 if b >= 1 and k % 8 >= 4 else 0)), at, 0.32)
    if b >= 1:                                    # groove enters on bar 2
        for k in range(4):
            at = t0 + k * B
            if at < end - 0.05:
                place(mix, kick(), at, 0.8)
                if k in (1, 3): place(mix, clap(), at, 0.35)
                place(mix, hat(), at + B / 2, 0.18)
place(mix, whoosh(1.6), end - 1.6, 0.35)
place(mix, hit(), end, 0.9)
place(mix, pad((62, 66, 69, 74), 2.6), end, 1.0)
x = mix[:int(DUR * SR)]
x = x / max(1e-6, np.abs(x).max()) * 0.9
fade = int(0.4 * SR); x[-fade:] *= np.linspace(1, 0, fade)
st = np.stack([x, np.roll(x, 220) * 0.96], 1)      # light stereo width
wavfile.write(OUT, SR, (st * 32767).astype(np.int16)); print("wrote", OUT, f"{DUR:.1f}s")
