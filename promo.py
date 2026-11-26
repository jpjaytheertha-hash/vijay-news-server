"""Vijay News channel promo (~72 s): Gemini/Veo clips in promo_clips/ (optional) + brand graphics,
Kannada voice-over and channel music.  python3 promo.py promo.mp4"""
import os, sys, glob, subprocess, math, re
import numpy as np
from PIL import Image, ImageDraw
from scipy.io import wavfile
import make_bulletin as mb
import brand
from tts import synth

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = mb.W, mb.H, mb.FPS, mb.SR
GOLD, RED, WHITE, NAVY, GREY = mb.GOLD, mb.RED, mb.WHITE, mb.NAVY, mb.GREY

# (kind, seconds, voice line, on-screen text)
SEGMENTS = [
    ("clip", 9, "ವಿಜಯ್ ನ್ಯೂಸ್. ನಿಖರ ಸುದ್ದಿ, ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ.", "ನಿಖರ ಸುದ್ದಿ • ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ"),
    ("words", 9, "ರಾಜ್ಯ, ದೇಶ ಮತ್ತು ವಿದೇಶದ ಪ್ರಮುಖ ಸುದ್ದಿಗಳು, ಒಂದೇ ಕಡೆ.", "ರಾಜ್ಯ|ದೇಶ|ವಿದೇಶ"),
    ("clip", 9, "ಪ್ರತಿದಿನ ಎರಡು ಬಾರಿ, ಹೊಸ ಸುದ್ದಿ ಬುಲೆಟಿನ್.", "ಪ್ರತಿದಿನ ಎರಡು ಹೊಸ ಬುಲೆಟಿನ್"),
    ("times", 9, "ಬೆಳಿಗ್ಗೆ ಏಳು ಗಂಟೆ, ಮತ್ತು ಸಂಜೆ ಆರು ಗಂಟೆಗೆ.", ""),
    ("clip", 9, "ಹಲವು ಮೂಲಗಳಿಂದ ಪರಿಶೀಲಿಸಿದ ಸುದ್ದಿ, ಸ್ಪಷ್ಟ ಕನ್ನಡದಲ್ಲಿ.", "ಪರಿಶೀಲಿಸಿದ ಸುದ್ದಿ • ಸ್ಪಷ್ಟ ಕನ್ನಡ"),
    ("card", 9, "ಪ್ರತಿ ಸುದ್ದಿಯ ಮೂಲವನ್ನೂ ತೆರೆಯ ಮೇಲೆ ತೋರಿಸುತ್ತೇವೆ.", "ಪ್ರತಿ ಸುದ್ದಿಗೂ ಮೂಲ ಉಲ್ಲೇಖ"),
    ("clip", 9, "ಸಂಪೂರ್ಣವಾಗಿ ಎಐ ನಡೆಸುವ ಕನ್ನಡ ಸುದ್ದಿ ವಾಹಿನಿ, ದಿನದ ಇಪ್ಪತ್ನಾಲ್ಕು ಗಂಟೆಯೂ ಲೈವ್.", "ಸಂಪೂರ್ಣ AI ಸುದ್ದಿ ವಾಹಿನಿ • 24 x 7 ಲೈವ್"),
    ("ai100", 8, "ವಿಜಯ್ ನ್ಯೂಸ್ ಕನ್ನಡ, ಕನ್ನಡದ ನೂರಕ್ಕೆ ನೂರು ಎಐ ನ್ಯೂಸ್ ಚಾನೆಲ್!", "ಕನ್ನಡದ 100% AI ನ್ಯೂಸ್ ಚಾನೆಲ್"),
    ("cta", 10, "ವಿಜಯ್ ನ್ಯೂಸ್ ಕನ್ನಡ – ದಿನದ ಇಪ್ಪತ್ನಾಲ್ಕು ಗಂಟೆಯೂ ಲೈವ್.", "@VijayNewsKannada"),
]

