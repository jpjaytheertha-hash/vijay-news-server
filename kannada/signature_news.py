"""Vijay, 27 Nov 2026: the end-card music must "match the news theme and also kind of promo music".
Built from the channel's OWN news theme (music2.py: 140 BPM, C minor, string ostinato, toms, brass, impact) –
a tom + string stab lands on every gold letter (2 sixteenths apart), then the theme's big impact + brass chord
when the name is complete. Timing matches make_bulletin.build_credit: first letter impact 0.43 s, step 0.2143 s,
stab 3.0 s."""
import sys, os, types, numpy as np
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "music2.py")).read()
src = src[:src.index('for n, fn in [("intro.wav"')]          # take the instruments, not the file writing
m2 = types.ModuleType("m2"); sys.argv = [sys.argv[0], "/tmp"] + sys.argv[1:]; exec(src, m2.__dict__)
B, S16 = m2.B, m2.S16; SR = m2.SR
D = 7.5; buf = np.zeros(int(D * SR))
FIRST, STEP, N, STAB = 0.43, 2 * S16, 11, 3.0
m2.place(buf, m2.whoosh(0.45), 0.0, 0.6)
for i, mm in enumerate([43, 45, 48]): m2.place(buf, m2.tom(mm, 0.4), FIRST - 3 * S16 + i * S16, 0.45)
# driving news groove under the letters
m2.ostinato(buf, FIRST, 2, [0, -4], 0.26)
m2.drums(buf, FIRST, 1, False, 0.7)
m2.place(buf, m2.pad(m2.CH[0], STAB - FIRST), FIRST, 0.28)
notes = [60, 62, 63, 65, 67, 68, 70, 72, 74, 75, 79]          # rising C-minor line, one note per letter
for k in range(N):
    at = FIRST + k * STEP
    m2.place(buf, m2.tom(50 - (k % 4) * 3, 0.35), at, 0.5)
    m2.place(buf, m2.string_stab([notes[k], notes[k] + 12], 0.18), at, 0.42)
    m2.place(buf, m2.bell(notes[k] + 12, 0.5), at, 0.08)
m2.place(buf, m2.whoosh(0.4), STAB - 0.4, 0.6)
m2.place(buf, m2.impact(4.0), STAB, 1.1)
m2.place(buf, m2.brass([48, 55, 60, 63, 67, 72], 3.2), STAB, 0.7)
m2.place(buf, m2.pad([48, 55, 60, 63, 67], 4.0, 1800), STAB, 0.3)
m2.place(buf, m2.bell(84, 2.5), STAB, 0.22)
for k, mm in enumerate([72, 75, 79, 84]):                    # sparkle as PRODUCTION types in
    m2.place(buf, m2.bell(mm, 0.6), STAB + 0.45 + k * 2 * S16, 0.07)
x = np.arange(len(buf)) / SR; buf *= np.clip((D - x) / 1.6, 0, 1)
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio2", "signature.wav")
m2.write.__globals__["OUT"] = os.path.dirname(out); m2.write(os.path.basename(out), m2.st(m2.verb(buf, 0.28)))
print("wrote", out)
