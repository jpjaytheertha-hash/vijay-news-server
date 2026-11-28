"""Vijay News English – PROMO 2 (~15 s, premium "behind the scenes"), Vijay 28 Nov 15:39:
"another promo with some punchy lines, premium ones, with showing camera, studio, technicians, OB van driving
in indian roads etc, for about 10-15 seconds. with good positive news themed music".
Real stock footage (Pixabay, fetched at render time – nothing stored), our own positive theme
(music_promo2.py), the channel voice.   python3 promo2.py promo2.mp4"""
import os, sys, subprocess
import numpy as np
from PIL import Image, ImageDraw
from scipy.io import wavfile
import make_bulletin as mb
import brand, promo
from tts import synth

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = mb.W, mb.H, mb.FPS, mb.SR
GOLD, RED, WHITE = mb.GOLD, mb.RED, mb.WHITE

# (seconds, spoken line, on-screen line, Pixabay searches: (query, [tag groups – one word of EACH must be in the tags]))
SHOTS = [
    (2.4, "Lights. Camera. Truth.", "LIGHTS. CAMERA. TRUTH.",
     [("broadcast camera", [["camera"], ["broadcast", "television", "tv", "studio", "video camera", "camcorder", "filming"]]),
      ("tv camera studio", [["camera"]])]),
    (2.4, "Built for India's biggest stories.", "BUILT FOR THE BIG STORIES",
     [("tv studio", [["studio"], ["tv", "television", "broadcast", "news", "camera", "lights"]]),
      ("news studio", [["studio"]])]),
    (2.4, "Experts behind every frame.", "EXPERTS BEHIND EVERY FRAME",
     [("broadcast control room", [["control room", "broadcast", "editing", "monitor", "mixer", "production"]]),
      ("video editing", [["editing", "editor", "monitor"]])]),
    (2.6, "On the road, wherever news breaks.", "WHEREVER NEWS BREAKS",
     [("broadcast van", [["van", "truck"], ["broadcast", "satellite", "news", "tv", "television"]]),
      ("satellite truck", [["truck", "van"], ["satellite", "broadcast"]]),
      ("indian highway traffic", [["india", "indian"], ["highway", "road", "traffic"]])]),
    (2.6, "India, on the move.", "INDIA, ON THE MOVE",
     [("indian highway traffic", [["india", "indian"], ["highway", "road", "traffic", "street"]]),
      ("india road", [["india", "indian"], ["road", "street", "traffic"]])]),
]
END = 2.6   # logo card: "Vijay News English. Live, twenty-four by seven."
END_LINE = "Vijay News English. Live, twenty-four by seven."

