"""Vijay News – vertical YouTube Short (1080x1920, ~30 s) from a rendered bulletin.
Called at the end of make_bulletin.main(); re-uses the bulletin's voice clips and AI pictures.
Picks the top state story + the sports, cinema and first tech story. Output: shorts/short_<timestamp>.mp4"""
import os, subprocess, time, math
import numpy as np
from PIL import Image, ImageDraw
from scipy.io import wavfile

SW, SH = 1080, 1920

# Vijay, 27 Nov: "such news like asha karyakartheyara strike, alok kumar IPS singing to be made as youtube shorts too"
# -> every bulletin also makes a Short of its people-centred story (workers'/women's/farmers' struggles, inspiring
# human moments), and stories that already have their own special Short (specials/<id>.json) are not repeated.
PEOPLE_WORDS = ("ಆಶಾ", "ಕಾರ್ಯಕರ್ತೆ", "ಅಂಗನವಾಡಿ", "ಮಹಿಳೆ", "ಮಹಿಳಾ", "ಹೋರಾಟ", "ಧರಣಿ", "ಮುಷ್ಕರ", "ಪ್ರತಿಭಟನೆ", "ರೈತ",
                "ಕಾರ್ಮಿಕ", "ನೌಕರ", "ಶಿಕ್ಷಕ", "ವಿದ್ಯಾರ್ಥಿ", "ಸ್ಫೂರ್ತಿ", "ಮಾನವೀಯ", "ಹಾಡು", "ಸಾಧನೆ", "ಹೆಮ್ಮೆ")


def _special_headlines():
    import glob, json
    out = set()
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "specials", "*.json")):
        if f.endswith("live.json"): continue
        try: out.add(json.load(open(f)).get("story", {}).get("headline", "").strip())
        except Exception: pass
    return out


def pick(stories):
    skip = _special_headlines()
    ok = [i for i, s in enumerate(stories) if not s.get("special_clip") and s.get("headline", "").strip() not in skip]
    if not ok: return []
    idx = [ok[0]]
    for tag in ("ಕ್ರೀಡೆ", "ಸಿನಿಮಾ", "ಟೆಕ್"):
        j = next((i for i in ok if stories[i].get("tag") == tag and i not in idx), None)
        if j is not None: idx.append(j)
    for i in ok:
        if len(idx) >= 4: break
        if i not in idx: idx.append(i)
    idx = idx[:4]
    def people(s):
        t = s.get("headline", "") + " " + s.get("body", "")
        return sum(w in t for w in PEOPLE_WORDS)
    best = max((i for i in ok if i not in idx), key=lambda i: people(stories[i]), default=None)
    if best is not None and people(stories[best]) >= 2 and not any(people(stories[i]) >= 2 and stories[i].get("tag") in ("ರಾಜ್ಯ", "ರಾಷ್ಟ್ರೀಯ") for i in idx[:1]):
        idx.append(best)   # 5th Short: the people story
    return idx


