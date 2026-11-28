"""Vijay News ENGLISH voice. Google Gemini TTS (only with its OWN key file ~/.vijaynews_en_gemini_key, so the
Kannada channel's free Puck quota is never used up) -> otherwise Microsoft neural Indian-English voice via edge-tts.
Usage: synth(text, out_wav).  Env: VN_VOICE (en-IN-PrabhatNeural | en-IN-NeerjaNeural), VN_RATE, VN_PITCH."""
import subprocess, shutil, os, asyncio, re
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

VOICE = os.environ.get("VN_VOICE", "en-IN-NeerjaExpressiveNeural")   # Vijay, 28 Nov: sample 3 (Neerja, expressive)
RATE = os.environ.get("VN_RATE", "+0%")   # Vijay, 27 Nov: natural human pace, not rushed
PITCH = os.environ.get("VN_PITCH", "+0Hz")

# spoken forms for a natural Indian English news reader (screen text unchanged)
SPOKEN = [
    (r"₹\s?([\d,.]+)\s?(lakh crore|crore|lakh|billion|million|trillion)?", lambda m: m.group(1) + " " + ((m.group(2) + " ") if m.group(2) else "") + "rupees"),
    (r"\bRs\.?\s?([\d,.]+)\s?(lakh crore|crore|lakh|billion|million)?", lambda m: m.group(1) + " " + ((m.group(2) + " ") if m.group(2) else "") + "rupees"),
    (r"\$\s?([\d,.]+)\s?(billion|million|trillion|bn|mn)?", lambda m: m.group(1) + " " + ({"bn": "billion", "mn": "million"}.get(m.group(2), m.group(2) or "") + " dollars").strip()),
    (r"\bDr\.\s", "Doctor "), (r"\bProf\.\s", "Professor "), (r"\bGovt\b", "government"), (r"\bvs\.?\s", "versus "),
    (r"\bkm/h\b", "kilometres per hour"), (r"(\d)\s?km\b", r"\1 kilometres"), (r"(\d)\s?bps\b", r"\1 basis points"),
    (r"\bCM\b", "Chief Minister"), (r"\bPM\b", "Prime Minister"), (r"\bISRO\b", "Isro"), (r"\bNASA\b", "Nasa"),
    (r"\bT20I?\b", "T-twenty"), (r"\bODI\b", "O D I"), (r"\bIST\b", "I S T"), (r"\s*[–—]\s*", ", "),
]
SAY_INSTEAD = {}

def normalize(text, spell=True):
    for pat, rep in SPOKEN:
        text = re.sub(pat, rep, text)
    text = text.replace(";", ".")
    return re.sub(r"\s+", " ", text).strip()

def _edge(text, wav):
    import edge_tts
    mp3 = wav[:-4] + ".mp3"
    # Microsoft's free voice service sometimes refuses one request ("NoAudioReceived") – retry with a pause
    import time
    for attempt in range(6):
        try:
            asyncio.run(edge_tts.Communicate(normalize(text), VOICE, rate=RATE, pitch=PITCH).save(mp3))
            if os.path.exists(mp3) and os.path.getsize(mp3) > 1000: break
            raise RuntimeError("empty audio")
        except Exception as e:
            if attempt == 5: raise
            print(f"  Microsoft voice retry {attempt + 1}: {type(e).__name__}", flush=True); time.sleep(5 * (attempt + 1))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3,
                    "-af", "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80,loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-ac", "1", wav], check=True)

# SEPARATE key for the English channel (a second free Google AI Studio key in its own Google Cloud project has its own
# free quota). Without it the English channel uses the Microsoft Indian-English voice and never touches the Kannada key.
GEMINI_KEYFILE = os.path.expanduser("~/.vijaynews_en_gemini_key")
# Vijay, 25 Nov 2026: "the news read for Rahul Gandhi section voice is good. Try retaining that for all."
# That clip was a single-story request on gemini-2.5-flash-preview-tts (Puck) -> make that the standard.
GEMINI_MODEL = os.environ.get("VN_GEMINI_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_VOICE = os.environ.get("VN_GEMINI_VOICE", "Puck")   # female: Kore, Aoede · male: Charon, Puck
# Vijay, 27 Nov: "India English tone, but a standard real one, near to normal human speaking or reading tone and pronunciations"
VOICE_BRIEF = ("a standard Indian English newsreader on a national English news channel: a natural, educated Indian English "
               "accent that is clear and neutral – never exaggerated, never American or British, never sing-song or robotic. "
               "Speak like a real person reading the news to the viewer: normal conversational pace, natural pauses and "
               "intonation, slight emphasis on the key fact, relaxed and confident. Indian names, places and words "
               "(crore, lakh, rupees, Lok Sabha) pronounced the way Indians say them; English words with standard pronunciation.")
GEMINI_STYLE = os.environ.get("VN_GEMINI_STYLE", "Read the following English news text exactly as written, as " + VOICE_BRIEF + " Text:")

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
    "You are " + VOICE_BRIEF + " Read the numbered English paragraphs below exactly as written: "
    "Do NOT read the paragraph numbers aloud. "
    "After each paragraph, stay completely silent for two full seconds before the next one.\n\n")
HEAD_STYLE = BATCH_STYLE.replace("Read the numbered English paragraphs below exactly as written: ",
    "Read the numbered English paragraphs below exactly as written. Most of them are short news HEADLINES: say each one "
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
        prompt = style + "\n\n".join(f"{n+1}. {normalize(text[k])}" for n, k in enumerate(todo))
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
    subprocess.run(["espeak-ng", "-v", "en", "-s", "135", "-p", "45", "-w", raw, normalize(text)], check=True)
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
    for v in ("en-IN-PrabhatNeural", "en-IN-NeerjaNeural"):
        for r in ("+4%", "+10%"):
            out = f"voice_samples/{v.split('-')[2].replace('Neural', '')}_{r.replace('%', 'pct').replace('+', 'plus')}.mp3"
            try: asyncio.run(edge_tts.Communicate(normalize(sample), v, rate=r, pitch=PITCH).save(out))
            except Exception as e: print("edge fail", e); continue
            print("wrote", out)
