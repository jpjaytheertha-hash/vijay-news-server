"""Kannada voice: Microsoft neural voice via edge-tts (Mac), offline espeak-ng fallback.
Usage: synth(text, out_wav).  Env: VN_VOICE (kn-IN-SapnaNeural | kn-IN-GaganNeural), VN_RATE, VN_PITCH."""
import subprocess, shutil, os, asyncio, re
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

VOICE = os.environ.get("VN_VOICE", "kn-IN-SapnaNeural")
RATE = os.environ.get("VN_RATE", "+10%")
PITCH = os.environ.get("VN_PITCH", "+2Hz")

KN = "ಀ-೿‌‍"
VIRAMA, ZWNJ = "್", "‌"

# Spoken forms (longest keys first so "ಡಿಸಿಎಂ" wins over "ಸಿಎಂ")
SPOKEN = {
    "ಡಿಸಿಎಂ": "ಉಪಮುಖ್ಯಮಂತ್ರಿ", "ಸಿಎಂ": "ಮುಖ್ಯಮಂತ್ರಿ", "ಕಿ.ಮೀ.": "ಕಿಲೋಮೀಟರ್",
    "COP31": "ಕಾಪ್ ಮೂವತ್ತೊಂದು", "CNN": "ಸಿಎನ್ಎನ್", "EU": "ಯುರೋಪಿಯನ್ ಒಕ್ಕೂಟ",
    "–": " ", "—": ", ",
}
# Kannada spellings of single English letters, used as initials in names
LETTERS = ["ಡಬ್ಲ್ಯು", "ಎಕ್ಸ್", "ಕ್ಯೂ", "ಜೆಡ್", "ಎಚ್", "ಹೆಚ್", "ಎಫ್", "ಎಲ್", "ಎಂ", "ಎನ್", "ಆರ್", "ಎಸ್",
           "ಎ", "ಬಿ", "ಸಿ", "ಡಿ", "ಇ", "ಜಿ", "ಐ", "ಜೆ", "ಕೆ", "ಒ", "ಪಿ", "ಟಿ", "ಯು", "ವಿ", "ವೈ"]
INIT = "(?:" + "|".join(LETTERS) + ")"


# Month abbreviations before a date: "ಡಿ.4" -> "ಡಿಸೆಂಬರ್ 4"
MONTHS = {"ಜ": "ಜನವರಿ", "ಫೆ": "ಫೆಬ್ರವರಿ", "ಮಾ": "ಮಾರ್ಚ್", "ಏ": "ಏಪ್ರಿಲ್", "ಜೂ": "ಜೂನ್", "ಜು": "ಜುಲೈ",
          "ಆ": "ಆಗಸ್ಟ್", "ಸೆ": "ಸೆಪ್ಟೆಂಬರ್", "ಅ": "ಅಕ್ಟೋಬರ್", "ನ": "ನವೆಂಬರ್", "ಡಿ": "ಡಿಸೆಂಬರ್"}
KN_NUM = ["", "ಒಂದು", "ಎರಡು", "ಮೂರು", "ನಾಲ್ಕು", "ಐದು", "ಆರು", "ಏಳು", "ಎಂಟು", "ಒಂಬತ್ತು", "ಹತ್ತು", "ಹನ್ನೊಂದು",
          "ಹನ್ನೆರಡು", "ಹದಿಮೂರು", "ಹದಿನಾಲ್ಕು", "ಹದಿನೈದು", "ಹದಿನಾರು", "ಹದಿನೇಳು", "ಹದಿನೆಂಟು", "ಹತ್ತೊಂಬತ್ತು", "ಇಪ್ಪತ್ತು",
          "ಇಪ್ಪತ್ತೊಂದು", "ಇಪ್ಪತ್ತೆರಡು", "ಇಪ್ಪತ್ತಮೂರು", "ಇಪ್ಪತ್ನಾಲ್ಕು", "ಇಪ್ಪತ್ತೈದು", "ಇಪ್ಪತ್ತಾರು", "ಇಪ್ಪತ್ತೇಳು",
          "ಇಪ್ಪತ್ತೆಂಟು", "ಇಪ್ಪತ್ತೊಂಬತ್ತು", "ಮೂವತ್ತು", "ಮೂವತ್ತೊಂದು"]