class Clip:
    def __init__(self, path, start=0.0):
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(start), "-i", path, "-vf",
                                   f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = None
    def next(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3: self.last = Image.frombytes("RGB", (W, H), b)
        return self.last

def load(p):
    sr, x = wavfile.read(p); x = x.astype(np.float32) / 32768
    return np.stack([x, x], 1) if x.ndim == 1 else x

def main(out):
    work = os.path.join(HERE, "build_promo"); os.makedirs(work, exist_ok=True)
    allc = sorted(glob.glob(os.path.join(HERE, "promo_clips", "*.mp4")))
    pres = [c for c in allc if os.path.basename(c).startswith("presenter")]   # Gemini/Veo AI presenter in a suit
    clips = [c for c in allc if c not in pres]
    probe = lambda c: float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", c],
                                           capture_output=True, text=True).stdout or 0)
    global SEGMENTS
    # Presenter reel (Vijay, 25 Nov: "create such short videos and stitch and keep playing such 3-5 promo videos"):
    # every clip in presenter_promos/ plays back-to-back at the start, trimmed to the speech, with the AI label.
    def speech_bounds(c):
        log = subprocess.run(["ffmpeg", "-i", c, "-af", "silencedetect=n=-35dB:d=0.35", "-vn", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        dur = probe(c); st_ = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
        en_ = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
        a = en_[0] if st_ and st_[0] < 0.05 and en_ else 0.0          # speech starts after the leading silence
        b = st_[-1] if st_ and (not en_ or st_[-1] > en_[-1]) else dur  # speech ends at the trailing silence
        return max(0.0, a - 0.35), min(dur, b + 0.9)
    reel = sorted(c for c in glob.glob(os.path.join(HERE, "presenter_promos", "*.mp4")) if os.path.getsize(c) > 20000)
    SEGMENTS = [["clip", 0, "", ""] for _ in reel] + [list(x) for x in SEGMENTS]; seg_pres = {}; seg_start = {}
    for k, c in enumerate(reel):
        a, b = speech_bounds(c); seg_pres[k] = c; seg_start[k] = a; SEGMENTS[k][1] = max(2.5, min(b - a, 12.0))
    for j, k in enumerate([i for i, x in enumerate(SEGMENTS) if x[0] == "clip" and i >= len(reel)][:len(pres)]):
        seg_pres[k] = pres[j]; SEGMENTS[k][1] = max(4.0, min(probe(pres[j]), 10.0)) + 0.4
    total = sum(s[1] for s in SEGMENTS)
    sig_p = os.path.join(HERE, "audio2", "signature.wav"); CR = 7.5 if os.path.exists(sig_p) else 0.0
    base_total = total; total = base_total + CR
    credit_frame = mb.build_credit() if CR else None
    # ---- audio
    music = os.path.join(HERE, os.environ.get("VN_MUSIC", "audio2"))
    intro, bed, sting, outro = (load(os.path.join(music, n)) for n in ("intro.wav", "bed.wav", "sting.wav", "outro.wav"))
    mix = np.zeros((int((total + 1) * SR), 2), np.float32)
    def put(sig, at, g):
        i = int(at * SR); j = min(len(mix), i + len(sig)); mix[i:j] += sig[:j - i] * g
    n = len(mix); put(np.tile(bed, (n // len(bed) + 1, 1))[:n], 0, 0.22)
    put(intro, 0, 0.55)
    # Puck (Google) voice for the promo lines, like the bulletins – human-sounding; cached, so only new lines cost requests
    need = [(f"v{k}", line) for k, (kind, d, line, txt) in enumerate(SEGMENTS)
            if not (k in seg_pres and "_vo" not in os.path.basename(seg_pres[k]))]
    puck = False
    try:
        import tts as _t
        if os.environ.get("VN_TTS", "auto") in ("auto", "gemini") and os.path.exists(_t.GEMINI_KEYFILE):
            ks = [k for k, _ in need]
            _t.synth_batch(need, work, groups=[ks[i:i + 3] for i in range(0, len(ks), 3)]); puck = True
            print("promo voice: Google Puck", flush=True)
    except Exception as e:
        # Vijay: keep the Puck reader – use every line already recorded in Puck; a line that is missing is
        # left silent (its text still shows on screen) instead of switching the whole promo to Microsoft.
        import tts as _t
        have = _t.puck_cached(need, work)
        if need and len(have) >= len(need) - 2:
            for k_, a_ in have.items():
                _t.write_clip(a_, work, k_)
            for k_, _ in need:
                if k_ not in have:
                    try: os.remove(os.path.join(work, k_ + ".wav"))
                    except OSError: pass
            puck = True
            print(f"promo voice: Google Puck (cached; silent: {[k_ for k_, _ in need if k_ not in have]})", flush=True)
        else:
            print("promo voice: Google failed, Microsoft used:", str(e)[:120], flush=True)
    t = 0; starts = []
    for k, (kind, d, line, txt) in enumerate(SEGMENTS):
        starts.append(t)
        if k: put(sting, t - 0.65, 0.5)
        wav = os.path.join(work, f"v{k}.wav")
        if k in seg_pres and "_vo" not in os.path.basename(seg_pres[k]):   # presenter speaks: use the clip's own sound
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(seg_start.get(k, 0.0)), "-t", str(d), "-i", seg_pres[k],
                            "-vn", "-ac", "2", "-ar", str(SR), "-af", "afade=t=in:d=0.12,afade=t=out:st=%.2f:d=0.25" % max(0.1, d - 0.3), wav], check=True)
            put(load(wav), t, 1.0)
        else:
            if not puck: synth(line, wav)
            if os.path.exists(wav): put(load(wav), t + 0.8, 1.0)
        t += d
    put(outro, base_total - 7.0, 0.8)
    if CR: put(load(sig_p), base_total, 1.0)   # "A VIJAY MELPAL PRODUCTION" with the beats signature
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    wavfile.write(os.path.join(work, "mix.wav"), SR, (mix * 32767).astype(np.int16))
    # ---- video
    bg = mb.make_bg(); LOGO = brand.mark(300); WM = brand.wordmark(90); WMS = brand.wordmark(46, kn=False)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", os.path.join(work, "mix.wav"), "-c:v", "libx264", "-preset", "veryfast", "-g", "50", "-keyint_min", "50", "-sc_threshold", "0", "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.2:LRA=9", "-ar", "44100", "-ac", "2",
                           "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    ci, cur = 0, None
    for fi in range(int(total * FPS)):
        t = fi / FPS
        if t >= base_total:
            ff.stdin.write(credit_frame(t - base_total, CR).convert("RGB").tobytes()); continue
        k = max(i for i, s in enumerate(starts) if s <= t); kind, d, line, txt = SEGMENTS[k]; lt = t - starts[k]
        if lt < 1 / FPS and kind == "clip":
            if k in seg_pres:
                cur = Clip(seg_pres[k], seg_start.get(k, 0.0))
            elif clips:
                path = clips[ci % len(clips)]
                dur_c = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                             capture_output=True, text=True).stdout or 0)
                start = ((ci // len(clips)) * 9.5) % max(1.0, dur_c - d) if dur_c > d else 0.0
                cur = Clip(path, start)
            else:
                cur = None
            ci += 1
        off = int((t * 18) % 600); fr = bg.crop((off, 0, off + W, H)).convert("RGBA")
        if kind == "clip" and cur is not None and cur.next() is not None:
            fr = cur.last.convert("RGBA")
            shade = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
            for y in range(H // 2, H, 8): sd.rectangle((0, y, W, y + 8), fill=(5, 10, 30, int(200 * (y - H / 2) / (H / 2))))
            fr.alpha_composite(shade)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d2 = ImageDraw.Draw(L)
        a = mb.ease((lt - 0.4) / 0.5)
        if kind == "clip":
            if k == 0:
                q = mb.back((lt - 1.0) / 0.5)
                if q > 0:
                    lg = LOGO.resize((int(220 * min(q, 1.2)), int(220 * min(q, 1.2))))
                    L.alpha_composite(lg, (120, 640 - lg.height // 2))
                    L.alpha_composite(WM, (380, 560))
            w = mb.text_w(txt, 64) + 80; x0 = 120 if k else 380; y0 = 880
            if a > 0 and txt:
                mb.rrect(d2, (x0 - 30, y0 - 78, x0 - 30 + w * a, y0 + 28), 14, RED + (230,))
                if a > 0.6: mb.draw_text(d2, x0 + 10, y0, txt, 64)
            L.alpha_composite(WMS, (W - WMS.width - 60, 50))
            if k in seg_pres:   # disclosure: the presenter is AI-generated
                mb.rrect(d2, (60, 50, 60 + mb.text_w("AI ನಿರೂಪಕ", 30) + 40, 100), 10, (0, 0, 0, 150))
                mb.draw_text(d2, 80, 88, "AI ನಿರೂಪಕ", 30, bold=False)
        elif kind == "words":
            for j, wd in enumerate(txt.split("|")):
                q = mb.back((lt - 0.6 - j * 0.9) / 0.4)
                if q > 0:
                    sz = max(10, int(150 * min(q, 1.15))); x = W // 2 + (j - 1) * 560
                    mb.draw_text(d2, x, 600, wd, sz, fill=(GOLD if j == 1 else WHITE), anchor="m")
            if lt > 3.6: mb.draw_text(d2, W // 2, 780, "ಪ್ರಮುಖ ಸುದ್ದಿಗಳು, ಒಂದೇ ಕಡೆ", 56, fill=GREY, anchor="m")
        elif kind == "times":
            for j, (lab, tm, col) in enumerate([("ಬೆಳಿಗ್ಗೆ", "7:00", GOLD), ("ಸಂಜೆ", "6:00", (120, 190, 255))]):
                q = mb.back((lt - 0.5 - j * 0.8) / 0.45)
                if q <= 0: continue
                cx = W // 2 + (j * 2 - 1) * 420; yo = int((1 - min(q, 1)) * 120)
                mb.rrect(d2, (cx - 330, 300 + yo, cx + 330, 800 + yo), 40, (255, 255, 255, 26))
                d2.rectangle((cx - 330, 300 + yo, cx + 330, 314 + yo), fill=col)
                mb.draw_text(d2, cx, 430 + yo, lab, 72, fill=col, anchor="m")
                d2.text((cx, 690 + yo), tm, font=mb.font("beb", 240), fill=WHITE, anchor="ms")
                mb.draw_text(d2, cx, 770 + yo, "ಹೊಸ ಬುಲೆಟಿನ್", 40, fill=GREY, anchor="m")
        elif kind == "card":
            q = mb.back((lt - 0.4) / 0.5); yo = int((1 - min(q, 1)) * 200)
            mb.rrect(d2, (360, 260 + yo, 1560, 760 + yo), 36, (255, 255, 255, 24))
            mb.rrect(d2, (420, 330 + yo, 600, 384 + yo), 12, RED); mb.draw_text(d2, 450, 372 + yo, "ರಾಜ್ಯ", 32)
            mb.draw_text(d2, 420, 480 + yo, "ಸುದ್ದಿಯ ಶೀರ್ಷಿಕೆ ಇಲ್ಲಿ", 64)
            for j in range(2): mb.rrect(d2, (420, 520 + yo + j * 70, 1100 - j * 180, 570 + yo + j * 70), 10, (255, 255, 255, 30))
            if lt > 1.5:
                hl = mb.ease((lt - 1.5) / 0.4)
                mb.rrect(d2, (410, 670 + yo, 410 + 560 * hl, 730 + yo), 12, GOLD + (235,))
                if hl > 0.7: mb.draw_text(d2, 432, 715 + yo, "ಮೂಲ: ಪರಿಶೀಲಿತ ಸುದ್ದಿ ಸಂಸ್ಥೆಗಳು", 34, fill=NAVY)
            if a > 0: mb.draw_text(d2, W // 2, 900, txt, 64, anchor="m")
        elif kind == "ai100":   # big "100% AI" statement
            q = mb.back((lt - 0.3) / 0.5); sc = max(0.01, min(q, 1.12))
            f = mb.font("beb", int(330 * sc)); d2.text((W // 2, 560), "100% AI", font=f, fill=GOLD, anchor="ms")
            b = mb.ease((lt - 1.2) / 0.5)
            if b > 0:
                mb.draw_text(d2, W // 2, 700, txt, 76, fill=(255, 255, 255, int(255 * b)), anchor="m")
                d2.rectangle((W // 2 - int(520 * b), 750, W // 2 + int(520 * b), 757), fill=RED)
            c = mb.ease((lt - 2.2) / 0.5)
            if c > 0: mb.draw_text(d2, W // 2, 850, "AI ನಿರೂಪಕ • AI ಧ್ವನಿ • ಪ್ರತಿ ಸುದ್ದಿ 2+ ಮೂಲಗಳಿಂದ ಪರಿಶೀಲನೆ", 44, fill=(200, 210, 230, int(255 * c)), anchor="m", bold=False)
        else:  # cta
            q = mb.back((lt - 0.3) / 0.5)
            lg = LOGO.resize((int(300 * min(q, 1.1)) or 1, int(300 * min(q, 1.1)) or 1)); L.alpha_composite(lg, (W // 2 - lg.width // 2, 140))
            L.alpha_composite(WM, (W // 2 - WM.width // 2, 470))
            b = mb.ease((lt - 1.2) / 0.5); pulse = 1 + 0.035 * math.sin(lt * 5)
            bw = (mb.text_w("24x7 ಕನ್ನಡ ನ್ಯೂಸ್ ಲೈವ್", 54) + 140) * pulse; bx = W // 2 - bw / 2
            if b > 0:
                mb.rrect(d2, (bx, 740, bx + bw, 740 + 110 * pulse), 55, RED + (int(255 * b),))
                mb.draw_text(d2, W // 2, 740 + 76 * pulse, "24x7 ಕನ್ನಡ ನ್ಯೂಸ್ ಲೈವ್", 54, fill=(255, 255, 255, int(255 * b)), anchor="m")
                d2.text((W // 2, 950), txt, font=mb.font("latr", 40), fill=GREY, anchor="ms")
            if lt > d - 1.0: L.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (lt - d + 1.0)))))
        fr.alpha_composite(L)
        kk = math.exp(-lt * 9) if lt < 0.5 and k else 0
        if kk > 0.02: fr = mb.punch(fr, kk, fi)
        ff.stdin.write(fr.convert("RGB").tobytes())
    ff.stdin.close(); ff.wait(); print("done", out, f"{total:.1f}s", f"{len(pres)} presenter + {len(clips)} other clips")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "promo.mp4")
