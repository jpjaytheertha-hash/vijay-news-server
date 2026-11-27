"""Vijay News – 'A Vijay Melpal Production' signature music (~7.5 s, C major, triumphant).
Uses the same synth instruments as music2.py.  python3 signature.py audio2   -> audio2/signature.wav"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "music2.py"), encoding="utf-8").read()
ns = {"__name__": "music2_lib", "sys": sys}
sys_argv = sys.argv[:]; sys.argv = [sys.argv[0], sys.argv[1] if len(sys.argv) > 1 else "audio2"]
exec(src.split("# harmony")[0], ns)          # instruments only, does not rewrite the other music files
sys.argv = sys_argv
SR, t, hz, lp = ns["SR"], ns["t"], ns["hz"], ns["lp"]
place, impact, whoosh, brass, pad, bell, tom, verb, st, write = (ns[k] for k in
    ("place", "impact", "whoosh", "brass", "pad", "bell", "tom", "verb", "st", "write"))

D = 7.5
L = np.zeros(int(D * SR)); R = np.zeros(int(D * SR))
mono = np.zeros(int(D * SR))
HIT = 1.0
place(mono, whoosh(1.0, True), 0.0, .55)                      # rising whoosh into the hit
for k, at in enumerate(np.linspace(0.35, 0.9, 6)):            # timpani pickup roll
    place(mono, tom(43 + (k % 2) * 7, .4), at, .35 + k * .08)
place(mono, impact(3.5), HIT, 1.0)                            # big cinematic hit
place(mono, brass([48, 55, 60, 64, 67], 1.6), HIT, .9)        # C major brass fanfare
place(mono, brass([53, 57, 60, 65, 69], 0.9), HIT + 1.55, .75) # F
place(mono, brass([48, 55, 60, 64, 67, 72], 3.6), HIT + 2.45, .95)  # back to C, held
place(mono, pad([48, 55, 60, 64, 67, 74], 5.8, 2200), HIT + .2, .55)  # warm string swell (add9)
for k, m in enumerate([79, 84, 88, 91, 96]):                  # golden bell sparkle
    place(mono, bell(m, 1.6), HIT + .25 + k * .14, .28)
for k, m in enumerate([84, 88, 91, 96]):
    place(mono, bell(m, 2.2), HIT + 2.5 + k * .1, .22)
place(mono, impact(3.0), HIT + 2.45, .45)
x = verb(mono, .3)
fade = np.ones(len(x)); n = int(1.2 * SR); fade[-n:] = np.linspace(1, 0, n) ** 1.5
write("signature.wav", st(x * fade))
print("wrote signature.wav")