def main(out):
    work = os.path.join(HERE, "build_promo2"); os.makedirs(work, exist_ok=True)
    # ---- footage: reuse the promo's careful Pixabay picker (full HD, real camera footage, tag groups)
    promo.PROMO_BROLL = {k: qs for k, (_, _, _, qs) in enumerate(SHOTS)}
    promo.CGI_OK = set()
    got = promo.promo_broll(work)
    print("promo2 footage:", {k: os.path.basename(v) for k, v in got.items()}, flush=True)
    total = sum(s[0] for s in SHOTS) + END
    # ---- audio: positive theme + voice lines (slightly above the music)
    mus = os.path.join(work, "positive.wav")
    subprocess.run([sys.executable, os.path.join(HERE, "music_promo2.py"), mus, f"{total:.2f}"], check=True)
    sr, m = wavfile.read(mus); m = m.astype(np.float32) / 32768
    mix = np.zeros((int((total + 0.5) * SR), 2), np.float32); mix[:len(m)] += m[:len(mix)] * 0.55
    t = 0.0; starts = []
    for k, (d, line, _, _) in enumerate(SHOTS + [(END, END_LINE, "", [])]):
        starts.append(t); w = os.path.join(work, f"v{k}.wav"); synth(line, w)
        sr_, v = wavfile.read(w); v = v.astype(np.float32) / 32768
        v = np.stack([v, v], 1) if v.ndim == 1 else v
        if sr_ != SR:   # tts writes 44.1 kHz; resample defensively
            idx = np.linspace(0, len(v) - 1, int(len(v) * SR / sr_)).astype(int); v = v[idx]
        i = int((t + 0.15) * SR); j = min(len(mix), i + len(v)); mix[i:j] += v[:j - i] * 1.35
        t += d
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    wavfile.write(os.path.join(work, "mix.wav"), SR, (mix * 32767).astype(np.int16))
    # ---- video
    LOGO = brand.mark(240); WM = brand.wordmark(90)
    bg = mb.make_bg()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", os.path.join(work, "mix.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-g", "50", "-keyint_min", "50", "-sc_threshold", "0", *mb.vrate(), "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.2:LRA=9", "-ar", "44100", "-ac", "2",
                           "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
    for y in range(H // 2, H, 6): sd.rectangle((0, y, W, y + 6), fill=(4, 8, 24, int(215 * (y - H / 2) / (H / 2))))
    lab_w = int(mb.text_w("Representative visuals", 22, False)) + 40
    LAB = Image.new("RGBA", (lab_w, 40), (0, 0, 0, 0)); ld = ImageDraw.Draw(LAB)
    ld.rounded_rectangle((0, 0, lab_w - 1, 39), 10, fill=(0, 0, 0, 150)); mb.draw_text(ld, lab_w // 2, 29, "Representative visuals", 22, anchor="m", bold=False)
    BUG = brand.wordmark(40)
    cur = None; seg = -1
    for fi in range(int(total * FPS)):
        tt = fi / FPS
        k = max(i for i, s in enumerate(starts) if s <= tt); lt = tt - starts[k]
        if k < len(SHOTS):
            if k != seg:
                seg = k; cur = promo.Clip(got[k], 1.0) if k in got else None
            fr = None
            if cur is not None and cur.next() is not None:
                z = 1.0 + 0.04 * (lt / SHOTS[k][0])          # slow push-in: premium feel
                im = cur.last
                if z > 1.001:
                    cw, ch = int(W / z), int(H / z); x0, y0 = (W - cw) // 2, (H - ch) // 2
                    im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)
                fr = im.convert("RGBA")
            if fr is None:
                off = int((tt * 18) % 600); fr = bg.crop((off, 0, off + W, H)).convert("RGBA")
            fr.alpha_composite(shade)
            L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
            a = mb.ease((lt - 0.12) / 0.35); txt = SHOTS[k][2]
            if a > 0:
                f = mb.font("beb", 120); tw_ = d.textlength(txt, font=f)
                x = 120 - int((1 - a) * 80)
                d.rectangle((x, 905, x + int(min(tw_, 1680) * a), 913), fill=RED)          # red wipe line
                d.text((x, 885), txt, font=f, fill=(255, 255, 255, int(255 * a)), anchor="ls")
            L.alpha_composite(BUG, (W - BUG.width - 60, 50)); L.alpha_composite(LAB, (60, 50))
            fr.alpha_composite(L)
            if lt < 0.12 and k:                                  # quick white flash cut between shots
                fr = Image.blend(fr, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.35 * (1 - lt / 0.12))
        else:   # end card
            off = int((tt * 18) % 600); fr = bg.crop((off, 0, off + W, H)).convert("RGBA")
            L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
            q = mb.back(lt / 0.45); s_ = max(0.01, min(q, 1.1))
            lg = LOGO.resize((max(1, int(240 * s_)), max(1, int(240 * s_)))); L.alpha_composite(lg, (W // 2 - lg.width // 2, 250 - (lg.height - 240) // 2))
            if lt > 0.3: L.alpha_composite(WM, (W // 2 - WM.width // 2, 540))
            b = mb.ease((lt - 0.7) / 0.4)
            if b > 0:
                bw = mb.text_w("LIVE 24x7", 54) + 190; bx = W // 2 - bw / 2
                mb.rrect(d, (bx, 790, bx + bw, 900), 55, RED + (int(255 * b),))
                mb.draw_text(d, W // 2 + 24, 866, "LIVE 24x7", 54, fill=(255, 255, 255, int(255 * b)), anchor="m")
                dx = W // 2 + 24 - mb.text_w("LIVE 24x7", 54) // 2 - 40
                d.ellipse((dx - 12, 834, dx + 12, 858), fill=(255, 255, 255, int(255 * b)))
            fr.alpha_composite(L)
        ff.stdin.write(fr.convert("RGB").tobytes())
    ff.stdin.close(); ff.wait(); print("done", out, f"{total:.1f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "promo2.mp4")
