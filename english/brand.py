"""Vijay News brand identity: geometric 'V' mark + wordmark (original design)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RED_A, RED_B, GOLD, WHITE = (236, 22, 36), (150, 6, 18), (255, 190, 20), (255, 255, 255)

def _grad(s, a, b):
    g = np.linspace(0, 1, s)
    m = (g[:, None] + g[None, :]) / 2
    arr = np.array(a, np.float32) * (1 - m[..., None]) + np.array(b, np.float32) * m[..., None]
    return Image.fromarray(arr.astype(np.uint8)).convert("RGBA")

def mark(s):
    """Rounded-square red tile with a geometric V chevron split white | gold (original design)."""
    S = s * 4
    tile = _grad(S, RED_A, RED_B)
    mask = Image.new("L", (S, S), 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), int(S * .16), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0)); out.paste(tile, (0, 0), mask)
    L, R, T, Bt, cx, w = S * .16, S * .84, S * .22, S * .80, S * .5, S * .19
    vmask = Image.new("L", (S, S), 0); vd = ImageDraw.Draw(vmask)
    vd.polygon([(L, T), (L + w, T), (cx, Bt - w * 1.55), (R - w, T), (R, T), (cx + w * .08, Bt), (cx - w * .08, Bt)], fill=255)
    gap = int(S * .022)
    left = Image.new("L", (S, S), 0); ImageDraw.Draw(left).rectangle((0, 0, cx - gap, S), fill=255)
    right = Image.new("L", (S, S), 0); ImageDraw.Draw(right).rectangle((cx + gap, 0, S, S), fill=255)
    from PIL import ImageChops
    out.paste(Image.new("RGBA", (S, S), WHITE), (0, 0), ImageChops.multiply(vmask, left))
    # gold arm sits slightly lower = forward motion
    rm = ImageChops.multiply(vmask, right); rm = ImageChops.offset(rm, 0, int(S * .035))
    out.paste(Image.new("RGBA", (S, S), GOLD), (0, 0), ImageChops.multiply(rm, mask))
    # thin underline bar = broadcast horizon
    ImageDraw.Draw(out).rectangle((S * .34, S * .865, S * .66, S * .882), fill=WHITE)
    return out.resize((s, s), Image.LANCZOS)

def _f(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size, layout_engine=ImageFont.Layout.RAQM)

def wordmark(h, kn=True, kn_text="ENGLISH"):
    """'VIJAY' + red 'NEWS' block, optional Kannada line. h = cap height-ish in px."""
    fz = int(h * 1.35); f = _f("inter-latin-800-normal.ttf", fz)
    w1 = f.getlength("VIJAY"); w2 = f.getlength("NEWS")
    pad = int(fz * .22); gap = int(fz * .18)
    W = int(w1 + gap + w2 + pad * 2) + 4; Hh = int(fz * 1.05) + (int(fz * .62) if kn else 0)
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    base = int(fz * .88)
    d.text((0, base), "VIJAY", font=f, fill=WHITE, anchor="ls")
    x2 = w1 + gap
    d.rounded_rectangle((x2, base - fz * .80, x2 + w2 + pad * 2, base + fz * .12), int(fz * .12), fill=RED_A)
    d.text((x2 + pad, base), "NEWS", font=f, fill=WHITE, anchor="ls")
    if kn:
        fk = _f("inter-latin-800-normal.ttf", int(fz * .36)); x = 2; sp = int(fz * .09)
        for ch in kn_text:   # "ENGLISH" in gold, letter-spaced (Vijay News English)
            d.text((x, base + fz * .56), ch, font=fk, fill=GOLD, anchor="ls"); x += fk.getlength(ch) + sp
    return im

def lockup(mark_size):
    m = mark(mark_size); wm = wordmark(int(mark_size * .38))
    gap = int(mark_size * .22)
    im = Image.new("RGBA", (m.width + gap + wm.width, max(m.height, wm.height)), (0, 0, 0, 0))
    im.alpha_composite(m, (0, (im.height - m.height) // 2)); im.alpha_composite(wm, (m.width + gap, (im.height - wm.height) // 2 + int(mark_size * .06)))
    return im

if __name__ == "__main__":
    sheet = Image.new("RGBA", (1600, 900), (8, 18, 44, 255))
    sheet.alpha_composite(mark(360), (80, 80))
    sheet.alpha_composite(lockup(180), (560, 150))
    sheet.alpha_composite(lockup(90), (560, 420))
    light = Image.new("RGBA", (1600, 330), (245, 246, 250, 255)); light.alpha_composite(mark(200), (80, 60))
    wm = wordmark(70); light.alpha_composite(wm, (330, 100))
    sheet.alpha_composite(light, (0, 570))
    sheet.convert("RGB").save("chk/logo_sheet.png")