_TENS = {20: "ಇಪ್ಪತ್ತು", 30: "ಮೂವತ್ತು", 40: "ನಲವತ್ತು", 50: "ಐವತ್ತು", 60: "ಅರವತ್ತು", 70: "ಎಪ್ಪತ್ತು", 80: "ಎಂಬತ್ತು", 90: "ತೊಂಬತ್ತು"}
_VSIGN = {"ಒ": "ೊ", "ಎ": "ೆ", "ಐ": "ೈ", "ಆ": "ಾ", "ಏ": "ೇ", "ಇ": "ಿ", "ಉ": "ು", "ಓ": "ೋ"}
_HUND = {1: "ನೂರು", 2: "ಇನ್ನೂರು", 3: "ಮುನ್ನೂರು", 4: "ನಾನೂರು", 5: "ಐನೂರು", 6: "ಆರುನೂರು", 7: "ಏಳುನೂರು", 8: "ಎಂಟುನೂರು", 9: "ಒಂಬೈನೂರು"}
def kn_number(n):
    """Integer -> spoken Kannada words, the way a news reader says it (390 -> ಮುನ್ನೂರ ತೊಂಬತ್ತು, 2027 -> ಎರಡು ಸಾವಿರದ ಇಪ್ಪತ್ತೇಳು)."""
    if n == 0: return "ಸೊನ್ನೆ"
    if n < 20: return ["", "ಒಂದು", "ಎರಡು", "ಮೂರು", "ನಾಲ್ಕು", "ಐದು", "ಆರು", "ಏಳು", "ಎಂಟು", "ಒಂಬತ್ತು", "ಹತ್ತು", "ಹನ್ನೊಂದು",
                       "ಹನ್ನೆರಡು", "ಹದಿಮೂರು", "ಹದಿನಾಲ್ಕು", "ಹದಿನೈದು", "ಹದಿನಾರು", "ಹದಿನೇಳು", "ಹದಿನೆಂಟು", "ಹತ್ತೊಂಬತ್ತು"][n]
    if n < 100:
        t, u = _TENS[n // 10 * 10], n % 10
        if not u: return t
        uw = kn_number(u); stem = t[:-1]          # "ಇಪ್ಪತ್ತ"
        return stem + _VSIGN[uw[0]] + uw[1:] if uw[0] in _VSIGN else stem + uw
    if n < 1000:
        h, r = _HUND[n // 100], n % 100
        return h if not r else h[:-1] + " " + kn_number(r)          # ಮುನ್ನೂರ ತೊಂಬತ್ತು
    for size, word, joined in ((10**7, "ಕೋಟಿ", "ಕೋಟಿ"), (10**5, "ಲಕ್ಷ", "ಲಕ್ಷದ"), (1000, "ಸಾವಿರ", "ಸಾವಿರದ")):
        if n >= size:
            q, r = divmod(n, size)
            return (kn_number(q) + " " + (joined if r else word) + (" " + kn_number(r) if r else "")).strip()
def _num_words(m):
    ip, dp, suf = m.group(1).replace(",", ""), m.group(2), m.group(3) or ""
    try: w = kn_number(int(ip))
    except Exception: return m.group(0)
    if dp: w += " ಪಾಯಿಂಟ್ " + " ".join(kn_number(int(c)) for c in dp)
    if suf:   # Kannada suffix glued to the number: "4ನೇ" -> "ನಾಲ್ಕನೇ", "390ರಷ್ಟು" -> "ಮುನ್ನೂರ ತೊಂಬತ್ತರಷ್ಟು"
        w = (w[:-1] if w.endswith("ು") else w) + suf
    return w
def spell_numbers(text):
    text = re.sub(r"(\d+)\s*[-–]\s*(\d+)\s*%", lambda m: "ಶೇಕಡಾ " + kn_number(int(m.group(1)))[:-1] + "ರಿಂದ " + kn_number(int(m.group(2))), text)
    text = re.sub(r"(\d+(?:,\d{2,3})*(?:\.\d+)?)\s*%", lambda m: "ಶೇಕಡಾ " + m.group(1), text)
    text = re.sub(r"(\d)\s+(ರಂದು|ರಿಂದ|ರವರೆಗೆ|ರಷ್ಟು|ರಲ್ಲಿ|ನೇ)(?![{KN}])".replace("{KN}", KN), r"\1\2", text)
    return re.sub(rf"(?<![\d.])(\d{{1,3}}(?:,\d{{2,3}})+|\d+)(?:\.(\d+))?([{KN}][{KN}\u200c]*)?", _num_words, text)
def _date_range(m):
    # Vijay, 26 Nov: "ಫೆ.8-12" must be read "ಫೆಬ್ರವರಿ ಎಂಟರಿಂದ ಹನ್ನೆರಡನೇ ತಾರೀಕಿನವರೆಗೆ", not "ಎಂಟು ಹನ್ನೆರಡು"
    mon, a, b = m.group(1), int(m.group(2)), int(m.group(3))
    mon = MONTHS.get(mon.rstrip(". "), mon.rstrip(". "))
    if not (1 <= a <= 31 and 1 <= b <= 31): return m.group(0)
    return f"{mon} {KN_NUM[a][:-1]}ರಿಂದ {KN_NUM[b][:-1]}ನೇ ತಾರೀಕಿನವರೆಗೆ"
TITLES = {"ಡಾ": "ಡಾಕ್ಟರ್", "ಪ್ರೊ": "ಪ್ರೊಫೆಸರ್", "ಶ್ರೀ": "ಶ್ರೀ", "ಶ್ರೀಮತಿ": "ಶ್ರೀಮತಿ"}
# Acronyms written in Kannada letters are read letter by letter: "ಐಸಿಎಂಆರ್" -> "ಐ ಸಿ ಎಂ ಆರ್"
ACR_SUFFIX = ["ಯೊಂದಿಗೆ", "ನೊಂದಿಗೆ", "ಯಲ್ಲಿ", "ನಲ್ಲಿ", "ಗಳಲ್ಲಿ", "ಯಿಂದ", "ನಿಂದ", "ಯನ್ನು", "ನ್ನು", "ಗಳನ್ನು", "ಗಳು", "ಗಳ",
              "ಗೆ", "ಕ್ಕೆ", "ಯು", "ಯ", "ನ", "ದ", "ಇಂದ", "ಅನ್ನು", "ಅಲ್ಲಿ", "ಇಗೆ", "ಉ", "ಎ", ""]
ACR_KEEP = {"ಬಿಸಿ", "ಸಿಡಿ", "ಇಡೀ", "ಎಂದು"}
ACR_TOK = sorted(LETTERS + ["ಐ", "ಒ", "ಯೂ", "ಇಎ"], key=len, reverse=True)
def _spell(word):
    w = word.replace(ZWNJ, "")
    if w in ACR_KEEP: return None
    for suf in ACR_SUFFIX:
        if suf and not w.endswith(suf): continue
        core = w[:len(w) - len(suf)] if suf else w
        toks, i = [], 0
        while i < len(core):
            t = next((t for t in ACR_TOK if core.startswith(t, i)), None)
            if not t: break
            toks.append(t); i += len(t)
        if i == len(core) and len(toks) >= 2 and core not in ACR_KEEP:
            return " ".join(toks) + (ZWNJ + suf if suf and toks[-1].endswith(VIRAMA) else suf)
    return None

def _join(parts):
    out = parts[0]
    for p in parts[1:]:
        out += (ZWNJ if out.endswith(VIRAMA) else "") + p
    return out

# Words the voices mispronounce -> spoken alternative with the same meaning (screen text unchanged).
# Vijay, 25 Nov 2026: "the pronunciation of mattu is incorrect".
# Vijay, 27 Nov: "ಬಣ್ಣಿಸಲಾಗಿದೆ is pronounced wrong as 'bannalisalagide'" – the voice stumbles on ಣ್ಣಿಸ; say the
# same meaning with ವರ್ಣಿಸಲಾಗಿದೆ (clear and natural). Spoken text only – on-screen text is unchanged.
SAY_INSTEAD = {"ಬಣ್ಣಿಸಲಾಗಿದೆ": "ವರ್ಣಿಸಲಾಗಿದೆ", "ಬಣ್ಣಿಸಿದ್ದಾರೆ": "ವರ್ಣಿಸಿದ್ದಾರೆ", "ಬಣ್ಣಿಸಿದರು": "ವರ್ಣಿಸಿದರು", "ಬಣ್ಣಿಸಿದೆ": "ವರ್ಣಿಸಿದೆ"}
# Vijay, 27 Nov: "the word FINAL should be pronounced as in English" – ಫ here is the English 'f', not 'ph'
ENGLISH_F_HINT = (" English loanwords are said the way Indian TV anchors say them (Indian English, not American or British): ಫ಼ೈನಲ್ = 'fai-nal' with a clear 'f' and the 'nal' fully spoken, "
                  "ಸೆಮಿಫ಼ೈನಲ್ = 'semi-fainal' said as ONE word in one breath with no pause, ಕ್ವಾರ್ಟರ್‌ಫ಼ೈನಲ್ likewise one word "
                  "(never an aspirated 'ph'); likewise ಫುಟ್‌ಬಾಲ್ = 'football', ಫೋನ್ = 'phone', ಫೇಸ್‌ಬುಕ್ = 'Facebook', ಫಿಲ್ಮ್ = 'film'. Wherever a ಫ carries a dot (ಫ಼) it is the English 'f' sound (ಆಫ಼್ = 'off', ಫ಼್ರೀ = 'free', ಟ್ರೋಫ಼ಿ = 'trophy'). "
                  "Read ONLY the numbered/given text – never add a greeting, a sign-off or the channel name that is not in the text. "
                  "If the text itself contains the channel's sign-off line, say it warmly like a TV anchor: 'Vijay News' as in English, then the "
                  "Kannada verb with a long 'O', retroflex d, a light soft dental 'tti', no stress on the end.")   # e.g. {"ಮತ್ತು": "ಹಾಗೂ"} – Vijay chose to keep ಮತ್ತು with the corrected pronunciation hint (25 Nov)

# Vijay, 27 Nov: "the word FINAL should be pronounced as in English" (in every script: bulletin, promo, Shorts, both
# voices) – English sports words are given to the voice in English letters, so neither voice says 'phainal'.
# Vijay, 27 Nov (later): "FINAL is like in English, make it Indian accent, and 'semi final' to be said as one word,
# as real humans pronounce" -> Kannada letters with the English-f mark (ಫ಼), Indian TV-anchor style 'fai-nal';
# semi-final / quarter-final joined into ONE word (no space, no hyphen) so there is no pause in the middle.
ENGLISH_WORDS = [("ಕ್ವಾರ್ಟರ್‌ಫೈನಲ್", "ಕ್ವಾರ್ಟರ್‌ಫ಼ೈನಲ್"), ("ಕ್ವಾರ್ಟರ್ ಫೈನಲ್", "ಕ್ವಾರ್ಟರ್‌ಫ಼ೈನಲ್"), ("ಕ್ವಾರ್ಟರ್-ಫೈನಲ್", "ಕ್ವಾರ್ಟರ್‌ಫ಼ೈನಲ್"),
                 ("ಸೆಮಿಫೈನಲ್", "ಸೆಮಿಫ಼ೈನಲ್"), ("ಸೆಮಿ ಫೈನಲ್", "ಸೆಮಿಫ಼ೈನಲ್"), ("ಸೆಮಿ-ಫೈನಲ್", "ಸೆಮಿಫ಼ೈನಲ್"), ("ಫೈನಲ್", "ಫ಼ೈನಲ್"),
                 ("semi-final", "ಸೆಮಿಫ಼ೈನಲ್"), ("semi final", "ಸೆಮಿಫ಼ೈನಲ್"), ("semifinal", "ಸೆಮಿಫ಼ೈನಲ್"), ("quarter-final", "ಕ್ವಾರ್ಟರ್‌ಫ಼ೈನಲ್"),
                 # Vijay, 27 Nov: "pronunciation of FINANCIAL is said a P ..make it as in english. Check all thoroughly"
                 ("ಫೈನಾನ್ಶಿಯಲ್", "financial"), ("ಫೈನಾನ್ಷಿಯಲ್", "financial"), ("ಫೈನಾನ್ಸ್", "finance"), ("ಫಿನ್‌ಟೆಕ್", "fintech"),
                 ("ಫೇಸ್‌ಬುಕ್", "Facebook"), ("ಫೇಸ್ ಬುಕ್", "Facebook"), ("ಫುಟ್‌ಬಾಲ್", "football"), ("ಫುಟ್ಬಾಲ್", "football"),
                 ("ಫೋನ್", "phone"), ("ಸ್ಮಾರ್ಟ್‌ಫೋನ್", "smartphone"), ("ಫೋಟೋ", "photo"), ("ಫ್ಲೈಟ್", "flight"), ("ಫೀಚರ್", "feature"),
                 ("ಫ್ಯಾಕ್ಟರಿ", "factory"), ("ಫೆಡರಲ್", "federal"), ("ಫೆಡರೇಶನ್", "federation"), ("ಫಂಡ್", "fund"), ("ಫೈಲ್", "file"),
                 ("ಫಾಸ್ಟ್‌ಟ್ಯಾಗ್", "FASTag"), ("ಫ್ರಾನ್ಸ್", "France"), ("ಫಿಫಾ", "FIFA"), ("ಟ್ರೋಫಿ", "trophy"), ("ಆಫೀಸ್", "office"),
                 ("ಸಾಫ್ಟ್‌ವೇರ್", "software"), ("ಇನ್ಫೋಸಿಸ್", "Infosys"), ("ಡಿಫೆನ್ಸ್", "defence"), ("ಫಿಲ್ಮ್", "film"), ("ಫ್ಯಾಷನ್", "fashion"),
                 ("ಫೀಸ್", "fees"), ("ಫಿಟ್ನೆಸ್", "fitness"), ("ಫಾರೆಕ್ಸ್", "forex"), ("ಫಾರ್ಮುಲಾ", "formula"), ("ಫ್ರೀ", "free")]
ENGLISH_WORDS.sort(key=lambda kv: -len(kv[0]))   # longest first (ಸ್ಮಾರ್ಟ್‌ಫೋನ್ before ಫೋನ್)

F_LOANS = ["ಟ್ರೋಫಿ", "ಆಫೀಸ್", "ಆಫೀಸರ್", "ಫೋನ್", "ಫೇಸ್‌ಬುಕ್", "ಫುಟ್‌ಬಾಲ್", "ಫಿಲ್ಮ್", "ಫ್ಯಾಷನ್", "ಫೀಸ್", "ಫೋಟೋ", "ಫ್ಲೈಟ್",
           "ಫೆಡರೇಶನ್", "ಫಂಡ್", "ಫಾರ್ಮ್", "ಫೈಲ್", "ಫ್ಯಾನ್", "ಫಾಸ್ಟ್", "ಫಿಟ್", "ಫಿಫಾ", "ಡಿಫೆನ್ಸ್", "ಇನ್ಫೋಸಿಸ್", "ಸಾಫ್ಟ್‌ವೇರ್"]

def _english_f(word):
    """English loanwords (ಆಫ್, ಫ್ರೀ, ಫೀಡ್, ಫೈನಾನ್ಶಿಯಲ್, ಟ್ರೋಫಿ…): ಫ is the English 'f' -> write ಫ಼ (nukta), which
    both voices read as 'f'. Native Kannada words (ಫಲ, ಫಲಿತಾಂಶ…) never end in ್ and keep ಫ."""
    if "ಫ" not in word: return word
    if "ಫ್" in word or word.rstrip("\u200c").endswith("್") or any(word.startswith(l) for l in F_LOANS):
        return word.replace("ಫ಼", "ಫ").replace("ಫ", "ಫ಼")
    return word


# Vijay, 27 Nov: "the letters ta, tha, da, dha – check once for all and add to the script checks, so that no future glitch".
# Before every recording the text is scanned: each word with a dental (ತ ಥ ದ ಧ) or retroflex (ಟ ಠ ಡ ಢ) letter is
# romanised (dental = th / dh, retroflex = capital T / D) and listed for the voice. English letters only – a Kannada
# example in the instructions was once read aloud by the voice.
_CONS = {"ಕ":"k","ಖ":"kh","ಗ":"g","ಘ":"gh","ಙ":"ng","ಚ":"ch","ಛ":"chh","ಜ":"j","ಝ":"jh","ಞ":"ny",
         "ಟ":"T","ಠ":"Th","ಡ":"D","ಢ":"Dh","ಣ":"N","ತ":"th","ಥ":"thh","ದ":"dh","ಧ":"dhh","ನ":"n",
         "ಪ":"p","ಫ":"ph","ಬ":"b","ಭ":"bh","ಮ":"m","ಯ":"y","ರ":"r","ಲ":"l","ವ":"v","ಶ":"sh","ಷ":"Sh",
         "ಸ":"s","ಹ":"h","ಳ":"L","ೞ":"zh","ಱ":"r"}
_VOW = {"ಅ":"a","ಆ":"aa","ಇ":"i","ಈ":"ee","ಉ":"u","ಊ":"oo","ಋ":"ru","ಎ":"e","ಏ":"ay","ಐ":"ai","ಒ":"o","ಓ":"oh","ಔ":"au"}
_SIGN = {"ಾ":"aa","ಿ":"i","ೀ":"ee","ು":"u","ೂ":"oo","ೃ":"ru","ೆ":"e","ೇ":"ay","ೈ":"ai","ೊ":"o","ೋ":"oh","ೌ":"au"}

def romanise(word):
    out = []; w = word.replace("‌", "").replace("‍", "")
    for i, c in enumerate(w):
        if c in _CONS:
            out.append(_CONS[c]); nx = w[i + 1] if i + 1 < len(w) else ""
            if nx not in _SIGN and nx != "್" and nx != "಼": out.append("a")
        elif c in _SIGN: out.append(_SIGN[c])
        elif c in _VOW: out.append(_VOW[c])
        elif c == "ಂ": out.append("m")
        elif c == "ಃ": out.append("h")
    return "".join(out)

def letter_notes(text, limit=12):
    """English-only pronunciation notes for the dental/retroflex words of this text."""
    import re as _re
    dental, retro = [], []
    for w in _re.findall(r"[ಀ-೿‌]+", text):
        r_ = romanise(w)
        if not r_: continue
        if any(c in w for c in "ತಥದಧ") and r_ not in dental: dental.append(r_)
        if any(c in w for c in "ಟಠಡಢ") and r_ not in retro: retro.append(r_)
    if not dental and not retro: return ""
    n = " PRONUNCIATION CHECK FOR THIS TEXT (instructions only – never read these romanised words aloud): "
    if dental: n += "these words have the SOFT DENTAL th/dh (tongue on the back of the upper teeth, like Hindi त/द; never a hard English T/D): " + ", ".join(dental[:limit]) + ". "
    if retro: n += "these words have the HARD RETROFLEX T/D (tongue curled back): " + ", ".join(retro[:limit]) + ". "
    return n

def normalize(text, spell=True):
    for k, v in ENGLISH_WORDS:
        text = re.sub(k + "\u200c?", v + ("\u200c" if re.match(r"[\u0C80-\u0CFF]", v) else " "), text)   # Kannada keeps its suffix joined (ಫ಼ೈನಲ್‌ಗೆ)
    text = re.sub(r"[\u0C80-\u0CFF\u200c]+", lambda m: _english_f(m.group(0)), text)
    _mon = "|".join(sorted([re.escape(k) + r"\." for k in MONTHS] + list(MONTHS.values()), key=len, reverse=True))
    text = re.sub(rf"(?<![{KN}])({_mon})\s*(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})(?!\d)", _date_range, text)
    for k, v in SAY_INSTEAD.items():
        text = re.sub(rf"(?<![{KN}]){k}(?![{KN}])", v, text)
    for k in sorted(SPOKEN, key=len, reverse=True):   # whole words only ("ಸಿಎಂ" but not inside "ಐಸಿಎಂಆರ್")
        text = re.sub(rf"(?<![{KN}]){re.escape(k)}", SPOKEN[k], text) if re.match(rf"[{KN}]", k) else text.replace(k, SPOKEN[k])
    for k, v in TITLES.items():   # "ಡಾ. ರಾಜೀವ್" -> "ಡಾಕ್ಟರ್ ರಾಜೀವ್"
        text = re.sub(rf"(?<![{KN}]){k}\.\s*", v + " ", text)
    for k, v in MONTHS.items():   # "ಡಿ.4" / "ಡಿ. 4" -> "ಡಿಸೆಂಬರ್ 4"
        text = re.sub(rf"(?<![{KN}]){k}\.\s*(?=\d)", v + " ", text)
    if spell: text = spell_numbers(text)   # Vijay, 26 Nov: read numbers like a human news reader, in Kannada words
    text = re.sub(r"(?<=\S)-(?=\S)", " ", text)   # "ಜಿಪಿಟಿ-6" -> "ಜಿಪಿಟಿ 6"
    # Initials spoken as ONE word, like Kannada TV: "ಡಿ.ಕೆ. ಶಿವಕುಮಾರ್" -> "ಡಿಕೆ ಶಿವಕುಮಾರ್"
    text = re.sub(rf"(?<![{KN}])({INIT}\.\s?(?:{INIT}\.\s?){{1,3}})",
                  lambda m: _join([g for g in re.split(r"\.\s?", m.group(1)) if g]) + "\x01 ", text)
    # acronyms letter by letter (ಐಸಿಎಂಆರ್ -> ಐ ಸಿ ಎಂ ಆರ್); dotted initials joined above are kept as one word
    text = re.sub(rf"[{KN}]+", lambda m: m.group(0) if "\x00" in m.group(0) else (_spell(m.group(0)) or m.group(0)), text)
    # standalone abbreviations only (not word endings like "ಹಾಸನ.")
    text = re.sub(rf"(?<![{KN}])ಶೇ\.\s*", "ಶೇಕಡಾ ", text)
    text = re.sub(rf"(?<![{KN}])ರೂ\.\s*", "ರೂಪಾಯಿ ", text)
    text = re.sub(rf"([{KN}]+)\x01", r"\1", text).replace("\x01", "")
    text = text.replace(";", ".")
    return re.sub(r"\s+", " ", text).strip()

def _edge(text, wav):
    import edge_tts
    mp3 = wav[:-4] + ".mp3"
    asyncio.run(edge_tts.Communicate(normalize(text), VOICE, rate=RATE, pitch=PITCH).save(mp3))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3,
                    "-af", "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-ac", "1", wav], check=True)

