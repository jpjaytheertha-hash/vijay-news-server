"""Vijay News bulletin renderer.
python3 make_bulletin.py bulletin.json out.mp4
Needs: ffmpeg, Pillow (with raqm), numpy, scipy; music in ./audio (python3 music.py audio)
"""
import json, os, sys, subprocess, math, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.io import wavfile
from tts import synth, synth_batch, GEMINI_KEYFILE
import brand

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1920, 1080, 25, 44100
HIT1, HIT2, OPEN_LEN = 1.2, 8.06, 10.2  # logo slam / final hit / opening length (match music2.py)
F = lambda n: os.path.join(HERE, "fonts", n)
NAVY, NAVY2 = (8, 18, 44), (16, 36, 82)
RED, GOLD, WHITE, GREY = (225, 29, 46), (245, 183, 10), (255, 255, 255), (170, 182, 205)

_fc = {}
def font(kind, size):
    path = {"kn": F("NotoSansKannada-700.ttf"), "knr": F("NotoSansKannada-400.ttf"),
            "lat": F("inter-latin-800-normal.ttf"), "latr": F("inter-latin-600-normal.ttf"),
            "beb": F("bebas-neue-latin-400-normal.ttf")}[kind]
    k = (path, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _fc[k]

def is_kn(ch): return 0x0C80 <= ord(ch) <= 0x0CFF or ch in "‌‍"

def runs(text):
    out = []
    for ch in text:
        k = is_kn(ch) if ch != " " else (out[-1][0] if out else False)
        if out and out[-1][0] == k: out[-1][1] += ch
        else: out.append([k, ch])
    return out

def text_w(text, size, bold=True):
    return sum(font(("kn" if bold else "knr") if k else ("lat" if bold else "latr"), size if k else int(size * .92)).getlength(s)
               for k, s in runs(text))

def draw_text(d, x, y, text, size, fill=WHITE, bold=True, anchor="l"):
    """y is baseline. anchor l/m/r horizontally."""
    w = text_w(text, size, bold)
    if anchor == "m": x -= w / 2
    elif anchor == "r": x -= w
    for k, s in runs(text):
        f = font(("kn" if bold else "knr") if k else ("lat" if bold else "latr"), size if k else int(size * .92))
        d.text((x, y), s, font=f, fill=fill, anchor="ls"); x += f.getlength(s)
    return w

def wrap(text, size, maxw, bold=True):
    lines, cur = [], ""
    for wd in text.split(" "):
        t = (cur + " " + wd).strip()
        if text_w(t, size, bold) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines

def back(x):
    x = min(max(x, 0), 1); c = 1.9; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def punch(fr, k, seed):
    """camera shake + zoom punch + RGB split, k in 0..1"""
    if k <= 0.02: return fr
    r = np.random.default_rng(seed)
    z = 1 + 0.06 * k; w2, h2 = int(W * z), int(H * z)
    big = fr.resize((w2, h2), Image.BILINEAR)
    dx, dy = (r.uniform(-1, 1, 2) * 22 * k).astype(int)
    x0, y0 = (w2 - W) // 2 + dx, (h2 - H) // 2 + dy
    out = big.crop((x0, y0, x0 + W, y0 + H))
    sp = int(12 * k)
    if sp:
        R, G, Bc = out.split()[:3]
        R = R.transform(out.size, Image.AFFINE, (1, 0, sp, 0, 1, 0)); Bc = Bc.transform(out.size, Image.AFFINE, (1, 0, -sp, 0, 1, 0))
        out = Image.merge("RGB", (R, G, Bc)).convert("RGBA")
    return out

def ease(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def rrect(d, box, r, fill): d.rounded_rectangle(box, r, fill=fill)

# ---------------------------------------------------------------- static art
def make_bg():
    g = np.linspace(0, 1, H)[:, None, None]
    col = np.array(NAVY, np.float32) * (1 - g) + np.array(NAVY2, np.float32) * g  # H,1,3
    img = Image.fromarray(np.repeat(col, W + 600, 1).astype(np.uint8))
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i in range(-4, 30):
        x = i * 120
        d.polygon([(x, H), (x + 60, H), (x + 60 + 700, 0), (x + 700, 0)], fill=(255, 255, 255, 7 if i % 3 else 13))
    for yy in range(40, H, 60):
        for xx in range(30, W + 600, 60): d.ellipse((xx, yy, xx + 3, yy + 3), fill=(255, 255, 255, 18))
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    gd.ellipse((W - 500, -400, W + 700, 700), fill=(225, 29, 46, 50)); gd.ellipse((-500, 600, 700, 1600), fill=(60, 110, 255, 40))
    return Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(160))).convert("RGB")

