"""Vijay, 27 Nov 2026: mass-cinema title music for "A VIJAY MELPAL PRODUCTION" – ORIGINAL, synthesized here
(no copied tune). Tension strings rising under the letters, a huge dhol/taiko BOOM + metal clang on every letter
slam, a riser and a split-second of silence, then a massive brass stab with sub drop, cymbal crash and a hero
whistle, and a dhol groove under PRODUCTION. Timing matches make_bulletin.build_credit."""
import numpy as np, wave, sys
SR = 44100; DUR = 7.5
LETTER_T0, LETTER_STEP, N, STAB_T, IMPACT = 0.35, 0.19, 11, 2.55, 0.13
t = np.arange(int(SR * DUR)) / SR; L = np.zeros_like(t); R = np.zeros_like(t)
rng = np.random.default_rng(5)
def add(sig, at, pan=0.0, g=1.0):
    i = int(at * SR); n = min(len(sig), len(L) - i)
    if n > 0: L[i:i+n] += sig[:n] * g * (1 - max(0, pan)); R[i:i+n] += sig[:n] * g * (1 + min(0, pan))
def env(n, a, d):
    x = np.arange(n) / SR; return np.minimum(1, x / max(a, 1e-4)) * np.exp(-x / d)
def lp(x, c):
    y = np.zeros_like(x); a = 0.0
    for i in range(len(x)): a += c * (x[i] - a); y[i] = a
    return y
def boom(big=1.0):
    n = int(SR * 1.2); x = np.arange(n) / SR
    body = np.sin(2 * np.pi * (48 * x + 90 * (1 - np.exp(-x * 22)) / 22)) * env(n, 0.001, 0.32 * big)
    crack = rng.standard_normal(n) * env(n, 0.0005, 0.03)
    return np.tanh(2.2 * (0.9 * body + 0.35 * crack)) * 0.8
def clang(k):
    n = int(SR * 0.8); x = np.arange(n) / SR; f = 520 + 40 * (k % 4)
    return sum(np.sin(2 * np.pi * f * r * x) / (1 + j) for j, r in enumerate((1, 2.41, 3.77, 5.93))) * env(n, 0.0005, 0.22) * 0.18
# tension strings: tremolo saw cluster rising in pitch until the stab
ts = t[t < STAB_T]; pitch = 1 + 0.5 * (ts / STAB_T) ** 2; trem = 0.6 + 0.4 * np.sin(2 * np.pi * 12 * ts)
strings = sum(sum(np.sin(2 * np.pi * h * f * np.cumsum(pitch) / SR) / h for h in range(1, 7)) for f in (110, 130.8, 164.8)) * trem
strings *= 0.05 * np.minimum(1, ts / 0.3)
L[:len(ts)] += strings; R[:len(ts)] += strings * 0.9
for k in range(N):
    at = LETTER_T0 + k * LETTER_STEP + IMPACT
    add(boom(1.0 + 0.04 * k), at, g=0.9); add(clang(k), at, pan=0.6 * np.sin(k * 1.7))
# riser into the stab, then a split second of silence
n = int(SR * 0.6); x = np.arange(n) / SR
riser = lp(rng.standard_normal(n), 0.05) * (x / 0.6) ** 2 * 0.7 + np.sin(2 * np.pi * np.cumsum(220 + 1400 * (x / 0.6) ** 2) / SR) * (x / 0.6) ** 2 * 0.15
add(riser, STAB_T - 0.68)
gap = (t > STAB_T - 0.08) & (t < STAB_T); L[gap] *= 0.15; R[gap] *= 0.15
# the stab: brass chord (saturated), sub drop, crash
n = int(SR * 4.5); x = np.arange(n) / SR
brass = np.zeros(n)
for f in (73.42, 146.83, 220.0, 293.66, 349.23, 440.0, 587.33):
    for det in (-1.2, 0, 1.2):
        brass += sum(np.sin(2 * np.pi * h * (f + det) * x) / h for h in range(1, 10)) * 0.03
brass = np.tanh(2.5 * lp(brass, 0.25)) * env(n, 0.015, 1.8)
sub = np.sin(2 * np.pi * (35 * x + 60 * (1 - np.exp(-x * 6)) / 6)) * env(n, 0.002, 1.0)
crash = lp(rng.standard_normal(n), 0.6) - lp(rng.standard_normal(n), 0.05); crash *= env(n, 0.001, 1.4) * 0.35
add(brass, STAB_T, g=0.7); add(sub, STAB_T, g=0.9); add(crash, STAB_T, pan=0.2); add(boom(1.6), STAB_T, g=1.0)
# hero whistle: "wheeet – wheeet"
for w0 in (STAB_T + 0.45, STAB_T + 0.95):
    n = int(SR * 0.42); x = np.arange(n) / SR
    f = 1800 + 1300 * np.minimum(1, x / 0.12) + 40 * np.sin(2 * np.pi * 7 * x)
    add(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.02, 0.3) * 0.22, w0, pan=-0.2)
# dhol groove under PRODUCTION (150 bpm eighths), fading out
beat = 60 / 150 / 2; pat = [1, 0, 0.6, 1, 0, 0.6, 1, 0.8]
for j in range(28):
    at = STAB_T + 0.6 + j * beat
    if at > DUR - 0.6: break
    if pat[j % 8]: add(boom(0.6) * pat[j % 8] * 0.55, at, g=0.8 * (1 - j / 34))
    nn = int(SR * 0.08); add(lp(rng.standard_normal(nn), 0.5) * env(nn, 0.0005, 0.02) * 0.25, at + beat / 2, pan=0.4)
fade = np.clip((DUR - t) / 1.0, 0, 1); L *= fade; R *= fade
st = np.stack([L, R], 1); st = np.tanh(st / (np.abs(st).max() + 1e-9) * 1.4) / np.tanh(1.4) * 0.9
out = sys.argv[1] if len(sys.argv) > 1 else "audio2/signature.wav"
w = wave.open(out, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
print("wrote", out)
