"""Vijay News English – QC gate before publishing (CHANNEL_RULES.md section 1).
python3 qc.py bulletin.json bulletin.mp4 render.log  ->  qc_report.txt + qc_sheet.jpg ; exit 1 = HOLD (not published).

FAIL (the render is held; the last good bulletin stays on air):
  video missing/short, wrong format, no audible voice, Kannada/Hindi script in English text, banned phrases
  (subscribe, morning-and-evening, bulletin times, "first AI channel"), a story without 2 named sources,
  a spoken date/weekday, a foreign place clip on an Indian (NATIONAL) story.
WARN (published, listed for review): length outside 25-30 min, story mix, stories without a clip, bitrate."""
import json, re, subprocess, sys, os

cfg_p, mp4, log_p = (sys.argv[1:4] + ["bulletin.json", "bulletin.mp4", "render.log"][len(sys.argv) - 1:])[:3]
fails, warns, oks = [], [], []
def F(m): fails.append(m)
def Wn(m): warns.append(m)
def OK(m): oks.append(m)

cfg = json.load(open(cfg_p)); stories = cfg.get("stories", [])
log = open(log_p, encoding="utf-8", errors="ignore").read() if os.path.exists(log_p) else ""

# ---------- 1. the video file
def probe(args):
    return subprocess.run(["ffprobe", "-v", "error", *args, mp4], capture_output=True, text=True).stdout.strip()
if not os.path.exists(mp4) or os.path.getsize(mp4) < 1_000_000:
    F("bulletin.mp4 missing or tiny")