def logo(size):
    s = size; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=GOLD); m = int(s * .06)
    d.ellipse((m, m, s - m, s - m), fill=RED)
    f = font("beb", int(s * .78)); d.text((s / 2, s * .54), "V", font=f, fill=WHITE, anchor="mm")
    d.arc((m * 2, m * 2, s - m * 2, s - m * 2), 200, 340, fill=(255, 255, 255, 120), width=max(2, s // 60))
    return im

def icon(kind, s=150):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); w = max(4, s // 18)
    if kind == "calendar":
        rrect(d, (s*.1, s*.18, s*.9, s*.9), s*.08, (255, 255, 255, 235)); d.rectangle((s*.1, s*.18, s*.9, s*.38), fill=RED)
        for x in (.3, .7): rrect(d, (s*x - w, s*.08, s*x + w, s*.28), w, GOLD)
        for r in range(2):
            for c in range(4): d.rectangle((s*(.18 + c*.17), s*(.48 + r*.18), s*(.28 + c*.17), s*(.58 + r*.18)), fill=NAVY2)
    elif kind == "pin":
        d.ellipse((s*.2, s*.05, s*.8, s*.65), fill=RED); d.polygon([(s*.24, s*.45), (s*.76, s*.45), (s*.5, s*.95)], fill=RED)
        d.ellipse((s*.38, s*.2, s*.62, s*.44), fill=WHITE)
    elif kind == "thermo":
        rrect(d, (s*.4, s*.05, s*.6, s*.7), s*.1, (255, 255, 255, 235)); d.ellipse((s*.28, s*.58, s*.72, s*.98), fill=(80, 170, 255))
        d.rectangle((s*.46, s*.45, s*.54, s*.7), fill=(80, 170, 255))
        for y in (.18, .3, .42): d.line((s*.62, s*y, s*.72, s*y), fill=WHITE, width=w // 2)
    elif kind == "globe":
        d.ellipse((s*.06, s*.06, s*.94, s*.94), outline=WHITE, width=w)
        d.ellipse((s*.3, s*.06, s*.7, s*.94), outline=WHITE, width=w // 1)
        d.line((s*.5, s*.06, s*.5, s*.94), fill=WHITE, width=w); d.line((s*.06, s*.5, s*.94, s*.5), fill=WHITE, width=w)
        for y in (.28, .72): d.line((s*.15, s*y, s*.85, s*y), fill=WHITE, width=w // 2)
    return im

# ---------------------------------------------------------------- audio
def load(path):
    sr, x = wavfile.read(path); x = x.astype(np.float32) / 32768
    if x.ndim == 1: x = np.stack([x, x], 1)
    return x

class Anchor:
    """Streams a presenter clip (green-screen mp4/mov, or transparent .webm/.mov) as RGBA frames."""
    def __init__(self, path, height):
        self.path, self.h = path, height
        info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,codec_name",
                               "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
        codec, w0, h0 = info[0], int(info[1]), int(info[2])
        self.w = int(round(w0 * height / h0 / 2) * 2)
        key = os.environ.get("VN_KEY", "0x00FF00")
        pre, vf = [], f"fps={FPS},scale={self.w}:{height}"
        if path.lower().endswith(".webm"): pre = ["-c:v", "libvpx-vp9"] if codec == "vp9" else ["-c:v", "libvpx"]
        elif os.environ.get("VN_ALPHA") != "1": vf = f"fps={FPS},chromakey={key}:0.16:0.05,despill=type=green,scale={self.w}:{height}"
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", *pre, "-i", path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                                  stdout=subprocess.PIPE)
        self.n, self.last, self.first = 0, None, None
        self._read()
        self.first = self.last
    def _read(self):
        b = self.p.stdout.read(self.w * self.h * 4)
        if len(b) < self.w * self.h * 4: return False
        self.last = Image.frombytes("RGBA", (self.w, self.h), b); self.n += 1; return True
    def at(self, lt):
        """frame for local time lt (seconds since voice start)"""
        if lt < 0: return self.first
        want = int(lt * FPS) + 1
        while self.n < want and self._read(): pass
        return self.last

class BRoll:
    """Short AI visual for one story, shown in the left panel: video (looped) or still image (slow zoom)."""
    BW, BH = 630, 354
    def __init__(self, path, length, size=None):
        self.path, self.len = path, max(1.0, length)
        if size: self.BW, self.BH = size
        self.video = path.lower().endswith((".mp4", ".mov", ".webm", ".m4v"))
        self.mask = Image.new("L", (self.BW, self.BH), 0); ImageDraw.Draw(self.mask).rounded_rectangle((0, 0, self.BW - 1, self.BH - 1), 28, fill=255)
        if self.video:
            vf = f"fps={FPS},scale={self.BW}:{self.BH}:force_original_aspect_ratio=increase,crop={self.BW}:{self.BH}"
            self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-i", path, "-an", "-vf", vf,
                                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
            self.n, self.last = 0, None; self._read()
        else:
            im = Image.open(path).convert("RGB"); z = 1.18
            sc = max(self.BW * z / im.width, self.BH * z / im.height)
            self.img = im.resize((int(im.width * sc) + 2, int(im.height * sc) + 2), Image.LANCZOS)
    def _read(self):
        b = self.p.stdout.read(self.BW * self.BH * 3)
        if len(b) < self.BW * self.BH * 3: return False
        self.last = Image.frombytes("RGB", (self.BW, self.BH), b); self.n += 1; return True
    def at(self, lt):
        if self.video:
            want = int(max(0, lt) * FPS) + 1
            while self.n < want and self._read(): pass
            return self.last
        u = min(1, max(0, lt / self.len)); u = u * u * (3 - 2 * u)
        iw, ih = self.img.size; cw = int(iw - (iw - self.BW * 1.0) * u * 0.85); ch = int(cw * self.BH / self.BW)
        x0 = int((iw - cw) * (0.35 + 0.3 * u)); y0 = int((ih - ch) * 0.45)
        return self.img.crop((x0, y0, x0 + cw, y0 + ch)).resize((self.BW, self.BH), Image.BILINEAR)
    def close(self):
        if self.video and self.p.poll() is None: self.p.kill()

class MultiBRoll:
    """Vijay, 27 Nov: 2–3 short clips for one story (topic, place landmark, second topic) – the story time is
    split evenly between them; each clip loops if it is shorter than its share. Clips start lazily.
    Vijay, 27 Nov (later): "each line of the story should be analysed and prepare the video clips" – with `starts`
    (fractions 0..1 of the story time, one per clip) each clip begins when its sentence is read; `kinds` says which
    on-screen label each clip gets ("pixabay", "ai" or "official")."""
    def __init__(self, paths, length, size=None, starts=None, kinds=None):
        self.paths, self.len, self.size = paths, max(1.0, length), size
        n = len(paths); self.seg = self.len / n; self.subs = [None] * n; self.mask = None
        st = list(starts) if starts and len(starts) == n else [j / n for j in range(n)]
        st[0] = 0.0
        for j in range(1, n): st[j] = min(max(st[j], st[j - 1] + 0.12), 1.0)   # every clip shows ≥12 % of the story
        self.t0 = [x * self.len for x in st] + [self.len]
        self.kinds = list(kinds) if kinds and len(kinds) == n else None
    def index(self, lt):
        j = 0
        while j + 1 < len(self.paths) and lt >= self.t0[j + 1]: j += 1
        return j
    def _sub(self, j):
        if self.subs[j] is None:
            self.subs[j] = BRoll(self.paths[j], max(1.0, self.t0[j + 1] - self.t0[j]), self.size)
            for k in range(len(self.subs)):
                if k != j and self.subs[k]: self.subs[k].close(); self.subs[k] = False
        return self.subs[j]
    def at(self, lt):
        j = self.index(max(0, lt))
        if self.subs[j] is False: self.subs[j] = None
        return self._sub(j).at(lt - self.t0[j])
    def close(self):
        for b in self.subs:
            if b: b.close()

def paste_clip(fr, im, cx, bottom):
    x0, y0 = int(cx - im.width / 2), int(bottom - im.height)
    sx0, sy0 = max(0, -x0), max(0, -y0); x1, y1 = min(W, x0 + im.width), min(H, y0 + im.height)
    if x1 > max(0, x0) and y1 > max(0, y0):
        fr.alpha_composite(im.crop((sx0, sy0, sx0 + x1 - max(0, x0), sy0 + y1 - max(0, y0))), (max(0, x0), max(0, y0)))

def build_credit():
    """returns credit_frame(lt, ln) -> RGBA frame of the gold 'A VIJAY MELPAL PRODUCTION' end card"""
    def gold_text(txt, fnt, spacing=0):
        """text filled with a vertical gold gradient, soft glow behind"""
        f = font(fnt[0], fnt[1]); w = int(sum(f.getlength(c) for c in txt) + spacing * (len(txt) - 1)) + 40
        h = int(fnt[1] * 1.3) + 40
        m = Image.new("L", (w, h), 0); md = ImageDraw.Draw(m); x = 20
        for c in txt: md.text((x, 20), c, font=f, fill=255); x += f.getlength(c) + spacing
        g = np.linspace(0, 1, h)[:, None]
        top, mid, bot = np.array([255, 236, 160]), np.array([232, 178, 48]), np.array([150, 98, 18])
        col = np.where(g < .5, top + (mid - top) * (g / .5)[..., None], mid + (bot - mid) * ((g - .5) / .5)[..., None])[:, 0, :]
        grad = Image.fromarray(np.repeat(col[:, None, :], w, 1).astype(np.uint8), "RGB").convert("RGBA")
        grad.putalpha(m)
        glow = Image.new("RGBA", (w, h), (255, 190, 60, 0)); glow.putalpha(m.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .55)))
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0)); out.alpha_composite(glow); out.alpha_composite(grad)
        return out, m
    CR_A, _ = gold_text("A", ("latr", 64))
    CR_NAME, CR_MASK = gold_text("VIJAY MELPAL", ("beb", 250), spacing=14)
    CR_PROD, _ = gold_text("PRODUCTION", ("beb", 118), spacing=34)
    CR_BG = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    yy, xx = np.mgrid[0:H, 0:W]; rad = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
    v = np.clip(1 - rad * 1.6, 0, 1)
    CR_BG = Image.fromarray(np.stack([18 + 30 * v, 10 + 18 * v, 4 + 6 * v, np.full_like(v, 255)], -1).astype(np.uint8), "RGBA")
    rs = np.random.default_rng(7); SPARK = rs.random((90, 4))
    def credit_frame(lt, ln):
        fr = CR_BG.copy(); d = ImageDraw.Draw(fr)
        for (sx, sy, ss, sp) in SPARK:   # drifting gold dust
            x = int(sx * W); y = int((sy * H - lt * (20 + 60 * sp)) % H); r = 1 + int(ss * 3)
            a = int(120 + 120 * math.sin(lt * (2 + 4 * sp) + sx * 9))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 210, 110, max(0, a)))
        hit = 1.0
        a = ease((lt - 0.2) / 0.6)
        if a > 0:
            q = CR_A.copy(); q.putalpha(q.getchannel("A").point(lambda v: int(v * a))); fr.alpha_composite(q, (W // 2 - q.width // 2, 250))
        if lt >= hit - 0.25:
            sc = 1.0 + 0.25 * max(0, 1 - back((lt - hit + 0.25) / 0.45)); al = min(1, (lt - hit + 0.25) / 0.25)
            nm = CR_NAME if sc == 1 else CR_NAME.resize((int(CR_NAME.width * sc), int(CR_NAME.height * sc)), Image.BILINEAR)
            if al < 1: nm = nm.copy(); nm.putalpha(nm.getchannel("A").point(lambda v: int(v * al)))
            fr.alpha_composite(nm, (W // 2 - nm.width // 2, 520 - nm.height // 2))
            sh = (lt - hit - 0.6) / 1.4   # shine sweep across the name
            if 0 < sh < 1:
                band = Image.new("L", CR_NAME.size, 0); bdd = ImageDraw.Draw(band); bx = int(-200 + (CR_NAME.width + 400) * sh)
                bdd.polygon([(bx, 0), (bx + 90, 0), (bx - 60, CR_NAME.height), (bx - 150, CR_NAME.height)], fill=200)
                band = band.filter(ImageFilter.GaussianBlur(18))
                shine = Image.new("RGBA", CR_NAME.size, (255, 250, 225, 0)); shine.putalpha(Image.fromarray(np.minimum(np.array(band), np.array(CR_MASK)).astype(np.uint8)))
                fr.alpha_composite(shine, (W // 2 - CR_NAME.width // 2, 520 - CR_NAME.height // 2))
        b = ease((lt - hit - 0.5) / 0.6)
        if b > 0:
            lw = int(700 * b); d.rectangle((W // 2 - lw, 690, W // 2 + lw, 694), fill=(232, 178, 48, 255))
            q = CR_PROD.copy(); q.putalpha(q.getchannel("A").point(lambda v: int(v * b))); fr.alpha_composite(q, (W // 2 - q.width // 2, 715))
        fade = (lt - (ln - 1.1)) / 1.1
        if fade > 0: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * min(1, fade)))))
        return fr
    return credit_frame

def spoken_intro(t):
    """Vijay, 27 Nov: the presenter in the opener already says "ನಮಸ್ಕಾರ, ವಿಜಯ್ ನ್ಯೂಸ್‌ಗೆ ಸ್ವಾಗತ" – the voice must not
    repeat it in a different pronunciation, so the spoken intro starts after the greeting (when the opener is used)."""
    import re as _re
    if not os.path.exists(os.path.join(HERE, "opener", "opener.mp4")): return t
    return _re.sub(r"^\s*(ನಮಸ್ಕಾರ|ಶುಭೋದಯ|ಶುಭ ಸಂಜೆ)\s*[,.]?\s*ವಿಜಯ್ ನ್ಯೂಸ್‌ಗೆ ಸ್ವಾಗತ\s*[.!]?\s*", "", t) or t

def spoken_headline(h):
    """Vijay, 27 Nov: headlines must sound like a human anchor, not a bot – speak them as a sentence:
    ';' and ':' become natural pauses (commas) and the line ends with a full stop."""
    import re as _re
    h = _re.sub(r"\s*[;:|]\s*", ", ", h.strip()).rstrip(" ,")
    return h if h.endswith((".", "!", "?")) else h + "."

def main(cfg_path, out_mp4):
    cfg = json.load(open(cfg_path))
    # Vijay, 27 Nov: special video stories (real footage with its own sound, e.g. an officer singing at Rajyotsava).
    # specials/live.json = [{..story fields.., "special_clip": "specials/x.mp4", "credit": "...", "until": "YYYY-MM-DD"}]
    # Each active special is added after the news stories of EVERY bulletin until its date: the anchor introduces it
    # (its "body", with the clip silent behind), then the clip plays full screen with its original sound and the credit.
    try:
        import datetime as _dt
        _sp = json.load(open(os.path.join(HERE, "specials", "live.json")))
        for _x in _sp:
            if _x.get("until", "9999") >= _dt.date.today().isoformat() and os.path.exists(os.path.join(HERE, _x["special_clip"])) \
               and not any(s_.get("special_clip") == _x["special_clip"] for s_ in cfg["stories"]):
                _y = dict(_x); _y["special_clip"] = os.path.join(HERE, _x["special_clip"]); _y["broll"] = _y["special_clip"]
                cfg["stories"].append(_y); print("special story added:", _x.get("id"), flush=True)
    except FileNotFoundError: pass
    except Exception as e: print("specials skipped:", e, flush=True)
    # Vijay, 25 Nov 2026: "never ask for subscribe" – drop any subscribe / bell request from the spoken outro
    o = re.sub(r",?\s*(ಚಾನೆಲ್\s*)?ಸಬ್‌?ಸ್ಕ್ರೈಬ್ ಮಾಡಿ", "", cfg.get("outro", ""))          # "…ನೋಡುತ್ತಿರಿ, ಚಾನೆಲ್ ಸಬ್‌ಸ್ಕ್ರೈಬ್ ಮಾಡಿ." -> "…ನೋಡುತ್ತಿರಿ."
    o = re.sub(r"[^.]*(ಸಬ್‌?ಸ್ಕ್ರೈಬ್|ಬೆಲ್ ಐಕಾನ್)[^.]*\.", " ", o)                            # any other subscribe/bell sentence
    cfg["outro"] = re.sub(r"\s+", " ", o).strip()
    # Vijay, 26 Nov 2026: the bulletin runs in a loop – never "ಸಂಜೆ/ನಾಳೆ ಮತ್ತೆ ಸಿಗೋಣ"; always the same closing line
    # (one fixed sentence, so its Puck recording is reused every time).
    cfg["outro"] = os.environ.get("VN_OUTRO", "ಇವು ಈಗಿನ ಪ್ರಮುಖ ಸುದ್ದಿಗಳು. ಇತ್ತೀಚಿನ ಸುದ್ದಿಗಳೊಂದಿಗೆ ಶೀಘ್ರದಲ್ಲೇ ಮತ್ತೆ ಬರುತ್ತೇವೆ. ವಿಜಯ್ ನ್ಯೂಸ್ ನೋಡುತ್ತಿರಿ. ನಮಸ್ಕಾರ.")
    work = os.path.join(HERE, "build"); os.makedirs(work, exist_ok=True)
    A = lambda n: load(os.path.join(HERE, os.environ.get("VN_MUSIC", "audio2"), n))
    intro_m, sting_m, bed_m, outro_m = A("intro.wav"), A("sting.wav"), A("bed.wav"), A("outro.wav")
    texts = [("intro", spoken_intro(cfg["intro"]))] + [(f"h{i}", s.get("headline_spoken") or spoken_headline(s["headline"])) for i, s in enumerate(cfg["stories"])] + [(f"s{i}", s["body"]) for i, s in enumerate(cfg["stories"])] + [("outro", cfg["outro"])]
    voices, engine = {}, None
    adir = os.environ.get("VN_ANCHOR", os.path.join(os.path.dirname(os.path.abspath(cfg_path)), "anchor"))
    clips = {}
    batched = False
    has_clip = any(os.path.exists(os.path.join(adir, k + e)) for k, _ in texts for e in (".mp4", ".mov", ".webm"))
    if not has_clip and os.environ.get("VN_TTS", "auto") in ("auto", "gemini") and os.path.exists(GEMINI_KEYFILE):
        for attempt in range(3):   # Google "Puck" is the channel voice: try hard before falling back
            try:
                print("Voice: Google Gemini 'Puck' (3 requests)…", flush=True)
                engine = synth_batch(texts, work); batched = True; break
            except Exception as e:
                daily = "per day" in str(e).lower() or "PerDay" in str(e)
                print(f"Google voice attempt {attempt+1} failed:", str(e)[:200], flush=True)
                if daily or attempt == 2:
                    break
                import time; time.sleep(300)
        if not batched:
            # Vijay (25 Nov 2026): keep the good Puck reader – never switch the whole bulletin to the
            # Microsoft voice just because a few clips are missing. Stories without a Puck recording are
            # left out; a missing intro/outro is skipped (the presenter opener and the close slide remain).
            import tts as _t
            have = _t.puck_cached(texts, work)
            keep = [i for i, _ in enumerate(cfg["stories"]) if f"h{i}" in have and f"s{i}" in have]
            if len(keep) >= int(os.environ.get("VN_MIN_PUCK_STORIES", "7")):
                dropped = len(cfg["stories"]) - len(keep)
                old_st = cfg["stories"]; cfg["stories"] = [old_st[i] for i in keep]
                sil = np.zeros(int(24000 * 0.6), dtype=np.int16)
                for k in ("intro", "outro"):
                    _t.write_clip(have.get(k, sil), work, k)
                for n, i in enumerate(keep):
                    _t.write_clip(have[f"h{i}"], work, f"h{n}"); _t.write_clip(have[f"s{i}"], work, f"s{n}")
                texts = [("intro", spoken_intro(cfg["intro"]))] + [(f"h{i}", s.get("headline_spoken") or spoken_headline(s["headline"])) for i, s in enumerate(cfg["stories"])] + [(f"s{i}", s["body"]) for i, s in enumerate(cfg["stories"])] + [("outro", cfg["outro"])]
                batched = True; engine = "gemini"
                print(f"-> Puck voice kept: {len(keep)} stories (left out {dropped} without a Puck recording; "
                      f"intro {'ok' if 'intro' in have else 'skipped'}, outro {'ok' if 'outro' in have else 'skipped'})", flush=True)
            else:
                print(f"-> only {len(keep)} stories in Puck – using the Microsoft backup voice for the whole bulletin", flush=True)
    for k, txt in texts:
        p = os.path.join(work, k + ".wav")
        clip = next((os.path.join(adir, k + e) for e in (".mp4", ".mov", ".webm") if os.path.exists(os.path.join(adir, k + e))), None)
        if clip:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-vn", "-ar", str(SR), "-ac", "1", p], check=True)
            clips[k] = clip; engine = "presenter clips"
        elif not batched:
            engine = synth(txt, p, "edge" if os.environ.get("VN_TTS", "auto") == "gemini" else os.environ.get("VN_TTS", "auto"))
        voices[k] = load(p)
    try:   # Vijay, 27 Nov: never let the voice add an unrequested "Vijay News noduttiri" to a story/headline clip
        import tts as _tt
        _fx = _tt.trim_signoff(voices, SR)
        if _fx: print("extra sign-off trimmed from:", ", ".join(_fx), flush=True)
    except Exception as e: print("sign-off check skipped:", e, flush=True)
    HAS_A = len(clips) > 0
    AH = 860  # presenter height on screen
    readers = {}
    def anchor_frame(k, lt):
        if k not in clips: return None
        if k not in readers: readers[k] = Anchor(clips[k], AH)
        return readers[k].at(lt)
    dur = lambda x: len(x) / SR

    # timeline: (kind, start, length, data)
    tl, t = [], 0.0; SPAUD = {}
    tl.append(("open", t, OPEN_LEN, None)); t += OPEN_LEN
    tl.append(("list", t, dur(voices["intro"]) + 1.2, None)); t_voice = {"intro": t + 0.4}; t += tl[-1][2]
    for i, s in enumerate(cfg["stories"]):
        tl.append(("roll", t, dur(voices[f"h{i}"]) + float(os.environ.get("VN_ROLL_HOLD", "2.0")), i)); t_voice[f"h{i}"] = t + 0.18; t += tl[-1][2]
    for i, s in enumerate(cfg["stories"]):
        STING = float(os.environ.get("VN_STING", "3.7")); tl.append(("sting", t, STING, i)); t += STING
        tl.append(("story", t, dur(voices[f"s{i}"]) + 1.0, i)); t_voice[f"s{i}"] = t + 0.35; t += tl[-1][2]
        if s.get("special_clip"):
            _wav = os.path.join(work, f"spclip{i}.wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", s["special_clip"], "-vn", "-ar", str(SR), "-ac", "2", _wav], check=True)
            SPAUD[i] = load(_wav); tl.append(("spclip", t, len(SPAUD[i]) / SR, i)); t += tl[-1][2]
    tl.append(("close", t, dur(voices["outro"]) + 6.5, None)); t_voice["outro"] = t + 0.4; t += tl[-1][2]
    CLOSE = tl[-1]
    sig_p = os.path.join(HERE, os.environ.get("VN_MUSIC", "audio2"), "signature.wav")
    sig_m = load(sig_p) if os.path.exists(sig_p) else None
    if sig_m is not None:   # end card: "A VIJAY MELPAL PRODUCTION" in big gold letters with signature music
        tl.append(("credit", t, len(sig_m) / SR, None)); t += tl[-1][2]
    total = t
    CLOSE_HIT = CLOSE[2] - 7.5 + 0.6 + 8 * 60 / 140  # outro music final impact (music2; +0.6 = CLOSE_SHIFT below)
    HITS = [HIT1, HIT2] + [st + 0.05 for k, st, ln, d in tl if k in ('sting', 'roll')] + [CLOSE[1] + CLOSE_HIT] + \
           [st + 1.0 for k, st, ln, d in tl if k == "credit"]

    mix = np.zeros((int(total * SR) + SR, 2), np.float32)
    def put(sig, at, g):
        i = int(at * SR); j = min(len(mix), i + len(sig)); mix[i:j] += sig[:j - i] * g
    put(intro_m, 0, 0.95)
    for kind, st, ln, d in tl:
        if kind == "sting": put(sting_m, st - 0.6, 0.75)
        if kind == "roll": put(sting_m, st - 0.62, 0.55)
        if kind in ("list", "story", "roll", "sting"):
            n = int(ln * SR); reps = np.tile(bed_m, (n // len(bed_m) + 1, 1))[:n]
            fade = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (0.4 * SR))[:, None]
            put(reps * fade, st, float(os.environ.get("VN_BED", "0.24")) * (0.7 if kind == "roll" else 1.0))
    # Vijay, 27 Nov: "at the end, the audio gets off for a second and comes back" – the close music faded to silence
    # ~0.4 s before the production-card music began. Close music now starts 0.6 s later so its fade overlaps the card music.
    CLOSE_SHIFT = 0.6
    put(outro_m, CLOSE[1] + CLOSE[2] - 7.0 + CLOSE_SHIFT, 0.9)
    for kind, st, ln, d in tl:
        if kind == "credit": put(sig_m, st, 1.0)
        if kind == "spclip":   # the clip's own sound (singing), gently faded in/out
            a_ = SPAUD[d].copy(); n_ = len(a_); f_ = np.minimum(1, np.minimum(np.arange(n_), n_ - np.arange(n_)) / (0.3 * SR))[:, None]
            put(a_ * f_, st, 1.0)
    # Vijay, 27 Nov: "keep announcements slightly high" – the headline voice is a little louder than the stories
    for k, st in t_voice.items(): put(voices[k], st, 0.0 if os.environ.get("VN_NOVOICE") else (float(os.environ.get("VN_HEAD_GAIN", "1.2")) if k.startswith("h") else 1.0))
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    wavfile.write(os.path.join(work, "mix.wav"), SR, (mix * 32767).astype(np.int16))

    # ------------------------------------------------ graphics
    bg = make_bg(); LOGO = brand.mark(400); LOGO_S = brand.mark(84)
    WM_OPEN = brand.wordmark(100); WM_BUG = brand.wordmark(30); WM_CLOSE = brand.wordmark(84); WM_BIG_NK = brand.wordmark(150, kn=False); BIGM = brand.mark(260)
    stories = cfg["stories"]
    tick_txt = "   •   ".join(s["headline"] for s in stories) + "   •   "
    tw = int(text_w(tick_txt, 36)) + 10
    tick = Image.new("RGB", (tw * 2 + 10, 64), (255, 255, 255)); td = ImageDraw.Draw(tick)
    for k in range(2): draw_text(td, k * tw, 46, tick_txt, 36, fill=NAVY)

    chrome = Image.new("RGBA", (W, H), (0, 0, 0, 0)); cd = ImageDraw.Draw(chrome)
    chrome.alpha_composite(LOGO_S, (60, 40))
    chrome.alpha_composite(WM_BUG, (166, 50))
    draw_text(cd, W - 60, 96, cfg["date_kn"], 30, fill=GREY, anchor="r")
    cd.rectangle((0, H - 110, W, H - 46), fill=WHITE); cd.rectangle((0, H - 46, W, H), fill=NAVY)
    cd.rectangle((0, H - 110, 290, H - 46), fill=RED); draw_text(cd, 145, H - 64, "ಮುಖ್ಯಾಂಶಗಳು", 34, anchor="m")
    cd.rectangle((0, H - 112, W, H - 108), fill=GOLD)
    draw_text(cd, W - 60, H - 14, ("ಸಂಪೂರ್ಣ AI ಸುದ್ದಿ ವಾಹಿನಿ • AI ನಿರೂಪಕಿ ಮತ್ತು ಧ್ವನಿ" if HAS_A else "ಸಂಪೂರ್ಣ AI ಸುದ್ದಿ ವಾಹಿನಿ • AI ಧ್ವನಿ • ಸಾಂಕೇತಿಕ ಗ್ರಾಫಿಕ್ಸ್"), 22, fill=GREY, bold=False, anchor="r")

    def base(t, with_chrome=True, ticker=True):
        off = int((t * 18) % 600); fr = bg.crop((off, 0, off + W, H)).convert("RGBA")
        if with_chrome:
            fr.alpha_composite(chrome)
            if ticker:
                o = int((t * 140) % tw); fr.paste(tick.crop((o, 0, o + W - 300, 64)), (300, H - 110))
        return fr

    # per-story AI visuals: "broll" in bulletin.json = path to a short .mp4 or an image (relative to bulletin.json)
    brolls = {}; OFFN = {}
    FULLB = os.environ.get("VN_BROLL_FULL", "1") == "1"   # Vijay, 26 Nov: show the story video full screen
    if not HAS_A:
        cdir = os.path.dirname(os.path.abspath(cfg_path))
        import pixabay_vis as _px
        _used = set(); BSRC = {}
        for i, s in enumerate(stories):
            # Vijay, 27 Nov: "use actual images and video from the official government x.com channels … police departments
            # … mention the source". story["official_media"] = [{"url", "type": "image"|"video", "credit"}] (written by the
            # bulletin task from official government/police posts only) – shown FIRST, with "ಚಿತ್ರ ಕೃಪೆ: …" on screen.
            if s.get("shots") and not s.get("broll") and FULLB:
                import hashlib as _h; sp_, st_, kd_ = [], [], []
                body_ = s.get("body", ""); n_ = max(1, len(body_))
                os.makedirs(os.path.join(cdir, "broll"), exist_ok=True)
                for sh in s["shots"][:4]:
                    p_ = None; kind_ = "pixabay"
                    img = (sh or {}).get("image")
                    if img:
                        if img.startswith("https://"):
                            ext = ".mp4" if ".mp4" in img.split("?")[0] else ".jpg"
                            dest = os.path.join(cdir, "broll", "shot_" + _h.md5(img.split("?")[0].encode()).hexdigest()[:12] + ext)
                            if not os.path.exists(dest):
                                r = subprocess.run(["curl", "-sSfL", "-m", "90", "-A", "Mozilla/5.0", "-o", dest + ".part", img])
                                if r.returncode == 0 and os.path.exists(dest + ".part") and os.path.getsize(dest + ".part") > 5000: os.replace(dest + ".part", dest)
                            if os.path.exists(dest): p_ = dest
                        else:
                            q_ = img if os.path.isabs(img) else os.path.join(cdir, img)
                            if os.path.exists(q_): p_ = q_
                        kind_ = "official" if sh.get("credit") else "ai"
                    elif sh.get("query"):
                        # geography: a line that names a foreign place may show that place even inside an Indian story
                        s["place_query_active"] = any(f_ in sh["query"].lower() for f_ in _px.FOREIGN_TAGS)
                        try: p_, _k = _px.fetch(s, _used, os.path.join(cdir, "broll"), want_video=True, photos=True, qlist=[sh["query"]], need=sh.get("need"))
                        except Exception as e: print("shot skipped:", e, flush=True)
                    if p_:
                        pos = body_.find((sh.get("line") or "").strip()[:25]) if sh.get("line") else -1
                        sp_.append(p_); st_.append(pos / n_ if pos >= 0 else None); kd_.append(kind_)
                        if kind_ == "official" and not s.get("credit"): s["credit"] = "ಚಿತ್ರ ಕೃಪೆ: " + sh["credit"]
                s.pop("place_query_active", None)
                if sp_:
                    for j in range(len(st_)):   # shots without a found line: spread evenly between neighbours
                        if st_[j] is None: st_[j] = j / len(st_)
                    s["broll"] = sp_[0]; s["_shots"] = (sp_, st_, kd_); BSRC[i] = "pixabay" if kd_[0] == "pixabay" else "ai"
                    if sp_[0].lower().endswith(".mp4"):
                        _st = _px.still_from_video(sp_[0])
                        if _st: s["broll_still"] = _st
                    print("shots for story", i + 1, ":", ", ".join(f"{os.path.basename(a)}@{b:.2f}({c})" for a, b, c in zip(sp_, st_, kd_)), flush=True)
            if s.get("official_media") and not s.get("broll"):
                import hashlib as _h; offs = []
                os.makedirs(os.path.join(cdir, "broll"), exist_ok=True)
                for m_ in s["official_media"][:3]:
                    u = (m_ or {}).get("url")
                    if not u or not u.startswith("https://"): continue
                    ext = ".mp4" if m_.get("type") == "video" or ".mp4" in u.split("?")[0] else ".jpg"
                    dest = os.path.join(cdir, "broll", "off_" + _h.md5(u.encode()).hexdigest()[:12] + ext)
                    if not os.path.exists(dest):
                        r = subprocess.run(["curl", "-sSfL", "-m", "90", "-A", "Mozilla/5.0", "-o", dest + ".part", u])
                        if r.returncode == 0 and os.path.exists(dest + ".part") and os.path.getsize(dest + ".part") > 5000: os.replace(dest + ".part", dest)
                    if os.path.exists(dest): offs.append(dest)
                if offs:
                    s["broll"] = offs[0]; s["_official"] = offs; BSRC[i] = "official"
                    s["credit"] = s.get("credit") or ("ಚಿತ್ರ ಕೃಪೆ: " + (s["official_media"][0].get("credit") or "ಅಧಿಕೃತ ಖಾತೆ (ಎಕ್ಸ್)"))
                    print("official media for story", i + 1, ":", ", ".join(os.path.basename(x) for x in offs), flush=True)
            # Vijay, 26 Nov: a short video clip per story (looped while it is read) – free Pixabay clip first
            if not s.get("broll") and os.environ.get("VN_PIXABAY", "1") == "1":
                try:
                    pth, kind = _px.fetch(s, _used, os.path.join(cdir, "broll"), want_video=True) if not s.get("broll_url") else _px.fetch(s, _used, os.path.join(cdir, "broll"), want_video=True)
                    if pth and (kind == "video" or not s.get("broll_url")):
                        s["broll"] = pth; BSRC[i] = "pixabay"
                        if kind == "video":
                            st_ = _px.still_from_video(pth)
                            if st_: s["broll_still"] = st_
                except Exception as e: print("pixabay skipped for story", i + 1, ":", e, flush=True)
            if s.get("broll_url") and not s.get("broll"):   # picture made in Canva by the scheduled task: fetch it on this Mac
                os.makedirs(os.path.join(cdir, "broll"), exist_ok=True)
                ext = ".mp4" if ".mp4" in s["broll_url"].split("?")[0] else ".jpg"
                import hashlib; dest = os.path.join(cdir, "broll", "v_" + hashlib.md5(s["broll_url"].split("?")[0].encode()).hexdigest()[:12] + ext)  # unique per picture
                if not os.path.exists(dest):
                    r = subprocess.run(["curl", "-sSfL", "-m", "90", "-o", dest + ".part", s["broll_url"]])
                    if r.returncode == 0 and os.path.getsize(dest + ".part") > 5000: os.replace(dest + ".part", dest)
                    else: print("visual download failed for story", i + 1, flush=True)
                if os.path.exists(dest): s["broll"] = dest
            bp = s.get("broll")
            if bp and not os.path.isabs(bp): bp = os.path.join(cdir, bp)
            if bp and os.path.exists(bp):
                try:
                    ln = next(l for k, st_, l, dd in tl if k == "story" and dd == i)
                    more = []
                    if FULLB and BSRC.get(i) == "pixabay" and bp.lower().endswith(".mp4") and os.environ.get("VN_MULTICLIP", "1") == "1":
                        try: more = [c for c in _px.extra_clips(s, _used, os.path.join(cdir, "broll"), bp)[1:] if c and c.lower().endswith(".mp4")]
                        except Exception as e: print("extra clips skipped for story", i + 1, ":", e, flush=True)
                    if s.get("_shots") and FULLB:
                        sp_, st_, kd_ = s["_shots"]; more = sp_[1:]
                        brolls[i] = MultiBRoll(sp_, ln, (W, H), st_, kd_) if len(sp_) > 1 else BRoll(sp_[0], ln, (W, H))
                    elif s.get("_official") and FULLB:   # official pictures/video first, then one real stock clip for long stories
                        offs = s["_official"][:3]; extra = []
                        if ln >= 14 and len(offs) < 3:
                            try:
                                p2, k2 = _px.fetch(s, _used, os.path.join(cdir, "broll"), photos=False)
                                if p2: extra = [p2]
                            except Exception as e: print("stock clip skipped:", e, flush=True)
                        OFFN[i] = len(offs); more = offs[1:] + extra; bp = offs[0]
                        brolls[i] = MultiBRoll(offs + extra, ln, (W, H)) if len(offs + extra) > 1 else BRoll(bp, ln, (W, H))
                    elif more and ln >= 12:
                        brolls[i] = MultiBRoll([bp] + more[:2], ln, (W, H))
                    else:
                        brolls[i] = BRoll(bp, ln, (W, H) if FULLB else None)
                    print("visual for story", i + 1, ":", ", ".join(os.path.basename(x) for x in ([bp] + more[:3] if s.get("_shots") else [bp] + (more[:2] if more and ln >= 12 else []))), flush=True)
                except Exception as e: print("visual skipped for story", i + 1, ":", e, flush=True)
    SPR = {}; _SPL = {}; RB = {}
    ROLL_DIM = Image.new("RGBA", (W, H), (6, 12, 30, 105))   # darken the headline background video a little
    def sp_label(i):   # "ವಿಡಿಯೋ ಕೃಪೆ: …" label for real footage (never the "AI ಸಾಂಕೇತಿಕ ದೃಶ್ಯ" label)
        if i not in _SPL:
            txt = stories[i].get("credit", "ವಿಡಿಯೋ ಕೃಪೆ: ಸಾಮಾಜಿಕ ಜಾಲತಾಣ"); w_ = int(text_w(txt, 24)) + 40
            im = Image.new("RGBA", (w_, 44), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
            dd.rounded_rectangle((0, 0, w_ - 1, 43), 10, fill=(0, 0, 0, 170)); draw_text(dd, w_ // 2, 32, txt, 24, anchor="m", bold=False)
            _SPL[i] = im
        return _SPL[i]
    BLABEL = Image.new("RGBA", (250, 40), (0, 0, 0, 0)); bl = ImageDraw.Draw(BLABEL)
    bl.rounded_rectangle((0, 0, 249, 39), 10, fill=(0, 0, 0, 150)); draw_text(bl, 125, 29, "AI ಸಾಂಕೇತಿಕ ದೃಶ್ಯ", 22, anchor="m", bold=False)
    PLABEL = Image.new("RGBA", (300, 40), (0, 0, 0, 0)); pl_ = ImageDraw.Draw(PLABEL)
    pl_.rounded_rectangle((0, 0, 299, 39), 10, fill=(0, 0, 0, 150)); draw_text(pl_, 150, 29, "ಸಾಂಕೇತಿಕ ದೃಶ್ಯ • Pixabay", 22, anchor="m", bold=False)
    if not HAS_A: pass
    else: BSRC = {}
    if brolls:
        cd.rectangle((W - 1000, H - 40, W, H), fill=NAVY)
        draw_text(cd, W - 60, H - 14, "ಸಂಪೂರ್ಣ AI ಸುದ್ದಿ ವಾಹಿನಿ • AI ಧ್ವನಿ • ಸಾಂಕೇತಿಕ ದೃಶ್ಯಗಳು", 22, fill=GREY, bold=False, anchor="r")

    # full-screen video stories: darken left side / top / bottom so the text stays readable
    GRAD = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if brolls and FULLB:
        xs = np.linspace(0, 1, W); ys = np.linspace(0, 1, H)
        ax = np.clip(1.15 - xs / 0.62, 0, 1) ** 1.4 * 205
        ay = np.maximum(np.clip(1 - ys / 0.20, 0, 1) * 150, np.clip((ys - 0.72) / 0.28, 0, 1) * 170)
        a = np.clip(np.maximum(ax[None, :], ay[:, None]), 0, 225).astype(np.uint8)
        GRAD = Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [Image.fromarray(a, "L")])
    FXS = {}
    # story static panels
    panels = []
    FX = 90 if HAS_A else 800
    for i, s in enumerate(stories):
        p = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
        if HAS_A and f"s{i}" in clips:
            x = 90; tagw = text_w(s["tag"], 32)
            rrect(d, (x, 200, x + tagw + 44, 260), 12, RED); draw_text(d, x + 22, 244, s["tag"], 32)
            draw_text(d, x + tagw + 70, 244, "• " + s["place"], 32, fill=GOLD)
            hl = wrap(s["headline"], 60, 1020)
            for j, ln in enumerate(hl[:2]): draw_text(d, x, 340 + j * 82, ln, 60)
            ys = 340 + (len(hl[:2]) - 1) * 82 + 150
            p.alpha_composite(icon(s["icon"], 96), (x, ys - 96))
            sw = font("beb", 130).getlength(s["stat"])
            d.text((x + 120, ys), s["stat"], font=font("beb", 130), fill=GOLD, anchor="ls")
            for j, ln in enumerate(wrap(s["stat_label"], 34, 1000 - sw - 150)[:2]): draw_text(d, x + 150 + sw, ys - 50 + j * 44, ln, 34)
            draw_text(d, x, 948, s["source"] + f"   |   ಸುದ್ದಿ {i+1} / {len(stories)}", 24, fill=GREY, bold=False)
            panels.append((p, ys - 4)); continue
        if i in brolls and FULLB:
            x = 90; tagw = text_w(s["tag"], 32); FXS[i] = (90, 1060)
            rrect(d, (x, 222, x + tagw + 44, 282), 12, RED); draw_text(d, x + 22, 266, s["tag"], 32)
            draw_text(d, x + tagw + 70, 266, "• " + s["place"], 32, fill=GOLD)
            hl = wrap(s["headline"], 64, 1150)
            for j, ln in enumerate(hl[:2]): draw_text(d, x, 372 + j * 88, ln, 64)
            # stat in a small box, bottom right
            sf = 96 if len(s["stat"]) <= 6 else 72; sw_ = font("beb", sf).getlength(s["stat"])
            lab = wrap(s["stat_label"], 28, 380)[:2]; bw_ = int(max(sw_, max([text_w(l, 28) for l in lab] or [0])) + 70)
            bx0 = W - 90 - bw_; rrect(d, (bx0, 680, W - 90, 900), 22, (8, 14, 34, 190)); d.rectangle((bx0, 680, W - 90, 688), fill=GOLD)
            d.text((bx0 + bw_ / 2, 800), s["stat"], font=font("beb", sf), fill=GOLD, anchor="ms")
            for j, l in enumerate(lab): draw_text(d, bx0 + bw_ / 2, 845 + j * 36, l, 28, anchor="m")
            draw_text(d, x, 940, s["source"] + f"   |   ಸುದ್ದಿ {i+1} / {len(stories)}", 24, fill=(225, 225, 225), bold=False)
            panels.append((p, 372 + len(hl[:2]) * 88 - 40)); continue
        rrect(d, (90, 200, 720, 900), 36, (255, 255, 255, 18)); rrect(d, (90, 200, 720, 212), 6, RED)
        if i in brolls:
            sz = 150 if len(s["stat"]) <= 5 else 110
            d.text((405, 720), s["stat"], font=font("beb", sz), fill=GOLD, anchor="ms")
            for j, ln in enumerate(wrap(s["stat_label"], 34, 580)[:2]): draw_text(d, 405, 776 + j * 44, ln, 34, anchor="m")
        else:
          p.alpha_composite(icon(s["icon"], 150), (330, 250))
          sz = 260 if len(s["stat"]) <= 3 else (200 if len(s["stat"]) <= 5 else 150)
          d.text((405, 590), s["stat"], font=font("beb", sz), fill=GOLD, anchor="ms")
          for j, ln in enumerate(wrap(s["stat_label"], 40, 560)): draw_text(d, 405, 660 + j * 54, ln, 40, anchor="m")
        draw_text(d, 405, 860, f"ಸುದ್ದಿ {i+1} / {len(stories)}", 28, fill=GREY, anchor="m", bold=False)
        x = 800; tagw = text_w(s["tag"], 32)
        rrect(d, (x, 222, x + tagw + 44, 282), 12, RED); draw_text(d, x + 22, 266, s["tag"], 32)
        draw_text(d, x + tagw + 70, 266, "• " + s["place"], 32, fill=GOLD)
        hl = wrap(s["headline"], 70, 1040)
        for j, ln in enumerate(hl[:2]): draw_text(d, x, 380 + j * 96, ln, 70)
        draw_text(d, x, 912, s["source"], 26, fill=GREY, bold=False)
        panels.append((p, 380 + len(hl[:2]) * 96))

    FMAXW = W - FX - 140   # text width available for a fact line
    def fact_plan(s, y0, FX=FX, FMAXW=FMAXW):
        # Vijay, 26 Nov: facts must be shown complete – wrap to 2 lines and shrink the font until all fit (never cut).
        for size in (40, 36, 33, 30, 28):
            lh = int(size * 1.3); rows = [wrap(f, size, FMAXW)[:3] for f in s["facts"]]
            hts = [len(r) * lh + 30 for r in rows]
            if y0 + 20 + sum(hts) + 12 * (len(hts) - 1) <= (915 if FX < 400 else 925) and all(len(wrap(f, size, FMAXW)) <= 2 for f in s["facts"]):
                return size, lh, rows, hts
        return size, lh, rows, hts
    def fact_layer(s, y0, n_show, t_in, fx=None):
        p = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
        FX_, MW_ = fx or (FX, FMAXW); onv = fx is not None
        size, lh, rows, hts = fact_plan(s, y0, FX_, MW_); y = y0 + 20
        for j in range(min(n_show, len(rows))):
            a = ease(t_in[j]); xo = int(FX_ + (1 - a) * 60); h = hts[j]
            bw = max(text_w(ln, size) for ln in rows[j]) + 90
            rrect(d, (xo, y, xo + bw, y + h), 18, (6, 12, 30, int(165 * a)) if onv else (255, 255, 255, int(28 * a)))
            d.rectangle((xo, y, xo + 8, y + h), fill=GOLD + (int(255 * a),))
            for k, ln in enumerate(rows[j]):
                draw_text(d, xo + 40, y + 15 + int(size * 1.0) + k * lh, ln, size, fill=(255, 255, 255, int(255 * a)))
            y += h + 12
        return p

    strap = Image.new("RGBA", (760, 84), (0, 0, 0, 0)); sd_ = ImageDraw.Draw(strap)
    an = cfg.get("anchor_name", "AI ನಿರೂಪಕಿ"); aw = text_w(an, 34) + 50
    sd_.rectangle((0, 0, aw, 84), fill=RED); draw_text(sd_, 25, 56, an, 34)
    sd_.rectangle((aw, 0, 760, 84), fill=(255, 255, 255, 235)); draw_text(sd_, aw + 25, 56, cfg["channel"], 34, fill=NAVY)
    ACX = 1490  # presenter centre x

    def add_anchor(fr, k, t, show_strap=False, cx=ACX):
        im = anchor_frame(k, t - t_voice[k]) if k in t_voice else None
        if im is None: return
        paste_clip(fr, im, cx, H - 112)
        if show_strap:
            a = ease((t - t_voice[k]) / 0.4)
            if a > 0: fr.alpha_composite(strap, (int(cx - 380 + (1 - a) * 100), H - 230))

    credit_frame = build_credit()

    # ------------------------------------------------ frame generator
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", os.path.join(work, "mix.wav"),
                           "-c:v", "libx264", "-preset", "veryfast", "-g", "50", "-keyint_min", "50", "-sc_threshold", "0", "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.2:LRA=9", "-ar", "44100", "-ac", "2", "-shortest", "-movflags", "+faststart", out_mp4], stdin=subprocess.PIPE)
    nframes = int(total * FPS)
    seg_i = 0
    for fi in range(nframes):
        t = fi / FPS
        while seg_i < len(tl) - 1 and t >= tl[seg_i][1] + tl[seg_i][2]: seg_i += 1
        kind, st, ln, data = tl[seg_i]; lt = t - st

        if kind == "open":
            fr = base(t, with_chrome=False); d = ImageDraw.Draw(fr)
            # streaks
            for k in range(14):
                y = (k * 83 + 40) % H; x = (lt * (900 + k * 70) + k * 300) % (W + 800) - 400
                d.rectangle((x, y, x + 260 + k * 10, y + 3), fill=(255, 255, 255, 60))
            if lt < HIT1:
                words = ["ಸತ್ಯ", "ನಿಖರ", "ವೇಗ"]; wi = min(2, int(lt / (HIT1 / 3))); ll = lt - wi * HIT1 / 3
                sc = 1.25 - 0.25 * ease(ll / 0.15)
                tw_ = Image.new("RGBA", (W, H), (0, 0, 0, 0)); tdw = ImageDraw.Draw(tw_)
                draw_text(tdw, W // 2, 620, words[wi], int(230 * sc), fill=(WHITE if wi != 1 else GOLD), anchor="m")
                fr.alpha_composite(tw_)
                fr = punch(fr, max(0, 1 - ll / 0.25) * 0.6, fi)
            if lt >= HIT1:
                a = ease((lt - HIT1) / 0.35); sc = 1.35 - 0.35 * a
                L = LOGO.resize((int(420 * sc), int(420 * sc)), Image.LANCZOS)
                L.putalpha(L.getchannel("A").point(lambda v: int(v * a)))
                fr.alpha_composite(L, (W // 2 - L.width // 2, 300 - L.height // 2 + 40))
                if lt < HIT1 + .25: fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(180 * (1 - (lt - HIT1) / .25)))))
                if HIT2 <= lt < HIT2 + .2: fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(140 * (1 - (lt - HIT2) / .2)))))
                txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); td2 = ImageDraw.Draw(txt)
                b = ease((lt - 2.0) / 0.6)
                rv = ease((lt - HIT1 - 0.35) / 0.55)
                if rv > 0:
                    wm = WM_OPEN.copy(); cut = int(wm.width * rv)
                    m = Image.new("L", wm.size, 0); ImageDraw.Draw(m).rectangle((0, 0, cut, wm.height), fill=255)
                    wm.putalpha(Image.composite(wm.getchannel("A"), m, m))
                    txt.alpha_composite(wm, (W // 2 - wm.width // 2, 590 + int((1 - rv) * 30)))
                    if rv < 1: td2.rectangle((W // 2 - wm.width // 2 + cut, 590, W // 2 - wm.width // 2 + cut + 10, 590 + wm.height), fill=GOLD)
                c = ease((lt - 4.5) / 0.6)
                draw_text(td2, W // 2, 860, "ನಿಖರ ಸುದ್ದಿ • ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ", 40, fill=(255, 255, 255, int(220 * c)), anchor="m")
                fr.alpha_composite(txt)
            if lt > OPEN_LEN - .4: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (lt - OPEN_LEN + .4) / 0.4))))

        elif kind == "list":
            fr = base(t); d = ImageDraw.Draw(fr)
            a = ease(lt / 0.5)
            draw_text(d, 120 - (1 - a) * 80, 270, "ಈ ಹೊತ್ತಿನ ಪ್ರಮುಖ ಸುದ್ದಿಗಳು", 64, fill=GOLD)
            d.rectangle((120, 300, 120 + 300 * a, 306), fill=RED)
            NL_ = min(10, len(stories)); per = max(0.5, (ln - 1.5) / NL_)
            for j, s in enumerate(stories[:NL_]):
                b = ease((lt - 0.6 - j * per * 0.6) / 0.4)
                if b <= 0: continue
                big_ = len(stories) <= 5; tight_ = NL_ > 8; sp_ = 108 if big_ else (58 if tight_ else 68); bx_ = 76 if big_ else (48 if tight_ else 54)
                y = (400 if big_ else 380) + j * sp_; x = 120 + (1 - b) * 120
                if not big_ and (j == 0 or stories[j - 1].get("section") != s.get("section")):
                    pass
                rrect(d, (x, y - bx_ + 14, x + bx_, y + 14), 12, RED); d.text((x + bx_ / 2, y - bx_ / 2 + 14), str(j + 1), font=font("lat", 42 if big_ else (27 if tight_ else 30)), fill=WHITE, anchor="mm")
                fs_ = (44 if HAS_A else 50) if big_ else (34 if tight_ else 38)
                hl_ = s["headline"]
                while text_w(hl_, fs_) > (1080 if HAS_A else 1600) and " " in hl_: hl_ = hl_.rsplit(" ", 1)[0] + "…"
                draw_text(d, x + bx_ + 30, y, hl_, fs_, fill=(255, 255, 255))
                if not big_:
                    sec_ = {"ರಾಜ್ಯ": GOLD, "ರಾಷ್ಟ್ರೀಯ": (120, 190, 255), "ಅಂತರರಾಷ್ಟ್ರೀಯ": (140, 230, 170), "ಟೆಕ್": (215, 150, 255)}.get(s.get("tag"), GREY)
                    d.rectangle((x - 18, y - bx_ + 14, x - 12, y + 14), fill=sec_)
            add_anchor(fr, "intro", t, show_strap=True)

        elif kind == "roll":
            s = stories[data]
            # Vijay, 27 Nov: "when showing bulletin headlines also show their relevant videos in the background"
            if data in brolls and FULLB and os.environ.get("VN_ROLL_VIDEO", "1") == "1":
                if data not in RB:
                    b_ = brolls[data]; RB[data] = BRoll(b_.paths[0] if hasattr(b_, "paths") else b_.path, ln, (W, H))
                    for k_ in [k_ for k_ in RB if k_ != data and RB[k_]]: RB[k_].close(); RB[k_] = None
                fr = base(t, with_chrome=False); v_ = RB[data].at(lt)
                if v_ is not None:
                    v_ = v_.convert("RGBA"); fr = v_ if lt >= 0.3 else Image.blend(fr, v_, min(1, lt / 0.3))
                fr.alpha_composite(ROLL_DIM); fr.alpha_composite(chrome)
                o_ = int((t * 140) % tw); fr.paste(tick.crop((o_, 0, o_ + W - 300, 64)), (300, H - 110))
            else: fr = base(t)
            p = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
            a = back(lt / 0.3)
            draw_text(d, 120, 250, "ಮುಖ್ಯಾಂಶಗಳು", 52, fill=GOLD)
            x0 = int(-W + (W + 0) * min(1, a))
            d.rectangle((x0, 430, x0 + W, 690), fill=RED)
            d.rectangle((x0, 690, x0 + W, 700), fill=GOLD)
            d.rectangle((x0, 430, x0 + 250, 690), fill=(150, 6, 18))
            d.text((x0 + 125, 615), f"{data+1:02d}", font=font("beb", 190), fill=WHITE, anchor="ms")
            hl = wrap(s["headline"], 66, 1500)
            for j, l in enumerate(hl[:2]): draw_text(d, x0 + 300, 545 + j * 84 - (40 if len(hl) > 1 else 0), l, 66)
            draw_text(d, x0 + 300, 760, s["tag"] + " • " + s["place"], 34, fill=GREY)
            fr.alpha_composite(p)

        elif kind == "sting":
            fr = base(t); s = stories[data]
            p = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
            if lt < 0.45: x = -W - 600 + (W + 600) * ease(lt / 0.45)
            elif lt < ln - 0.45: x = 0
            else: x = (W + 600) * ease((lt - (ln - 0.45)) / 0.45)
            d.polygon([(x - 300, 0), (x + W + 300, 0), (x + W, H), (x - 600, H)], fill=RED)
            d.polygon([(x + W + 300, 0), (x + W + 380, 0), (x + W + 80, H), (x + W, H)], fill=GOLD)
            if 0.3 < lt < ln - 0.3:
                sec = s.get("section")
                if sec and (data == 0 or stories[data - 1].get("section") != sec):
                    draw_text(d, x + W // 2, 190, sec, 84, fill=(255, 225, 120), anchor="m")
                d.text((x + W // 2, 470), f"{data+1:02d}", font=font("beb", 260), fill=(255, 255, 255, 70), anchor="ms")
                for j, l in enumerate(wrap(s["headline"], 76, 1500)[:2]):
                    draw_text(d, x + W // 2, 620 + j * 100, l, 76, anchor="m")
                draw_text(d, x + W // 2, 790, s["tag"] + " • " + s["place"], 36, fill=(255, 235, 180), anchor="m")
            fr.alpha_composite(p)

        elif kind == "story":
            s = stories[data]; p, y0 = panels[data]
            if data in brolls and FULLB:
                fr = base(t, with_chrome=False); bim = brolls[data].at(lt)
                if bim is not None:
                    v = bim.convert("RGBA"); al = min(1, lt / 0.5)
                    fr = v if al >= 1 else Image.blend(fr, v, al)
                fr.alpha_composite(GRAD); fr.alpha_composite(chrome)
                o = int((t * 140) % tw); fr.paste(tick.crop((o, 0, o + W - 300, 64)), (300, H - 110))
            else: fr = base(t)
            a = back(lt / 0.45)
            if lt < 0.45:
                q = p.copy(); al = min(1, lt / 0.2); q.putalpha(q.getchannel("A").point(lambda v: int(v * al)))
                fr.alpha_composite(q, (int((1 - a) * 260), 0))
            else: fr.alpha_composite(p)
            nf = len(s["facts"]); gap = max(1.2, (ln - 2.0) / nf)
            t_in = [(lt - (0.9 + j * gap)) / 0.5 for j in range(nf)]
            shown = sum(1 for v in t_in if v > 0)
            if data in brolls and FULLB:
                _b = brolls[data]; _seg = _b.index(max(0, lt)) if hasattr(_b, "index") else 0
                _kd = _b.kinds[_seg] if getattr(_b, "kinds", None) else None
                if _kd:   # shot plan: label each clip by its own source
                    if _kd == "official": fr.alpha_composite(sp_label(data), (W - 90 - sp_label(data).width, 150))
                    else: fr.alpha_composite(PLABEL if _kd == "pixabay" else BLABEL, (W - 90 - (300 if _kd == "pixabay" else 250), 150))
                elif stories[data].get("special_clip") or (stories[data].get("_official") and _seg < OFFN.get(data, 1)):
                    fr.alpha_composite(sp_label(data), (W - 90 - sp_label(data).width, 150))
                else: fr.alpha_composite(PLABEL if BSRC.get(data) == "pixabay" else BLABEL, (W - 90 - (300 if BSRC.get(data) == "pixabay" else 250), 150))
            elif data in brolls:
                bim = brolls[data].at(lt)
                if bim is not None:
                    al = min(1, lt / 0.4); m = brolls[data].mask if al >= 1 else brolls[data].mask.point(lambda v: int(v * al))
                    fr.paste(bim, (90 + int((1 - a) * 260), 222), m)
                    if al >= 1: fr.alpha_composite(PLABEL if BSRC.get(data) == "pixabay" else BLABEL, (110, 222 + BRoll.BH - 54))
            if shown: fr.alpha_composite(fact_layer(s, y0, shown, t_in, FXS.get(data)))
            if HAS_A and f"s{data}" in clips: add_anchor(fr, f"s{data}", t)
            else:
                d = ImageDraw.Draw(fr)
                if data in FXS: d.rectangle((0, H - 116, int(W * min(1, lt / ln)), H - 112), fill=GOLD)
                else: d.rectangle((90, 912, 90 + 630 * min(1, lt / ln), 918), fill=GOLD)

        elif kind == "spclip":   # special: the real clip full screen with its own sound, headline strip + credit
            if data not in SPR: SPR[data] = BRoll(stories[data]["special_clip"], ln, (W, H))
            fr = SPR[data].at(lt).convert("RGBA")
            fr.alpha_composite(LOGO_S, (60, 40)); fr.alpha_composite(WM_BUG, (166, 50))
            fr.alpha_composite(sp_label(data), (W - 60 - sp_label(data).width, 52))
            a = ease(min(1, lt / 0.5)) * (1 if lt < ln - 0.6 else max(0, (ln - lt) / 0.6))
            if a > 0:
                lt3 = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lt3); s_ = stories[data]
                tagw = text_w(s_.get("tag", "ವಿಶೇಷ"), 34) + 44; y0 = H - 210
                ld.rectangle((0, y0, W, H - 70), fill=NAVY + (215,)); ld.rectangle((0, y0, W, y0 + 6), fill=GOLD)
                rrect(ld, (60, y0 + 26, 60 + tagw, y0 + 86), 12, RED); draw_text(ld, 82, y0 + 70, s_.get("tag", "ವಿಶೇಷ"), 34)
                draw_text(ld, 90 + tagw, y0 + 72, s_["headline"], 46)
                lt3.putalpha(lt3.getchannel("A").point(lambda v: int(v * a))); fr.alpha_composite(lt3)

        elif kind == "credit":
            fr = credit_frame(lt, ln)

        elif lt >= CLOSE[2] - 7.5 + 8 * 60 / 140:  # BIG TEXT closing slide
            h0 = lt - (ln - 7.5 + 8 * 60 / 140)
            fr = Image.new("RGBA", (W, H), (12, 6, 10, 255)); d = ImageDraw.Draw(fr)
            for k in range(7):  # red speed bars
                y = 90 + k * 150; xx = int((h0 * (1600 + k * 300) + k * 500) % (W + 900)) - 900
                d.rectangle((xx, y, xx + 700, y + 14), fill=(RED if k % 2 else (120, 14, 26)))
            sc = 1.35 - 0.35 * back(h0 / 0.35)
            big = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
            big.alpha_composite(BIGM, (W // 2 - BIGM.width // 2, 150))
            big.alpha_composite(WM_BIG_NK, (W // 2 - WM_BIG_NK.width // 2, 470))
            if h0 > 0.35: draw_text(bd, W // 2, 740, cfg["channel"], 96, fill=GOLD, anchor="m")
            if h0 > 0.7:
                bd.rectangle((W // 2 - 520, 790, W // 2 + 520, 796), fill=RED)
            if sc != 1:
                bz = big.resize((int(W * sc), int(H * sc)), Image.BILINEAR); fr.alpha_composite(bz, ((W - bz.width) // 2, (H - bz.height) // 2))
            else: fr.alpha_composite(big)
            fade = (lt - (ln - 1.0)) / 1.0
            if fade > 0: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * min(1, fade)))))

        elif "outro" in clips and lt < dur(voices["outro"]) + 0.6:
            fr = base(t); add_anchor(fr, "outro", t, show_strap=True, cx=W // 2)

        else:  # close
            fr = base(t); d = ImageDraw.Draw(fr)
            a = ease(lt / 0.6)
            L = LOGO.resize((260, 260), Image.LANCZOS); fr.alpha_composite(L, (W // 2 - 130, 200))
            fr2 = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d2 = ImageDraw.Draw(fr2)
            wmc = brand.wordmark(84, kn=False); wmc.putalpha(wmc.getchannel("A").point(lambda v: int(v * a)))
            fr2.alpha_composite(wmc, (W // 2 - wmc.width // 2, 500))
            draw_text(d2, W // 2, 720, "ನೋಡಿದ್ದಕ್ಕೆ ಧನ್ಯವಾದಗಳು", 52, fill=GOLD + (int(255 * a),), anchor="m")
            b = ease((lt - 1.0) / 0.5); bw = text_w("ಪ್ರತಿದಿನ ಬೆಳಿಗ್ಗೆ ಮತ್ತು ಸಂಜೆ 6ಕ್ಕೆ", 44) + 120
            pulse = 1 + 0.03 * math.sin(lt * 5)
            bx0, by0 = W // 2 - bw * pulse / 2, 770
            rrect(d2, (bx0, by0, bx0 + bw * pulse, by0 + 92 * pulse), 46, RED + (int(255 * b),))
            draw_text(d2, W // 2, by0 + 62 * pulse, "ಪ್ರತಿದಿನ ಬೆಳಿಗ್ಗೆ ಮತ್ತು ಸಂಜೆ 6ಕ್ಕೆ", 44, fill=(255, 255, 255, int(255 * b)), anchor="m")
            fr.alpha_composite(fr2)

        k = max([math.exp(-(t - h) * 9) for h in HITS if 0 <= t - h < 0.5] + [0])
        if k > 0.02: fr = punch(fr, k, fi)
        ff.stdin.write(fr.convert("RGB").tobytes())
        if fi % 250 == 0: print(f"frame {fi}/{nframes}", flush=True)
    ff.stdin.close(); ff.wait()
    add_opener(out_mp4, work)
    try:   # vertical YouTube Short of the top stories (uploaded by the scheduled task)
        # Vijay, 26 Nov: each Short = ONE news story (its full spoken report), then the usual end card + production card.
        import shorts, time as _tm
        ts = _tm.strftime("%Y%m%d_%H%M")
        for n, i in enumerate(shorts.pick(cfg["stories"])):
            st = dict(cfg["stories"][i]); vk = f"s{i}" if f"s{i}" in voices else f"h{i}"
            o = shorts.make_short({"stories": [st]}, {"h0": voices[vk]}, HERE, work, header=st.get("section", "ಸುದ್ದಿ"),
                                  out_name=f"short_{ts}_{n + 1}.mp4")
            print("short:", o, flush=True)
    except Exception as e: print("short skipped:", e, flush=True)
    try:   # special one-story Shorts requested by Vijay: specials/<id>.json (made once, marked <id>.done)
        import glob, shorts, tts as _t
        for sp in sorted(glob.glob(os.path.join(HERE, "specials", "*.json"))):
            done = sp[:-5] + ".done"
            if os.path.exists(done) or sp.endswith("live.json"): continue   # live.json = special video stories (not Shorts)
            spec = json.load(open(sp)); st = spec["story"]; sw = os.path.join(work, "special"); os.makedirs(sw, exist_ok=True)
            if st.get("broll_auto"):   # use the picture chosen for the same story in THIS bulletin (Vijay, 27 Nov: ASHA)
                m_ = next((x for x in cfg["stories"] if x.get("headline", "").strip() == st.get("headline", "").strip()), None)
                if m_ and (m_.get("broll_still") or m_.get("broll")): st["broll"] = m_.get("broll_still") or m_["broll"]
            if st.get("broll_url"):
                dest = os.path.join(sw, spec["id"] + ".jpg")
                if subprocess.run(["curl", "-sSfL", "-m", "90", "-o", dest, st["broll_url"]]).returncode == 0: st["broll"] = dest
            try: _t.synth_batch([("h0", spec["script"])], sw, groups=[["h0"]])
            except Exception as e: print("special voice: Google failed, Microsoft used:", str(e)[:80], flush=True); _t.synth(spec["script"], os.path.join(sw, "h0.wav"), "edge")
            out = shorts.make_short({"stories": [st]}, {"h0": load(os.path.join(sw, "h0.wav"))}, HERE, sw,
                                    header=spec.get("header", "ವಿಶೇಷ ಸುದ್ದಿ"), out_name="special_" + spec["id"] + ".mp4")
            open(done, "w").write(out + "\n"); print("special short:", out, flush=True)
    except Exception as e: print("special short skipped:", e, flush=True)
    print("done", out_mp4, f"{total:.1f}s", "voice:", engine)

def add_opener(out_mp4, work):
    """If opener/opener.mp4 exists (AI presenter: "ನಮಸ್ಕಾರ, ವಿಜಯ್ ನ್ಯೂಸ್‌ಗೆ ಸ್ವಾಗತ…"), put it in front of the bulletin.
    The clip is re-encoded to the bulletin's exact format, with an "AI ನಿರೂಪಕ" label, then joined without re-encoding the bulletin."""
    op = next((os.path.join(HERE, "opener", n) for n in ("opener.mp4", "opener.mov") if os.path.exists(os.path.join(HERE, "opener", n))), None)
    if not op: return
    try:
        lab = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lab)
        tw = text_w("AI ನಿರೂಪಕ", 30) + 40
        d.rounded_rectangle((60, 50, 60 + tw, 100), 10, fill=(0, 0, 0, 150)); draw_text(d, 80, 88, "AI ನಿರೂಪಕ", 30, bold=False)
        lab.alpha_composite(brand.wordmark(46, kn=False), (W - brand.wordmark(46, kn=False).width - 60, 50))
        lp = os.path.join(work, "opener_label.png"); lab.save(lp)
        oe = os.path.join(work, "opener_enc.mp4")
        has_a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", op],
                               capture_output=True, text=True).stdout.strip() != ""
        ain = ["-i", op] if has_a else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", op, "-i", lp, *ain, "-filter_complex",
                        f"[0:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[v];[v][1:v]overlay=0:0,format=yuv420p[vo]",
                        "-map", "[vo]", "-map", "2:a", "-t", "12",
                        "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-g", "50", "-keyint_min", "50", "-sc_threshold", "0",
                        "-b:v", "4500k", "-maxrate", "4500k", "-bufsize", "9000k", "-r", str(FPS),
                        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-af", "loudnorm=I=-14:TP=-1.2:LRA=9",
                        "-shortest", "-movflags", "+faststart", oe], check=True)
        lst = os.path.join(work, "opener_concat.txt"); joined = out_mp4 + ".join.mp4"
        # Vijay, 26 Nov: after the presenter's greeting, skip the first 6 s of the 10 s title animation (no long gap)
        cut = float(os.environ.get("VN_OPEN_CUT", "6.0")); body = out_mp4
        if cut > 0:
            body = out_mp4 + ".cut.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(cut), "-i", out_mp4, "-c", "copy", "-movflags", "+faststart", body], check=True)
        open(lst, "w").write(f"file '{os.path.abspath(oe)}'\nfile '{os.path.abspath(body)}'\n")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", joined], check=True)
        os.replace(joined, out_mp4)
        if body != out_mp4 and os.path.exists(body): os.remove(body)
        print("opener added:", os.path.basename(op), flush=True)
    except Exception as e:
        print("opener skipped:", e, flush=True)

if __name__ == "__main__":
    try:   # Vijay (25 Nov 2026): upload the previous day's editions as normal videos, then free the Mac
        if os.path.exists(os.path.expanduser("~/.vijaynews_yt_token.json")):
            subprocess.Popen([sys.executable, os.path.join(HERE, "yt_upload.py"), "daily"], cwd=HERE,
                             stdout=subprocess.DEVNULL, stderr=open(os.path.join(HERE, "upload.err"), "a"),
                             start_new_session=True)
    except Exception as e:
        print("daily upload not started:", e, flush=True)
    main(sys.argv[1] if len(sys.argv) > 1 else "bulletin.json", sys.argv[2] if len(sys.argv) > 2 else "vijay_news_bulletin.mp4")
