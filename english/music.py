"""Original Vijay News music, synthesised from scratch (no samples, no copyright claims).
Outputs WAVs: intro.wav, sting.wav, bed.wav (loopable), outro.wav
"""
import numpy as np, sys, os
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
rng = np.random.default_rng(7)
OUT = sys.argv[1] if len(sys.argv) > 1 else "audio"
os.makedirs(OUT, exist_ok=True)

def t(d): return np.arange(int(d * SR)) / SR
def note(n): return 440.0 * 2 ** ((n - 69) / 12)  # midi -> Hz
def lp(x, fc, o=2): return sosfilt(butter(o, fc, 'low', fs=SR, output='sos'), x)
def hp(x, fc, o=2): return sosfilt(butter(o, fc, 'high', fs=SR, output='sos'), x)
def env(n, a=0.005, r=0.3):
    e = np.ones(n); A = max(1, int(a * SR)); e[:A] = np.linspace(0, 1, A)
    e *= np.exp(-np.arange(n) / (r * SR)); return e

def saw(f, d):
    x = t(d); return 2 * ((x * f) % 1) - 1

def pad(midis, d, bright=1800):
    x = t(d); s = np.zeros_like(x)
    for m in midis:
        for det in (-0.08, 0, 0.08):
            s += saw(note(m + det), d)
    s = lp(s / (3 * len(midis)), bright)
    a = np.minimum(1, x / 0.25) * np.minimum(1, (d - x) / 0.3).clip(0, 1)
    return s * a

def bell(m, d=1.6):
    x = t(d); f = note(m)
    mod = np.sin(2 * np.pi * f * 3.5 * x) * 2.2 * np.exp(-x * 3)
    return np.sin(2 * np.pi * f * x + mod) * env(len(x), 0.002, 0.5)

def boom(d=1.5, f0=110, f1=38):
    x = t(d); f = f1 + (f0 - f1) * np.exp(-x * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-x * 2.6)
    click = lp(rng.standard_normal(len(x)), 3000) * np.exp(-x * 60) * 0.5
    return np.tanh((body + click) * 1.8)

def hit(d=2.5):
    x = t(d); n = rng.standard_normal(len(x))
    crash = hp(n, 3000) * np.exp(-x * 2.2) * 0.35
    return boom(d) * 0.9 + crash

def riser(d):
    x = t(d); n = rng.standard_normal(len(x)); out = np.zeros_like(x)
    seg = 2048
    for i in range(0, len(x), seg):
        fc = 300 + 9000 * (i / len(x)) ** 2
        out[i:i + seg] = lp(n[i:i + seg], min(fc, 18000))
    return out * (x / d) ** 2 * 0.5

def tick(d=0.05):
    x = t(d); return hp(rng.standard_normal(len(x)), 7000) * np.exp(-x * 120)

IR = None
def reverb(x, wet=0.25, size=1.8):
    global IR
    if IR is None:
        n = int(size * SR); xi = np.arange(n) / SR
        IR = lp(rng.standard_normal(n), 6000) * np.exp(-xi * 3.2); IR /= np.abs(IR).sum() / 8
    return x + wet * fftconvolve(x, IR)[:len(x)]

def place(buf, sig, at, g=1.0):
    i = int(at * SR); j = min(len(buf), i + len(sig)); buf[i:j] += sig[:j - i] * g

def stereo(m, width=0.0):
    d = int(0.012 * SR) if width else 0
    r = np.concatenate([np.zeros(d), m])[:len(m)]
    return np.stack([m, m * (1 - width) + r * width], 1)

def norm(x, peak=0.89): return x / (np.abs(x).max() + 1e-9) * peak

def write(name, x):
    wavfile.write(os.path.join(OUT, name), SR, (norm(x) * 32767).astype(np.int16))

BPM = 120; B = 60 / BPM
# D minor: Dm, Bb, F, C
CHORDS = [[50, 53, 57, 62], [46, 50, 53, 58], [53, 57, 60, 65], [48, 52, 55, 60]]
ROOTS = [38, 34, 41, 36]