GEMINI_KEYFILE = os.path.expanduser("~/.vijaynews_gemini_key")
# Vijay, 25 Nov 2026: "the news read for Rahul Gandhi section voice is good. Try retaining that for all."
# That clip was a single-story request on gemini-2.5-flash-preview-tts (Puck) -> make that the standard.
GEMINI_MODEL = os.environ.get("VN_GEMINI_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_VOICE = os.environ.get("VN_GEMINI_VOICE", "Puck")   # female: Kore, Aoede · male: Charon, Puck
GEMINI_STYLE = os.environ.get("VN_GEMINI_STYLE",
    "Read the following Kannada news text exactly as written, like a top Kannada TV news anchor: "
    "confident, energetic, crisp and fast-paced broadcast delivery, clear native Kannada pronunciation, "
    "names spoken smoothly as single words, short natural pauses at commas and full stops. "
    "Pronounce like a native Bengaluru/Mysuru Kannada anchor (no Hindi or Tamil accent): the Kannada ತ and ದ are DENTAL (tongue touching the back of the upper teeth: the soft Indian 'th' and 'dh' sounds) – never the hard English or retroflex 't'/'d' (ಟ/ಡ); only ಟ ಠ ಡ ಢ ಣ are retroflex. This applies to EVERY form: ತ ತಾ ತಿ ತು ತೆ ತೇ ತೊ ತ್ತ ತ್ತೆ ತ್ತಿ ತ್ರ – e.g. ಮತ್ತೆ = 'muth-the', ಇತ್ತೀಚಿನ = 'ith-thee-chi-na', ಬರುತ್ತೇವೆ = 'ba-ruth-thay-ve', ತೆರಿಗೆ = 'the-ri-ge', ಸಮಿತಿ = 'sa-mi-thi' – a soft 'the/thi/thu', NEVER a hard 'Te/Ta' as in English 'ten' or 'table'. Example: ಪಂದ್ಯ (match) = 'pan-dhya' with a soft dental dh, never 'pan-Da'; ದೇಶ = 'dhesha'; ಆದಾಯ (income) = 'aa-dhaa-ya' – soft dental 'dh', NOT a hard 'Da', and no stress on it; same for ಆದರೆ 'aa-dha-re', ಆದೇಶ 'aa-dhe-sha', ಉದ್ಯೋಗ 'udh-yo-ga', ಸುದ್ದಿ 'sudh-dhi'. ಮತ್ತು (= 'and') is said 'muth-thu': the double ತ್ತ is the SOFT DENTAL 'th' (tongue touching the back of the upper teeth, like Hindi त in 'तुम'), NEVER the hard English 'T' of 'mutt' or 'butter'; it ends in a clearly spoken short 'u'; light, quick and unstressed. Do not stress or force these dental syllables (ತ್ತ, ದ್ಯ, ತ್ಯ…) – keep them soft and even; same for ಮತ್ತೆ 'math-the', ಹತ್ತು 'hath-thu', ಎತ್ತು 'eth-thu'. Numbers too, all with soft dental th and even rhythm: ಹತ್ತೊಂಬತ್ತು 'hath-thom-bath-thu' (19), ತೊಂಬತ್ತು 'thom-bath-thu' (90), ಇಪ್ಪತ್ತು 'ip-path-thu' (20), ಮೂವತ್ತು 'moo-vath-thu' (30), ಎಂಬತ್ತು 'em-bath-thu' (80), ಎಪ್ಪತ್ತು 'ep-path-thu' (70), ಅರವತ್ತು 'a-ra-vath-thu' (60), ಐವತ್ತು 'ai-vath-thu' (50) – say each number smoothly as one word; ಳ and ಣ retroflex; every short final vowel clearly spoken." + ENGLISH_F_HINT + " Text:")

GEMINI_MODELS = [GEMINI_MODEL] + [m for m in ("gemini-2.5-flash-preview-tts", "gemini-3.1-flash-tts-preview", "gemini-2.5-pro-preview-tts") if m != GEMINI_MODEL]
_SPENT = set()   # models whose free quota ran out in this run

def _gemini_pcm(prompt):
    """One Gemini TTS request -> int16 numpy array at 24 kHz. Same voice (Puck) on every model;
    when one model's free quota is used up, the next model is tried (each has its own quota)."""
    import json, base64, urllib.request, urllib.error, time
    import numpy as np
    key = open(GEMINI_KEYFILE).read().strip()
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_VOICE}}}}}
    last = None
    for model in [m for m in GEMINI_MODELS if m not in _SPENT]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(4):
            req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "x-goog-api-key": key})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = json.load(r)
                try:
                    pcm = base64.b64decode(data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
                    return np.frombuffer(pcm, dtype=np.int16)
                except (KeyError, IndexError):
                    why = (data.get("candidates") or [{}])[0].get("finishReason") or str(data.get("promptFeedback", ""))[:120]
                    last = RuntimeError(f"Google TTS returned no audio ({why})")
                    if attempt < 1: time.sleep(20); continue
                    raise last
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", "ignore")
                if e.code in (500, 503) and attempt < 3:
                    time.sleep(20 * (attempt + 1)); continue
                if e.code == 429:
                    daily = "perday" in msg.lower().replace("_", "").replace(" ", "") or "per day" in msg.lower()
                    if not daily and attempt < 1:
                        time.sleep(65); continue   # per-minute limit: wait once
                    print(f"  quota used up on {model} – trying next model", flush=True)
                    _SPENT.add(model); last = RuntimeError(f"Google TTS HTTP 429 per day: {model}"); break
                if e.code == 404:
                    _SPENT.add(model); last = RuntimeError(f"Google TTS model not available: {model}"); break
                raise RuntimeError(f"Google TTS HTTP {e.code}: {msg[:300]}")
    raise last or RuntimeError("Google TTS: no model available")

def _post(raw, wav):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
                    "-af", "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-ac", "1", wav], check=True)