def make_short(cfg, voices, here, work, header="ಇಂದಿನ ಪ್ರಮುಖ ಸುದ್ದಿಗಳು", out_name=None):
    import make_bulletin as mb, brand
    FPS, SR = mb.FPS, mb.SR
    stories = cfg["stories"]; sel = [0] if len(stories) == 1 else pick(stories)   # one-story Short: always that story
    A = lambda n: mb.load(os.path.join(here, os.environ.get("VN_MUSIC", "audio2"), n))
    sting, bed, intro_m = A("sting.wav"), A("bed.wav"), A("intro.wav")
    sig = os.path.join(here, "audio2", "signature.wav")
    # timeline
    OPEN, HOLD, END = 2.2, 2.4, 2.6
    CR = 7.5 if os.path.exists(os.path.join(here, "audio2", "signature.wav")) else 0.0
    credit = mb.build_credit() if CR else None
    segs, t = [], OPEN
    for i in sel:
        ln = len(voices[f"h{i}"]) / SR + HOLD
        segs.append((i, t, ln)); t += ln
    total = t + END + CR
    mix = np.zeros((int(total * SR) + SR, 2), np.float32)
    def put(sig_, at, g):
        a = int(at * SR); b = min(len(mix), a + len(sig_)); mix[a:b] += sig_[:b - a] * g
    put(intro_m[: int(2.6 * SR)], 0, 0.7)
    n = len(mix); put(np.tile(bed, (n // len(bed) + 1, 1))[:n], 0, 0.18)
    for i, st, ln in segs:
        put(sting, st - 0.55, 0.6); put(voices[f"h{i}"], st + 0.35, 1.05)
    if CR: put(mb.load(sig), t + END, 1.0)   # gold "A VIJAY MELPAL PRODUCTION" with the beats
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    wav = os.path.join(work, "short_mix.wav"); wavfile.write(wav, SR, (mix * 32767).astype(np.int16))

    # static layers
    g = np.linspace(0, 1, SH)[:, None]
    top, bot = np.array([10, 20, 52]), np.array([30, 8, 22])
    bgarr = (top + (bot - top) * g)[:, None, :].repeat(SW, 1).astype(np.uint8)
    BG = Image.fromarray(bgarr, "RGB").convert("RGBA"); d = ImageDraw.Draw(BG)
    ov = Image.new("RGBA", (SW, SH), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for k in range(-SH, SW, 90): od.line((k, 0, k + SH, SH), fill=(255, 255, 255, 9), width=18)
    BG.alpha_composite(ov); d = ImageDraw.Draw(BG)
    lg = brand.mark(150); BG.alpha_composite(lg, (60, 80))
    wm = brand.wordmark(74, kn=False); BG.alpha_composite(wm, (230, 105))
    mb.draw_text(d, 60, 300, header, 58, fill=mb.GOLD)
    d.rounded_rectangle((60, 1660, 1020, 1770), 55, fill=mb.RED)
    mb.draw_text(d, 540, 1735, "ಪೂರ್ಣ ಸುದ್ದಿ 24x7 ಲೈವ್‌ನಲ್ಲಿ ನೋಡಿ", 48, anchor="m")
    d.text((540, 1830), "@VijayNewsKannada", font=mb.font("latr", 40), fill=mb.GREY, anchor="ms")
    mb.draw_text(d, 540, 1885, "ಸಂಪೂರ್ಣ AI ಸುದ್ದಿ ವಾಹಿನಿ • AI ಧ್ವನಿ • AI ಸಾಂಕೇತಿಕ ದೃಶ್ಯ", 28, fill=mb.GREY, anchor="m", bold=False)

    pics = {}
    for i in sel:
        p = stories[i].get("broll_still") or stories[i].get("broll")
        if p and os.path.exists(p) and not p.lower().endswith((".mp4", ".mov", ".webm")):
            im = Image.open(p).convert("RGB"); sc = max(960 * 1.2 / im.width, 600 * 1.2 / im.height)
            pics[i] = im.resize((int(im.width * sc) + 2, int(im.height * sc) + 2), Image.LANCZOS)
    mask = Image.new("L", (960, 600), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, 959, 599), 34, fill=255)

    out_dir = os.path.join(here, "shorts"); os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, out_name or time.strftime("short_%Y%m%d_%H%M.mp4"))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}", "-r", str(FPS),
                           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out + ".part.mp4"], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        tt = fi / FPS; fr = BG.copy(); d = ImageDraw.Draw(fr)
        cur = next(((i, st, ln) for i, st, ln in segs if st <= tt < st + ln), None)
        if tt < OPEN:   # opening title
            a = mb.ease(tt / 0.5)
            mb.draw_text(d, 540, 900, "ಕನ್ನಡ ನ್ಯೂಸ್ ಲೈವ್", int(96 * (0.8 + 0.2 * a)), anchor="m")
            mb.draw_text(d, 540, 1010, stories[sel[0]].get("section", "") if len(sel) == 1 else "ರಾಜ್ಯ • ಕ್ರೀಡೆ • ಸಿನಿಮಾ • ಟೆಕ್", 44, fill=mb.GOLD, anchor="m")
        elif cur:
            i, st, ln = cur; lt = tt - st; s = stories[i]; a = mb.ease(lt / 0.4); x = int((1 - a) * 200)
            if i in pics:
                im = pics[i]; u = min(1, lt / ln); iw, ih = im.size
                cw = int(iw - (iw - 960) * u * 0.8); ch = int(cw * 600 / 960)
                crop = im.crop(((iw - cw) // 2, (ih - ch) // 2, (iw - cw) // 2 + cw, (ih - ch) // 2 + ch)).resize((960, 600), Image.BILINEAR)
                fr.paste(crop, (60 + x, 380), mask)
                d.rounded_rectangle((80 + x, 920, 330 + x, 960), 10, fill=(0, 0, 0, 160))
                mb.draw_text(d, 205 + x, 950, "AI ಸಾಂಕೇತಿಕ ದೃಶ್ಯ", 24, anchor="m", bold=False)
            else:
                ov2 = Image.new("RGBA", (SW, SH), (0, 0, 0, 0)); ImageDraw.Draw(ov2).rounded_rectangle((60 + x, 380, 1020 + x, 980), 34, fill=(255, 255, 255, 18))
                fr.alpha_composite(ov2); d = ImageDraw.Draw(fr)
                d.text((540 + x, 760), s.get("stat", ""), font=mb.font("beb", 260), fill=mb.GOLD, anchor="ms")
            tw = mb.text_w(s["tag"], 40) + 50
            d.rounded_rectangle((60 + x, 1030, 60 + x + tw, 1100), 14, fill=mb.RED); mb.draw_text(d, 85 + x, 1080, s["tag"], 40)
            mb.draw_text(d, 90 + x + tw, 1080, "• " + s.get("place", ""), 38, fill=mb.GOLD)
            for j, l in enumerate(mb.wrap(s["headline"], 74, 960)[:3]): mb.draw_text(d, 60 + x, 1210 + j * 100, l, 74)
            hl_n = len(mb.wrap(s["headline"], 74, 960)[:3])
            if len(sel) == 1 and s.get("facts"):   # one-story Short: the story's key points, one after another
                fs = s["facts"]; fk = min(len(fs) - 1, int(lt / max(0.1, ln / len(fs)))); fa = mb.ease((lt - fk * ln / len(fs)) / 0.4)
                y0 = 1210 + hl_n * 100 + 20
                lines = mb.wrap(fs[fk], 46, 900)[:2]
                ovl = Image.new("RGBA", (SW, SH), (0, 0, 0, 0)); od2 = ImageDraw.Draw(ovl)
                od2.rounded_rectangle((60, y0, 1020, y0 + 40 + 62 * len(lines)), 20, fill=(255, 255, 255, int(30 * fa)))
                od2.rectangle((60, y0, 68, y0 + 40 + 62 * len(lines)), fill=mb.GOLD + (int(255 * fa),))
                for j, l in enumerate(lines): mb.draw_text(od2, 95, y0 + 70 + j * 62, l, 46, fill=(255, 255, 255, int(255 * fa)))
                fr.alpha_composite(ovl); d = ImageDraw.Draw(fr)
            elif i in pics and s.get("stat"):
                d.text((60 + x, 1590), s["stat"], font=mb.font("beb", 110), fill=mb.GOLD, anchor="ls")
                sw_ = mb.font("beb", 110).getlength(s["stat"])
                for j, l in enumerate(mb.wrap(s.get("stat_label", ""), 34, 900 - sw_)[:2]): mb.draw_text(d, 90 + x + sw_, 1545 + j * 42, l, 34, fill=mb.GREY)
            k = sel.index(i)
            for j in (range(len(sel)) if len(sel) > 1 else []): d.ellipse((480 + j * 40, 1615, 496 + j * 40, 1631), fill=(mb.GOLD if j == k else (90, 100, 130)))
        elif CR and tt >= t + END:   # gold production card (16:9) centred on black
            cf = credit(tt - t - END, CR).convert("RGB").resize((SW, int(SW * 1080 / 1920)), Image.LANCZOS)
            fr = Image.new("RGBA", (SW, SH), (6, 4, 2, 255)); fr.paste(cf, (0, (SH - cf.height) // 2))
            d = ImageDraw.Draw(fr)
            mb.draw_text(d, 540, 560, "ವಿಜಯ್ ನ್ಯೂಸ್ ಕನ್ನಡ", 64, fill=mb.GOLD, anchor="m")
            mb.draw_text(d, 540, 1420, "ಕನ್ನಡದ 100% AI ನ್ಯೂಸ್ ಚಾನೆಲ್", 52, fill=(235, 225, 200), anchor="m")
        else:   # end card
            lt = tt - t; a = mb.ease(lt / 0.5)
            big = brand.mark(300); fr.alpha_composite(big, (390, 640))
            mb.draw_text(d, 540, 1080, "24x7 ಕನ್ನಡ ನ್ಯೂಸ್ ಲೈವ್", 72, fill=(255, 255, 255, int(255 * a)), anchor="m")
            mb.draw_text(d, 540, 1180, "ಪ್ರತಿದಿನ ಬೆಳಿಗ್ಗೆ ಮತ್ತು ಸಂಜೆ 6ಕ್ಕೆ ಹೊಸ ಸುದ್ದಿ", 44, fill=mb.GOLD, anchor="m")
        ff.stdin.write(fr.convert("RGB").tobytes())
    ff.stdin.close(); ff.wait()
    os.replace(out + ".part.mp4", out)
    return out