def bass_line(dur_beats, roots, beats_per=4, g=0.35):
    n = int(dur_beats * B * SR); out = np.zeros(n)
    for k in range(int(dur_beats * 2)):
        r = roots[(k // (beats_per * 2)) % len(roots)]
        s = lp(saw(note(r), B / 2 * 0.9), 500) * env(int(B / 2 * 0.9 * SR), 0.003, 0.12)
        place(out, s, k * B / 2, g)
    return out

# ---------- INTRO (8 s) ----------
def intro():
    d = 8.5; buf = np.zeros(int(d * SR))
    place(buf, riser(2.0), 0.0, 0.8)
    place(buf, hit(3), 2.0, 1.0)
    for i, c in enumerate(CHORDS):
        place(buf, pad(c, 4 * B * 0.98), 2.0 + i * 4 * B * 0.5, 0.0)  # placeholder (overwritten below)
    # 4 chords x 2 beats from 2.0s
    for i, c in enumerate(CHORDS):
        place(buf, pad(c, 2 * B), 2.0 + i * 2 * B, 0.55)
    place(buf, bass_line(8, ROOTS, beats_per=2), 2.0, 0.6)
    for k in range(16):
        place(buf, tick(), 2.0 + k * B / 2, 0.18 if k % 2 else 0.1)
        if k % 4 == 0: place(buf, boom(0.5, 90, 45), 2.0 + k * B / 2, 0.45)
    for i, m in enumerate([74, 81, 77, 74, 72, 74]):
        place(buf, bell(m), 2.0 + i * B * 0.75, 0.35)
    place(buf, hit(3.5), 6.0, 1.1)
    place(buf, pad([50, 57, 62, 65, 69], 2.5, 2500), 6.0, 0.5)
    place(buf, bell(86, 2.5), 6.0, 0.3)
    buf = reverb(buf, 0.3)
    return stereo(buf, 0.3)

# ---------- STING (2.2 s) ----------
def sting():
    d = 2.4; buf = np.zeros(int(d * SR))
    place(buf, riser(0.7), 0.0, 0.9)
    place(buf, hit(1.7), 0.7, 1.0)
    place(buf, pad([50, 57, 62, 65], 1.2, 3000) * env(int(1.2 * SR), 0.003, 0.4), 0.7, 0.6)
    place(buf, bell(86), 0.7, 0.3); place(buf, bell(81), 0.85, 0.25)
    return stereo(reverb(buf, 0.3), 0.3)

# ---------- BED (16 s loop, soft) ----------
def bed():
    bpm_b = 60 / 100; d = 16 * bpm_b * 1.0 * 1.0 * 1.0 * 1.0; d = 16 * bpm_b
    buf = np.zeros(int(d * SR))
    seq = [CHORDS[0], CHORDS[1], CHORDS[2], CHORDS[3]]
    for i, c in enumerate(seq):
        place(buf, pad([m - 12 for m in c] + c[:2], 4 * bpm_b, 900), i * 4 * bpm_b, 0.35)
    for k in range(32):
        r = ROOTS[(k // 8) % 4]
        s = lp(saw(note(r), bpm_b / 2 * 0.8), 300) * env(int(bpm_b / 2 * 0.8 * SR), 0.004, 0.1)
        place(buf, s, k * bpm_b / 2, 0.25)
        place(buf, tick(), k * bpm_b / 2 + bpm_b / 4, 0.07)
    # crossfade tail into head for seamless loop
    buf = reverb(buf, 0.2)
    return stereo(buf, 0.4)

# ---------- OUTRO (6.5 s) ----------
def outro():
    d = 7.0; buf = np.zeros(int(d * SR))
    prog = [CHORDS[1], CHORDS[3], CHORDS[0]]
    for i, c in enumerate(prog):
        place(buf, pad(c, 2 * B if i < 2 else 3.5, 2200), i * 2 * B, 0.55)
    place(buf, bass_line(4, [34, 36], beats_per=2), 0, 0.55)
    for i, m in enumerate([77, 79, 81, 86]):
        place(buf, bell(m, 2), i * B * 0.5, 0.3)
    place(buf, hit(4), 2.0, 1.0)
    place(buf, bell(74, 3), 2.0, 0.35)
    x = np.arange(len(buf)) / SR
    buf *= np.clip((d - x) / 2.5, 0, 1)
    return stereo(reverb(buf, 0.35), 0.3)

for name, fn in [("intro.wav", intro), ("sting.wav", sting), ("bed.wav", bed), ("outro.wav", outro)]:
    write(name, fn()); print("wrote", name)
