"""Vijay News channel promo (~72 s): Gemini/Veo clips in promo_clips/ (optional) + brand graphics,
English voice-over and channel music (Vijay News English).  python3 promo.py promo.mp4"""
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
    ("clip", 9, "Vijay News English. Accurate news from India and the world.", "Accurate news • India & the World"),
    ("words", 9, "The biggest national, international and business stories, all in one place.", "INDIA|WORLD|BUSINESS"),
    ("clip", 9, "Every story checked with more than one reliable source.", "Verified news • 2+ sources"),
    ("card", 9, "And we show you the source of every story, right on screen.", "Source shown for every story"),
    ("clip", 9, "A fully AI-produced English news channel, live twenty-four by seven.", "Fully AI-produced • LIVE 24x7"),
    ("ai100", 8, "Vijay News English. India's one hundred percent AI news channel!", "India's 100% AI English news channel"),
    ("cta", 10, "Vijay News English. Live, twenty-four by seven.", "@VijayNewsEnglish"),
]

# Vijay, 28 Nov: "for english news other promos, use indian flag, indian parliament, and other videos with good
# quality renditions". Segment number (in SEGMENTS above) -> Pixabay searches; a hit's tags must contain one word
# from EACH group. Real camera footage only, full HD or better; an Indian photo (slow zoom) only if no video fits.
CGI_OK = {0}          # a rendered waving tricolour is standard broadcast material
NOT_FLAG = ("prayer", "mountain", "himalaya", "tibet", "nepal", "buddhist", "river", "landscape", "pakistan", "bangladesh")
PROMO_BROLL = {
    0: [("indian flag waving", [["india", "indian", "tiranga", "tricolor", "tricolour"], ["flag"]]),
        ("indian flag", [["india", "indian", "tiranga", "tricolor", "tricolour"], ["flag"]]),
        ("tiranga", [["india", "indian", "tiranga", "tricolor"], ["flag"]])],
    1: [("india gate", [["india gate"]]), ("new delhi", [["delhi"]])],
    2: [("indian parliament", [["parliament", "sansad"], ["india", "indian", "delhi"]]),
        ("parliament new delhi", [["parliament", "sansad"], ["india", "indian", "delhi"]]),
        ("sansad bhavan", [["parliament", "sansad"], ["india", "indian", "delhi"]]),
        ("rashtrapati bhavan", [["rashtrapati"]]), ("india gate delhi", [["india gate"]])],
    4: [("mumbai skyline", [["mumbai"]]), ("mumbai city", [["mumbai"]]), ("bangalore city", [["bangalore", "bengaluru"]])],
}

def promo_broll(work):
    """Download the promo backgrounds (cached in build_promo/broll). Returns {segment: path}."""
    import json, urllib.parse
    import pixabay_vis as pv
    if not os.path.exists(pv.KEYFILE): return {}
    key = open(pv.KEYFILE).read().strip(); bdir = os.path.join(work, "broll"); os.makedirs(bdir, exist_ok=True)
    got, used = {}, set()
    fake = [x for x in pv.FAKE_TAGS if x not in ("background", "loop")]   # real footage is often tagged "background"
    def has(t, w): return re.search(r"\b" + re.escape(w) + r"\b", t) is not None
    def good(h, groups, fk=fake, bad=()):
        t = (h.get("tags") or "").lower()
        return all(any(has(t, w) for w in g) for g in groups) and not any(has(t, x) for x in pv.FOREIGN_TAGS) \
            and not any(has(t, x) for x in fk) and not any(has(t, x) for x in bad)
    for seg, qs in PROMO_BROLL.items():
        fk = [] if seg in CGI_OK else fake
        bad = NOT_FLAG if seg in CGI_OK else ()
        for minw in (1920, 1280):                      # full HD first; 1280 only if nothing better exists
            for q, groups in qs:
                d = pv._get(f"https://pixabay.com/api/videos/?key={key}&q={urllib.parse.quote(q)}&safesearch=true&per_page=30&order=popular")
                for h in d.get("hits", []):
                    vid = "pxv_%s" % h.get("id")
                    if vid in used or h.get("duration", 0) < 8 or (h.get("type", "film") != "film" and seg not in CGI_OK) or not good(h, groups, fk, bad): continue
                    v = h.get("videos", {}); r = None
                    for name in ("medium", "large"):    # the smallest file that is still >= minw wide
                        x = v.get(name) or {}
                        if x.get("url") and minw <= x.get("width", 0) <= 3840 and x.get("height", 0) * 16 <= x.get("width", 0) * 9 + 32:
                            r = x; break
                    if not r: continue
                    dest = os.path.join(bdir, f"{vid}_{r['width']}.mp4")
                    if pv._download(r["url"], dest):
                        used.add(vid); got[seg] = dest; print(f"promo video {seg} '{q}': {vid} {r['width']}x{r['height']}", flush=True); break
                if seg in got: break
            if seg in got: break
        if seg not in got:                             # fallback: a large Indian photo with a slow zoom
            for q, groups in qs:
                d = pv._get(f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(q)}&image_type=photo&orientation=horizontal&safesearch=true&per_page=30&order=popular&min_width=1920")
                for h in d.get("hits", []):
                    pid = "pxp_%s" % h.get("id")
                    if pid in used or not good(h, groups, fk, bad) or not h.get("largeImageURL"): continue
                    dest = os.path.join(bdir, pid + ".jpg")
                    if pv._download(h["largeImageURL"], dest):
                        used.add(pid); got[seg] = dest; print(f"promo photo {seg} '{q}': {pid}", flush=True); break
                if seg in got: break
    return got

