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
SAY_INSTEAD = {}   # e.g. {"ಮತ್ತು": "ಹಾಗೂ"} – Vijay chose to keep ಮತ್ತು with the corrected pronunciation hint (25 Nov)

def normalize(text):
    for k, v in SAY_INSTEAD.items():
        text = re.sub(rf"(?<![{KN}]){k}(?![{KN}])", v, text)
    for k in sorted(SPOKEN, key=len, reverse=True):   # whole words only ("ಸಿಎಂ" but not inside "ಐಸಿಎಂಆರ್")
        text = re.sub(rf"(?<![{KN}]){re.escape(k)}", SPOKEN[k], text) if re.match(rf"[{KN}]", k) else text.replace(k, SPOKEN[k])
    for k, v in TITLES.items():   # "ಡಾ. ರಾಜೀವ್" -> "ಡಾಕ್ಟರ್ ರಾಜೀವ್"
        text = re.sub(rf"(?<![{KN}]){k}\.\s*", v + " ", text)
    for k, v in MONTHS.items():   # "ಡಿ.4" / "ಡಿ. 4" -> "ಡಿಸೆಂಬರ್ 4"
        text = re.sub(rf"(?<![{KN}]){k}\.\s*(?=\d)", v + " ", text)
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
    "Pronounce like a native Bengaluru/Mysuru Kannada anchor (no Hindi or Tamil accent): the Kannada ತ and ದ are DENTAL (tongue touching the back of the upper teeth: the soft Indian 'th' and 'dh' sounds) – never the hard English or retroflex 't'/'d' (ಟ/ಡ); only ಟ ಠ ಡ ಢ ಣ are retroflex. Example: ಪಂದ್ಯ (match) = 'pan-dhya' with a soft dental dh, never 'pan-Da'; ದೇಶ = 'dhesha'. ಮತ್ತು sounds like 'math-thu': light, quick and UNSTRESSED, it is just the word 'and'. Do not stress or force these dental syllables (ತ್ತ, ದ್ಯ, ತ್ಯ…) – keep them soft and even; same for ಮತ್ತೆ 'math-the', ಹತ್ತು 'hath-thu', ಎತ್ತು 'eth-thu'. Numbers too, all with soft dental th and even rhythm: ಹತ್ತೊಂಬತ್ತು 'hath-thom-bath-thu' (19), ತೊಂಬತ್ತು 'thom-bath-thu' (90), ಇಪ್ಪತ್ತು 'ip-path-thu' (20), ಮೂವತ್ತು 'moo-vath-thu' (30), ಎಂಬತ್ತು 'em-bath-thu' (80), ಎಪ್ಪತ್ತು 'ep-path-thu' (70), ಅರವತ್ತು 'a-ra-vath-thu' (60), ಐವತ್ತು 'ai-vath-thu' (50) – say each number smoothly as one word; ಳ and ಣ retroflex; every short final vowel clearly spoken. Text:")

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
    "Pronounce like a native Bengaluru/Mysuru Kannada anchor (no Hindi or Tamil accent): the Kannada ತ and ದ are DENTAL (tongue touching the back of the upper teeth: the soft Indian 'th' and 'dh' sounds) – never the hard English or retroflex 't'/'d' (ಟ/ಡ); only ಟ ಠ ಡ ಢ ಣ are retroflex. Example: ಪಂದ್ಯ (match) = 'pan-dhya' with a soft dental dh, never 'pan-Da'; ದೇಶ = 'dhesha'. ಮತ್ತು sounds like 'math-thu': light, quick and UNSTRESSED, it is just the word 'and'. Do not stress or force these dental syllables (ತ್ತ, ದ್ಯ, ತ್ಯ…) – keep them soft and even; same for ಮತ್ತೆ 'math-the', ಹತ್ತು 'hath-thu', ಎತ್ತು 'eth-thu'. Numbers too, all with soft dental th and even rhythm: ಹತ್ತೊಂಬತ್ತು 'hath-thom-bath-thu' (19), ತೊಂಬತ್ತು 'thom-bath-thu' (90), ಇಪ್ಪತ್ತು 'ip-path-thu' (20), ಮೂವತ್ತು 'moo-vath-thu' (30), ಎಂಬತ್ತು 'em-bath-thu' (80), ಎಪ್ಪತ್ತು 'ep-path-thu' (70), ಅರವತ್ತು 'a-ra-vath-thu' (60), ಐವತ್ತು 'ai-vath-thu' (50) – say each number smoothly as one word; ಳ and ಣ retroflex; every short final vowel clearly spoken. "
    "After each paragraph, stay completely silent for two full seconds before the next one.\n\n")

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
                h2 = hashlib.md5((GEMINI_VOICE + m + normalize(text[k])).encode()).hexdigest()[:10]
                q = os.path.join(work, f"{k}.puck_{h2}.npy")
                if os.path.exists(q): return q
        return p_
    def run(g, depth=0):
        import numpy as np
        todo = [k for k in g if not os.path.exists(cache_path(k))]
        for k in g:
            if k not in todo: out[k] = np.load(cache_path(k))
        if not todo: return
        prompt = BATCH_STYLE + "\n\n".join(f"{n+1}. {normalize(text[k])}" for n, k in enumerate(todo))
        try:
            a = _gemini_pcm(prompt) if len(todo) > 1 else _gemini_pcm(GEMINI_STYLE + "\n" + normalize(text[todo[0]]))
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
            q = os.path.join(work, f"{k}.puck_{h}.npy")
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