def _write24(arr, path):
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(arr.astype("int16").tobytes())

def _gemini(text, wav):
    pcm = _gemini_pcm(GEMINI_STYLE + "\n" + normalize(text)).tobytes()
    import wave
    raw = wav[:-4] + ".pcm.wav"
    with wave.open(raw, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
                    "-af", "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-ac", "1", wav], check=True)

BATCH_STYLE = (
    "You are a top Kannada TV news anchor. Read the numbered Kannada paragraphs below exactly as written: "
    "confident, energetic, crisp, fast-paced broadcast delivery with clear native Kannada pronunciation; "
    "names and initials spoken smoothly as single words. Do NOT read the paragraph numbers aloud. "
    "Pronounce like a native Bengaluru/Mysuru Kannada anchor (no Hindi or Tamil accent): the Kannada ತ and ದ are DENTAL (tongue touching the back of the upper teeth: the soft Indian 'th' and 'dh' sounds) – never the hard English or retroflex 't'/'d' (ಟ/ಡ); only ಟ ಠ ಡ ಢ ಣ are retroflex. This applies to EVERY form: ತ ತಾ ತಿ ತು ತೆ ತೇ ತೊ ತ್ತ ತ್ತೆ ತ್ತಿ ತ್ರ – e.g. ಮತ್ತೆ = 'muth-the', ಇತ್ತೀಚಿನ = 'ith-thee-chi-na', ಬರುತ್ತೇವೆ = 'ba-ruth-thay-ve', ತೆರಿಗೆ = 'the-ri-ge', ಸಮಿತಿ = 'sa-mi-thi' – a soft 'the/thi/thu', NEVER a hard 'Te/Ta' as in English 'ten' or 'table'. Example: ಪಂದ್ಯ (match) = 'pan-dhya' with a soft dental dh, never 'pan-Da'; ದೇಶ = 'dhesha'; ಆದಾಯ (income) = 'aa-dhaa-ya' – soft dental 'dh', NOT a hard 'Da', and no stress on it; same for ಆದರೆ 'aa-dha-re', ಆದೇಶ 'aa-dhe-sha', ಉದ್ಯೋಗ 'udh-yo-ga', ಸುದ್ದಿ 'sudh-dhi'. ಮತ್ತು (= 'and') is said 'muth-thu': the double ತ್ತ is the SOFT DENTAL 'th' (tongue touching the back of the upper teeth, like Hindi त in 'तुम'), NEVER the hard English 'T' of 'mutt' or 'butter'; it ends in a clearly spoken short 'u'; light, quick and unstressed. Do not stress or force these dental syllables (ತ್ತ, ದ್ಯ, ತ್ಯ…) – keep them soft and even; same for ಮತ್ತೆ 'math-the', ಹತ್ತು 'hath-thu', ಎತ್ತು 'eth-thu'. Numbers too, all with soft dental th and even rhythm: ಹತ್ತೊಂಬತ್ತು 'hath-thom-bath-thu' (19), ತೊಂಬತ್ತು 'thom-bath-thu' (90), ಇಪ್ಪತ್ತು 'ip-path-thu' (20), ಮೂವತ್ತು 'moo-vath-thu' (30), ಎಂಬತ್ತು 'em-bath-thu' (80), ಎಪ್ಪತ್ತು 'ep-path-thu' (70), ಅರವತ್ತು 'a-ra-vath-thu' (60), ಐವತ್ತು 'ai-vath-thu' (50) – say each number smoothly as one word; ಳ and ಣ retroflex; every short final vowel clearly spoken." + ENGLISH_F_HINT + " "
    "After each paragraph, stay completely silent for two full seconds before the next one.\n\n")
