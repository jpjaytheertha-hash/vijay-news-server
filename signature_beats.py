"""Vijay News – 'A Vijay Melpal Production' signature, BEATS version (~7.5 s, 128 BPM, C minor).
Riser + drum fill -> punchy drop (kick, clap, 16th hats, sub bass, synth stabs) -> big final hit with tail.
python3 signature_beats.py audio2   -> audio2/signature.wav  (old brass version kept as signature_brass.wav)"""
import os, sys, shutil
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = sys.argv[1] if len(sys.argv) > 1 else "audio2"
src = open(os.path.join(HERE, "music2.py"), encoding="utf-8").read()
ns = {"__name__": "music2_lib"}
argv = sys.argv[:]; sys.argv = [argv[0], OUTDIR]; exec(src.split("# harmony")[0], ns); sys.argv = argv
SR, t, hz, lp, hp, bp = ns["SR"], ns["t"], ns["hz"], ns["lp"], ns["hp"], ns["bp"]
place, kick, snare, hat, impact, whoosh, saw, env, verb, st, write, tom = (ns[k] for k in
    ("place", "kick", "snare", "hat", "impact", "whoosh", "saw", "env", "verb", "st", "write", "tom"))
rng = np.random.default_rng(5)

BPM = 128; B = 60 / BPM; S = B / 4          # beat, sixteenth
D = 7.5; N = int(D * SR)
drums = np.zeros(N); music = np.zeros(N)
DROP = 1.0                                   # the logo hit lands here (matches the end card animation)

def clap(d=0.25):
    x = t(d); n = rng.standard_normal(len(x)); e = np.zeros_like(x)
    for o in (0, .011, .022): e += np.exp(-np.clip(x - o, 0, None) * 40) * (x >= o)
    return bp(n, 900, 5000) * e * .7
def sub(m, d):
    x = t(d); f = hz(m); y = np.sin(2 * np.pi * f * x) + .3 * np.sin(4 * np.pi * f * x)
    return np.tanh(1.5 * y) * env(len(x), .005, d * .7)
def stab(midis, d):
    s = sum(saw(hz(m), d, (-10, 0, 10)) for m in midis) / len(midis)
    return np.tanh(1.8 * lp(s, 2600)) * env(len(s), .003, d * .35)
def riser(d):
    x = t(d); f = 200 + 1800 * (x / d) ** 2; ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * .25 + whoosh(d, True) * .8) * (x / d) ** 1.5

# 1) build-up: riser + snare roll speeding up
place(music, riser(DROP), 0, .7)
k, at = 0, 0.15
while at < DROP - .05:
    place(drums, snare(.12), at, .25 + .6 * at / DROP); at += S if at < .6 else S / 2
place(drums, tom(45, .4), DROP - .25, .7); place(drums, tom(40, .4), DROP - .12, .8)

# 2) the drop: 4 bars of beats (C minor: Cm – Ab – Bb – Cm)
CH = [[60, 63, 67], [56, 60, 63], [58, 62, 65], [60, 63, 67]]
BASS = [36, 32, 34, 36]
bar_len = 4 * B / 2.5                        # short 'bars' so the groove fits the card
for bar in range(4):
    b0 = DROP + bar * bar_len
    for q in range(4):                       # kicks on every beat
        place(drums, kick(.45), b0 + q * bar_len / 4, 1.0)
        if q in (1, 3): place(drums, clap(), b0 + q * bar_len / 4, .8)
    for h in range(8):                       # off-beat / 8th hats
        place(drums, hat(.05), b0 + h * bar_len / 8 + (bar_len / 16 if h % 2 else 0), .35 if h % 2 else .2)
    place(music, sub(BASS[bar], bar_len * .95), b0, .9)
    for s_ in (0, 3, 6):                     # syncopated synth stabs (3-3-2 feel)
        place(music, stab(CH[bar], .22), b0 + s_ * bar_len / 8, .55)
    place(music, stab([m + 12 for m in CH[bar]], .16), b0 + 7 * bar_len / 8, .35)
end = DROP + 4 * bar_len
place(drums, impact(3.0), DROP, .9)          # hit with the logo
place(drums, impact(D - end + .2), end, 1.0) # final hit
place(music, stab([48, 55, 60, 63, 67, 72], D - end), end, .8)
place(music, sub(24, D - end), end, .9)

x = verb(music, .18) * .9 + drums * 1.0
fade = np.ones(N); n = int(1.0 * SR); fade[-n:] = np.linspace(1, 0, n) ** 1.6
dst = os.path.join(OUTDIR, "signature.wav")
if os.path.exists(dst) and not os.path.exists(os.path.join(OUTDIR, "signature_brass.wav")):
    shutil.copyfile(dst, os.path.join(OUTDIR, "signature_brass.wav"))
write("signature.wav", st(x * fade))
print("wrote", dst)