class Clip:
    def __init__(self, path, start=0.0):
        if path.lower().endswith((".jpg", ".jpeg", ".png")):   # a photo: slow zoom
            src = ["-loop", "1", "-framerate", str(FPS), "-i", path]
            vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
                  f"zoompan=z='min(1+0.0009*on,1.25)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={FPS}")
        else:
            src = ["-ss", str(start), "-i", path]
            vf = f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", *src, "-vf", vf,
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
    bro = promo_broll(work)
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
                           "-r", str(FPS), "-i", "-", "-i", os.path.join(work, "mix.wav"), "-c:v", "libx264", "-preset", "veryfast", "-g", "50", "-keyint_min", "50", "-sc_threshold", "0", *mb.vrate(),
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.2:LRA=9", "-ar", "44100", "-ac", "2",
                           "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    ci, cur = 0, None
    for fi in range(int(total * FPS)):
        t = fi / FPS
        if t >= base_total:
            ff.stdin.write(credit_frame(t - base_total, CR).convert("RGB").tobytes()); continue
        k = max(i for i, s in enumerate(starts) if s <= t); kind, d, line, txt = SEGMENTS[k]; lt = t - starts[k]
        kb = k - len(reel)   # segment number in the SEGMENTS table (PROMO_BROLL keys)
        if lt < 1 / FPS and kind == "words":
            cur = Clip(bro[kb]) if kb in bro else None
        if lt < 1 / FPS and kind == "clip":
            if k in seg_pres:
                cur = Clip(seg_pres[k], seg_start.get(k, 0.0))
            elif kb in bro:
                cur = Clip(bro[kb], 1.0)
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
        elif kind == "words" and cur is not None and cur.next() is not None:   # Indian landmark behind the words, dimmed
            fr = Image.blend(cur.last, Image.new("RGB", (W, H), (6, 12, 34)), 0.62).convert("RGBA")
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
                mb.rrect(d2, (60, 50, 60 + mb.text_w("AI Presenter", 30) + 40, 100), 10, (0, 0, 0, 150))
                mb.draw_text(d2, 80, 88, "AI Presenter", 30, bold=False)
        elif kind == "words":
            wds = txt.split("|"); ws = [mb.text_w(wd, 150) for wd in wds]; gap = 110
            sc_ = min(1.0, (W - 240) / (sum(ws) + gap * (len(ws) - 1))); ws = [w_ * sc_ for w_ in ws]
            xs, x_ = [], W / 2 - (sum(ws) + gap * sc_ * (len(ws) - 1)) / 2
            for w_ in ws: xs.append(int(x_ + w_ / 2)); x_ += w_ + gap * sc_
            for j, wd in enumerate(wds):
                q = mb.back((lt - 0.6 - j * 0.9) / 0.4)
                if q > 0:
                    sz = max(10, int(150 * sc_ * min(q, 1.15))); x = xs[j]
                    mb.draw_text(d2, x, 600, wd, sz, fill=(GOLD if j == 1 else WHITE), anchor="m")
            if lt > 3.6: mb.draw_text(d2, W // 2, 780, "Top stories, all in one place", 56, fill=GREY, anchor="m")
        elif kind == "times":
            for j, (lab, tm, col) in enumerate([("MORNING", "8:00", GOLD), ("EVENING", "7:00", (120, 190, 255))]):
                q = mb.back((lt - 0.5 - j * 0.8) / 0.45)
                if q <= 0: continue
                cx = W // 2 + (j * 2 - 1) * 420; yo = int((1 - min(q, 1)) * 120)
                mb.rrect(d2, (cx - 330, 300 + yo, cx + 330, 800 + yo), 40, (255, 255, 255, 26))
                d2.rectangle((cx - 330, 300 + yo, cx + 330, 314 + yo), fill=col)
                mb.draw_text(d2, cx, 430 + yo, lab, 72, fill=col, anchor="m")
                d2.text((cx, 690 + yo), tm, font=mb.font("beb", 240), fill=WHITE, anchor="ms")
                mb.draw_text(d2, cx, 770 + yo, "New bulletin", 40, fill=GREY, anchor="m")
        elif kind == "card":
            q = mb.back((lt - 0.4) / 0.5); yo = int((1 - min(q, 1)) * 200)
            mb.rrect(d2, (360, 260 + yo, 1560, 760 + yo), 36, (255, 255, 255, 24))
            mb.rrect(d2, (420, 330 + yo, 600, 384 + yo), 12, RED); mb.draw_text(d2, 450, 372 + yo, "INDIA", 32)
            mb.draw_text(d2, 420, 480 + yo, "The headline goes here", 64)
            for j in range(2): mb.rrect(d2, (420, 520 + yo + j * 70, 1100 - j * 180, 570 + yo + j * 70), 10, (255, 255, 255, 30))
            if lt > 1.5:
                hl = mb.ease((lt - 1.5) / 0.4)
                mb.rrect(d2, (410, 670 + yo, 410 + 560 * hl, 730 + yo), 12, GOLD + (235,))
                if hl > 0.7: mb.draw_text(d2, 432, 715 + yo, "Source: verified news agencies", 34, fill=NAVY)
            if a > 0: mb.draw_text(d2, W // 2, 900, txt, 64, anchor="m")
        elif kind == "ai100":   # big "100% AI" statement
            q = mb.back((lt - 0.3) / 0.5); sc = max(0.01, min(q, 1.12))
            f = mb.font("beb", int(330 * sc)); d2.text((W // 2, 560), "100% AI", font=f, fill=GOLD, anchor="ms")
            b = mb.ease((lt - 1.2) / 0.5)
            if b > 0:
                mb.draw_text(d2, W // 2, 700, txt, 76, fill=(255, 255, 255, int(255 * b)), anchor="m")
                d2.rectangle((W // 2 - int(520 * b), 750, W // 2 + int(520 * b), 757), fill=RED)
            c = mb.ease((lt - 2.2) / 0.5)
            if c > 0: mb.draw_text(d2, W // 2, 850, "AI voice • AI production • every story checked with 2+ sources", 44, fill=(200, 210, 230, int(255 * c)), anchor="m", bold=False)
        else:  # cta
            q = mb.back((lt - 0.3) / 0.5)
            lg = LOGO.resize((int(300 * min(q, 1.1)) or 1, int(300 * min(q, 1.1)) or 1)); L.alpha_composite(lg, (W // 2 - lg.width // 2, 140))
            L.alpha_composite(WM, (W // 2 - WM.width // 2, 470))
            b = mb.ease((lt - 1.2) / 0.5); pulse = 1 + 0.035 * math.sin(lt * 5)
            bw = (mb.text_w("24x7 English News LIVE", 54) + 140) * pulse; bx = W // 2 - bw / 2
            if b > 0:
                mb.rrect(d2, (bx, 740, bx + bw, 740 + 110 * pulse), 55, RED + (int(255 * b),))
                mb.draw_text(d2, W // 2, 740 + 76 * pulse, "24x7 English News LIVE", 54, fill=(255, 255, 255, int(255 * b)), anchor="m")
                d2.text((W // 2, 950), txt, font=mb.font("latr", 40), fill=GREY, anchor="ms")
            if lt > d - 1.0: L.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (lt - d + 1.0)))))
        fr.alpha_composite(L)
        kk = math.exp(-lt * 9) if lt < 0.5 and k else 0
        if kk > 0.02: fr = mb.punch(fr, kk, fi)
        ff.stdin.write(fr.convert("RGB").tobytes())
    ff.stdin.close(); ff.wait(); print("done", out, f"{total:.1f}s", f"{len(pres)} presenter + {len(clips)} other clips")
    # Vijay, 28 Nov: reuse the Vijay News office walkthrough from the Kannada promo (English captions; the Kannada
    # sign and end slate cut out) – it plays just before the end card, like on the Kannada channel.
    ow = os.path.join(HERE, "branding", "office_walkthrough_en.mp4")
    if CR and os.path.exists(ow):
        cut = base_total; tmp = out[:-4] + "_ow.mp4"
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", out, "-i", ow, "-filter_complex",
            f"[0:v]trim=0:{cut},setpts=PTS-STARTPTS[v1];[0:a]atrim=0:{cut},asetpts=PTS-STARTPTS,afade=t=out:st={cut - 0.3}:d=0.3[a1];"
            f"[1:v]fps={FPS},scale={W}:{H},setsar=1,setpts=PTS-STARTPTS[v2];[1:a]aresample=44100,loudnorm=I=-16:TP=-1.5,asetpts=PTS-STARTPTS[a2];"
            f"[0:v]trim={cut},setpts=PTS-STARTPTS[v3];[0:a]atrim={cut},asetpts=PTS-STARTPTS,afade=t=in:d=0.2[a3];"
            "[v1][a1][v2][a2][v3][a3]concat=n=3:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-g", "50", "-keyint_min", "50", "-sc_threshold", "0", *mb.vrate(),
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", tmp])
        if r.returncode == 0: os.replace(tmp, out); print("office walkthrough added before the end card", flush=True)
        else: print("office walkthrough NOT added", flush=True)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "promo.mp4")