# Vijay, 27 Nov: "the headline reading pronunciation should be same as detailed reader tone ... currently it is
# reading like a bot, make it near to human" -> headlines get the same anchor voice, read as real spoken sentences.
HEAD_STYLE = BATCH_STYLE.replace("Read the numbered Kannada paragraphs below exactly as written: ",
    "Read the numbered Kannada paragraphs below exactly as written. Most of them are short news HEADLINES: say each one "
    "as a complete, natural spoken sentence with the same warm, human anchor voice, tone and pronunciation you use for "
    "a full news report – natural rise and fall, emphasis on the key word, never flat, never like reading out a list: ")

def split_on_pauses(a, n, lens, sr=24000):
    """Cut int16 audio `a` into n parts at the n-1 longest pauses. lens = text lengths for a sanity check."""
    import numpy as np
    x = a.astype(np.float32) / 32768.0
    hop = int(sr * 0.02); m = len(x) // hop
    if m < 10: raise ValueError("audio too short")
    rms = np.sqrt((x[: m * hop].reshape(m, hop) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms); thr = max(db.max() - 38, np.percentile(db, 10) + 6)
    quiet = db < thr
    runs, i = [], 0
    while i < m:
        if quiet[i]:
            j = i
            while j < m and quiet[j]: j += 1
            if i > 0 and j < m: runs.append((j - i, i, j))
            i = j
        else: i += 1
    if len(runs) < n - 1: raise ValueError(f"found {len(runs)} pauses, need {n-1}")
    cuts = sorted(sorted(runs, reverse=True)[: n - 1], key=lambda r: r[1])
    if n > 1 and cuts[-1][0] * 0.02 < 0.45: raise ValueError("pauses too short to split safely")
    bounds, prev = [], 0
    for _, i0, j0 in cuts: bounds.append((prev, i0)); prev = j0
    bounds.append((prev, m))
    parts = []
    for i0, j0 in bounds:
        seg = quiet[i0:j0]; nz = np.where(~seg)[0]
        if len(nz) == 0: raise ValueError("empty part")
        s0 = max(0, (i0 + nz[0] - 4) * hop); s1 = min(len(a), (i0 + nz[-1] + 6) * hop)
        parts.append(a[s0:s1])
    secs = np.array([len(p) / sr for p in parts]); L = np.array(lens, dtype=float)
    rate = secs / L; med = np.median(rate)
    if np.any(rate < med * 0.45) or np.any(rate > med * 2.2):
        raise ValueError("part lengths don't match the text: " + ", ".join(f"{s:.1f}s/{int(l)}" for s, l in zip(secs, L)))
    return parts

def synth_batch(items, work, groups=None):
    """items: [(key, text)] -> writes work/<key>.wav for all, in small Gemini requests.
    All-or-nothing: raises if any part fails, so a bulletin never mixes two voices.
    Saves every finished group in work/ (cache), so a retry never repeats a request that worked;
    a group that fails is split in half instead of being re-sent whole."""
    import time, hashlib
    keys = [k for k, _ in items]; text = dict(items)
    if groups is None:
        st = [k for k in keys if k.startswith("s") and k != "intro"]
        head = [k for k in keys if k == "intro" or k.startswith("h")]
        tail = [k for k in keys if k == "outro"]
        size = max(1, int(os.environ.get("VN_BODY_GROUP", "1")))   # each story read on its own (best, most natural)
        groups = [head + tail] + [st[i:i + size] for i in range(0, len(st), size)]
    out = {}
    def cache_path(k):
        h = hashlib.md5((GEMINI_VOICE + GEMINI_MODEL + normalize(text[k])).encode()).hexdigest()[:10]
        p_ = os.path.join(work, f"{k}.puck_{h}.npy")
        if not os.path.exists(p_):   # same text already recorded by another Puck model -> reuse it (saves requests)
            for m in GEMINI_MODELS:
                for nt in (normalize(text[k]), normalize(text[k], spell=False)):
                    h2 = hashlib.md5((GEMINI_VOICE + m + nt).encode()).hexdigest()[:10]
                    q = os.path.join(work, f"{k}.puck_{h2}.npy")
                    if os.path.exists(q): return q
        return p_
    def run(g, depth=0):
        import numpy as np
        todo = [k for k in g if not os.path.exists(cache_path(k))]
        for k in g:
            if k not in todo: out[k] = np.load(cache_path(k))
        if not todo: return
        style = HEAD_STYLE if any(k.startswith("h") for k in todo) else BATCH_STYLE
        _notes = letter_notes(" ".join(normalize(text[k]) for k in todo), limit=20)
        prompt = style + _notes + "\n\n" + "\n\n".join(f"{n+1}. {normalize(text[k])}" for n, k in enumerate(todo))
        try:
            a = _gemini_pcm(prompt) if len(todo) > 1 else _gemini_pcm((GEMINI_STYLE.rstrip()[:-5] if GEMINI_STYLE.rstrip().endswith("Text:") else GEMINI_STYLE) + letter_notes(normalize(text[todo[0]])) + " Text:\n" + normalize(text[todo[0]]))
            parts = split_on_pauses(a, len(todo), [len(normalize(text[k])) for k in todo]) if len(todo) > 1 else [a]
            for k, part in zip(todo, parts):
                np.save(cache_path(k), part); out[k] = part
            time.sleep(22)  # stay under the free per-minute limit
        except Exception as e:
            msg = str(e)
            print(f"  Google voice part ({len(todo)} clips) failed:", msg[:160], flush=True)
            if "per day" in msg.lower() or "PerDay" in msg or depth >= 2: raise
            time.sleep(25)
            if len(todo) == 1: return run(todo, depth + 1)
            half = (len(todo) + 1) // 2
            run(todo[:half], depth + 1); run(todo[half:], depth + 1)
    for g in groups:
        if g: run(g)
    for k in keys:
        raw = os.path.join(work, k + ".g24.wav"); _write24(out[k], raw); _post(raw, os.path.join(work, k + ".wav"))
    return "gemini"

def puck_cached(items, work):
    """{key: audio} for every clip of items already recorded in the Puck voice (any Puck model)."""
    import hashlib, numpy as np
    got = {}
    for k, t in items:
        for m in [GEMINI_MODEL] + GEMINI_MODELS:
            h = hashlib.md5((GEMINI_VOICE + m + normalize(t)).encode()).hexdigest()[:10]
            for nt in (normalize(t), normalize(t, spell=False)):   # also reuse clips recorded before numbers were spelled out
                h = hashlib.md5((GEMINI_VOICE + m + nt).encode()).hexdigest()[:10]
                q = os.path.join(work, f"{k}.puck_{h}.npy")
                if os.path.exists(q): break
            if os.path.exists(q):
                got[k] = np.load(q); break
    return got

def write_clip(audio, work, k):
    raw = os.path.join(work, k + ".g24.wav"); _write24(audio, raw); _post(raw, os.path.join(work, k + ".wav"))

def _espeak(text, wav):
    raw = wav[:-4] + ".raw.wav"
    subprocess.run(["espeak-ng", "-v", "kn", "-s", "135", "-p", "45", "-w", raw, normalize(text)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
                    "highpass=f=90,lowpass=f=7000,acompressor=threshold=-18dB:ratio=3,volume=1.4",
                    "-ar", "44100", "-ac", "1", wav], check=True)

def synth(text, wav, engine=os.environ.get("VN_TTS", "auto")):
    if engine == "gemini" and os.path.exists(GEMINI_KEYFILE):  # single clips: opt-in only (free tier ~10 requests/day)
        try:
            _gemini(text, wav); return "gemini"
        except Exception as e:
            if engine == "gemini": raise
            print("Gemini TTS unavailable, using Microsoft voice:", type(e).__name__, str(e)[:120])
    if engine in ("auto", "edge", "gemini"):
        try:
            _edge(text, wav); return "edge"
        except Exception as e:
            if engine == "edge": raise
            print("edge-tts unavailable, falling back to espeak-ng:", type(e).__name__)
    if not shutil.which("espeak-ng"):
        raise RuntimeError("No TTS engine: pip install edge-tts, or install espeak-ng")
    _espeak(text, wav); return "espeak"

if __name__ == "__main__":  # voice samples for comparison
    import json, sys, edge_tts
    cfg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "bulletin.json"))
    sample = cfg["intro"] + " " + cfg["stories"][0]["body"]
    os.makedirs("voice_samples", exist_ok=True)
    if os.path.exists(GEMINI_KEYFILE):
        log = open("voice_samples/google_log.txt", "w")
        for m in (GEMINI_MODEL, "gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"):
            GEMINI_MODEL = m; ok = 0
            for gv in ("Kore", "Aoede", "Charon", "Puck"):
                GEMINI_VOICE = gv
                try:
                    _gemini(sample, f"voice_samples/Google_{gv}.wav"); ok += 1
                    print("wrote", f"voice_samples/Google_{gv}.wav"); log.write(f"OK {m} {gv}\n")
                except Exception as e:
                    body = getattr(e, "read", lambda: b"")()[:600]
                    msg = f"FAIL {m} {gv}: {type(e).__name__} {e} {body!r}"
                    print(msg); log.write(msg + "\n"); log.flush()
                    if ok == 0: break
            if ok: break
        log.close()
    else:
        print("No Google key found at", GEMINI_KEYFILE)
    for v in ("kn-IN-SapnaNeural", "kn-IN-GaganNeural"):
        for r in ("+4%", "+10%"):
            out = f"voice_samples/{v.split('-')[2].replace('Neural', '')}_{r.replace('%', 'pct').replace('+', 'plus')}.mp3"
            try: asyncio.run(edge_tts.Communicate(normalize(sample), v, rate=r, pitch=PITCH).save(out))
            except Exception as e: print("edge fail", e); continue
            print("wrote", out)