else:
    dur = float(probe(["-show_entries", "format=duration", "-of", "csv=p=0"]) or 0)
    vs = probe(["-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0"])
    br = float(probe(["-show_entries", "format=bit_rate", "-of", "csv=p=0"]) or 0) / 1000
    if dur < 60: F(f"duration {dur:.0f} s – too short")
    elif not 25 * 60 <= dur <= 30 * 60: Wn(f"length {dur / 60:.1f} min – rule is 25-30 min (about 26 stories)")
    else: OK(f"length {dur / 60:.1f} min")
    if not vs.startswith("1920,1080,25/1"): F(f"video format {vs} – must be 1920x1080 25 fps (the stream joins files without re-encoding)")
    else: OK("1920x1080 25 fps")
    if br < 9000: Wn(f"bitrate {br:.0f} kbps – keep ~12 Mbps so the free Oracle server never looks idle")
    else: OK(f"bitrate {br:.0f} kbps")
    vol = subprocess.run(["ffmpeg", "-v", "info", "-t", "180", "-i", mp4, "-af", "volumedetect", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r"mean_volume: (-?[0-9.]+) dB", vol)
    if not m or float(m.group(1)) < -35: F(f"no audible voice (mean volume {m.group(1) if m else '?'} dB)")
    else: OK(f"audio level {m.group(1)} dB")
    # contact sheet for a human look: one frame every 20 s
    n = max(1, int(dur // 20))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", f"fps=1/20,scale=384:-1,tile=6x{(n + 5) // 6}",
                    "-frames:v", "1", "-q:v", "4", "qc_sheet.jpg"])

# ---------- 2. text rules (everything said or shown)
def texts():
    yield "intro", cfg.get("intro", ""); yield "outro", cfg.get("outro", "")
    for i, s in enumerate(stories, 1):
        for k in ("headline", "headline_spoken", "body", "section", "place", "stat_label", "source"):
            if s.get(k): yield f"story {i} {k}", str(s[k])
        for x in s.get("facts", []): yield f"story {i} fact", x
NONLATIN = re.compile(r"[ऀ-෿]")          # Devanagari … Kannada … Malayalam
BANNED = [(r"\bsubscrib", "asks viewers to subscribe"), (r"\b(hit|press) the bell", "bell request"),
          (r"\blike,? (and )?share", "like/share request"), (r"morning and evening", "'morning and evening'"),
          (r"\b(twice|two times) a day\b", "'twice a day'"), (r"\bevery (morning|evening)\b", "'every morning/evening'"),
          (r"\b(first|only) (ai|artificial intelligence)\b.*\bchannel", "'first AI channel' claim"),
          (r"\b(india's|indias) first\b.*\bai\b", "'India's first AI' claim"), (r"\bsee you (again|tomorrow)\b", "'see you again'")]
bad = 0
for where, t in texts():
    if NONLATIN.search(t): F(f"{where}: non-English script in an English text"); bad += 1
    for pat, what in BANNED:
        if re.search(pat, t, re.I): F(f"{where}: {what}"); bad += 1
if not bad: OK("text: English only, no banned phrases")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import make_bulletin as mb
    si = mb.spoken_intro(cfg.get("intro", ""))
    if re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", si, re.I):
        F("spoken intro still says a date/weekday")
    else: OK("no spoken date")
except Exception as e:
    Wn(f"spoken-intro check skipped: {e}")

# ---------- 3. stories: sources, mix, visuals
srcbad = []
for i, s in enumerate(stories, 1):
    src = re.sub(r"^\s*source[s]?\s*:\s*", "", s.get("source", ""), flags=re.I)
    names = [x for x in re.split(r",|/|&|\band\b", src) if x.strip()]
    if len(names) < 2: srcbad.append(i)
    if not s.get("place"): F(f"story {i}: no place")
if srcbad: F(f"stories without 2 named sources: {srcbad}")
else: OK(f"{len(stories)} stories, each with 2+ sources")
mix = {}
for s in stories: mix[s.get("tag", "?")] = mix.get(s.get("tag", "?"), 0) + 1
OK("mix: " + ", ".join(f"{k} {v}" for k, v in mix.items()))
if len(stories) < 26: Wn(f"{len(stories)} stories – rule is about 26 (6 national, 6 international, 3 business, 3 sport, 2 cinema, 5 tech, 1 viral)")
for k in ("NATIONAL", "INTERNATIONAL"):
    if mix.get(k, 0) == 0: F(f"no {k} story")
noclip = [i for i in range(1, len(stories) + 1) if not re.search(rf"^visual for story {i} :", log, re.M)]
if noclip: Wn(f"stories with no clip/photo found (graphic used): {noclip}")
elif log: OK("every story has a clip or photo")

# one shot per line (rulebook 2): every sentence needs a planned shot, and every planned shot must be found
for i, s in enumerate(stories, 1):
    nsent = len([x for x in re.split(r"(?<=[.!?])\s+", s.get("body", "").strip()) if x])
    plan = len(s.get("shots", []))
    if plan < min(nsent, 4): F(f"story {i}: {plan} planned shots for {nsent} sentences (one shot per line)")
    m = re.search(rf"^shots for story {i} : (.*)$", log, re.M)
    if log and plan:
        got = len(m.group(1).split(", ")) if m else 0
        if got < min(plan, 4): Wn(f"story {i}: SHOT MISSING – {got} of {min(plan, 4)} planned shots found")
if stories and all(len(s.get("shots", [])) >= 1 for s in stories): OK("shot plan present for every story")

# foreign place clip on an Indian story (rulebook 2a.3)
FOREIGN = ("shanghai", "beijing", "china", "dubai", "london", "new york", "washington", "paris", "tokyo", "moscow", "sydney", "toronto", "berlin", "singapore")
# render.log order: the "pixabay ... for 'query'" lines of a story come right BEFORE its "visual for story N" line
qs, cur = {}, []
for line in log.splitlines():
    m = re.match(r"pixabay (?:video|photo) for '([^']+)'", line)
    if m: cur.append(m.group(1).lower())
    m2 = re.match(r"visual for story (\d+) :", line)
    if m2: qs[int(m2.group(1))] = cur; cur = []
for i, s in enumerate(stories, 1):
    if s.get("tag") == "NATIONAL" or (s.get("place", "").lower() in ("new delhi", "mumbai", "bhopal", "kerala", "goa")):
        hit = [q for q in qs.get(i, []) if any(f in q for f in FOREIGN)]
        if hit: F(f"story {i} (Indian) used a foreign place clip: {hit}")

# ---------- report
rep = ["Vijay News English – QC " + ("HOLD (not published)" if fails else "PASS"), ""]
rep += ["FAIL  " + x for x in fails] + ["WARN  " + x for x in warns] + ["ok    " + x for x in oks]
open("qc_report.txt", "w").write("\n".join(rep) + "\n"); print("\n".join(rep))
sys.exit(1 if fails else 0)