def trim_signoff(clips, sr=24000):
    """Vijay, 27 Nov: the voice once added 'Vijay News noduttiri' at the end of story clips. Uses the outro's own
    recording of that line as a template; any other clip whose LAST ~2.5 s matches it is cut at the pause before it."""
    import numpy as np
    from scipy.signal import stft
    if "outro" not in clips: return []
    def mono(a):
        a = np.asarray(a, dtype=np.float32); return a if a.ndim == 1 else a.mean(1)
    def pauses(x):
        w = int(sr * 0.02); e = np.array([np.sqrt((x[i:i + w] ** 2).mean()) for i in range(0, len(x) - w, w)]); thr = e.max() * 0.05
        out = []; run = 0
        for i, v in enumerate(e < thr):
            if v: run += 1
            else:
                if run >= 8: out.append(((i - run) * 0.02, i * 0.02))
                run = 0
        return out
    o = mono(clips["outro"]); ps = [p for p in pauses(o) if p[0] > 0.5]
    if len(ps) < 2: return []
    a0, a1 = ps[-2][1], ps[-1][0]          # the line between the last two pauses = "Vijay News noduttiri"
    if not 0.6 < a1 - a0 < 2.5: return []
    n = 40; f = np.linspace(0, sr / 2, 257); m = lambda x: 2595 * np.log10(1 + x / 700); im = lambda y: 700 * (10 ** (y / 2595) - 1)
    pts = im(np.linspace(m(80), m(7600), n + 2)); FB = np.zeros((n, 257))
    for i in range(n):
        l, c, r = pts[i:i + 3]; FB[i] = np.clip(np.minimum((f - l) / (c - l), (r - f) / (r - c)), 0, None)
    def feat(x):
        _, _, Z = stft(x, sr, nperseg=512, noverlap=32); M = np.log(FB @ (np.abs(Z) ** 2) + 1e-6).T; M = M - M.mean(0)
        return M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    T = feat(o[int(a0 * sr):int(a1 * sr)]); fixed = []
    for k, a in list(clips.items()):
        if k == "outro" or not (k.startswith("s") or k.startswith("h")): continue
        x = mono(a); tail = x[-int(sr * 3.0):]
        if len(tail) < sr: continue
        C = 1 - T @ feat(tail).T; mm, nn = C.shape; D = np.full((mm, nn), np.inf); D[0] = C[0]
        for i in range(1, mm):
            p = D[i - 1]; b = np.minimum(p, np.concatenate([[np.inf], p[:-1]])); b = np.minimum(b, np.concatenate([[np.inf, np.inf], p[:-2]])); D[i] = C[i] + b
        if D[-1].min() / mm < 0.25:
            pz = [q for q in pauses(x) if q[1] < len(x) / sr - 0.6]
            if pz:
                cut = int((pz[-1][0] + 0.15) * sr); clips[k] = a[:cut]; fixed.append(k)
    return fixed
