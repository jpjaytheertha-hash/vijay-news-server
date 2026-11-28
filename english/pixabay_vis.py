"""Vijay News – free stock visuals from Pixabay (Pixabay Content License: free, no attribution required;
we still show "Pixabay" in the label). Vijay, 26 Nov 2026: "for each news bit we could use relevant images" /
"or short AI videos for each news bit and play it in loop until the script reading is done".

fetch(story, used, broll_dir) -> (path, kind) where kind is "video" or "photo", or (None, None).
Key: ~/.vijaynews_pixabay_key (typed by Vijay). Query: story["image_query"] (English, written by the bulletin
task) or keywords mapped from the English headline/body below.
"""
import json, os, re, subprocess, urllib.parse

KEYFILE = os.path.expanduser("~/.vijaynews_pixabay_key")
FAKE_TAGS = ("cartoon", "animation", "animated", "3d", "render", "illustration", "vector", "texture", "abstract", "background",
             "motion graphic", "particles", "loop", "icon", "clipart", "drawing", "emoji", "fractal", "digital art")
INDIA_TAGS = ("india", "indian", "bangalore", "bengaluru", "mumbai", "delhi", "kerala", "rajasthan", "kolkata", "chennai",
              "hyderabad", "mysore", "karnataka", "goa", "varanasi", "jaipur", "hindu", "rupee", "assam")

# English keyword in headline/body (lower case) -> Pixabay search words, most specific first
KW = [
    ("hockey", "field hockey"), ("cricket", "cricket match"), ("football", "football match"), ("kabaddi", "kabaddi"),
    ("badminton", "badminton"), ("tennis", "tennis"), ("chess", "chess"), ("olympic", "athletics stadium"),
    ("air force", "fighter jet"), ("fighter", "fighter jet"), ("airline", "airplane"), ("airport", "airport"), ("rocket", "rocket launch"),
    ("isro", "rocket launch"), ("satellite", "satellite space"), ("space", "space satellite"),
    ("sensex", "stock market"), ("nifty", "stock market"), ("shares", "stock market"), ("stock", "stock market"), ("gold price", "gold jewellery"),
    ("rupee", "indian rupee notes"), ("currency", "indian rupee notes"), ("loan", "indian bank branch"), ("atm", "indian atm"), ("inflation", "market vegetables"), ("gdp", "economy finance"), ("rbi", "indian bank branch"),
    ("port", "container port"), ("ship", "cargo ship"), ("railway", "train india"), ("train", "train india"), ("metro", "metro train"),
    ("traffic", "city traffic"), ("highway", "highway traffic"), ("tunnel", "tunnel road"),
    ("elephant", "elephants"), ("tiger", "tiger"), ("forest", "forest"), ("power", "power lines"), ("electricity", "power lines"),
    ("rain", "heavy rain"), ("flood", "flood water"), ("cyclone", "storm clouds"), ("storm", "storm clouds"), ("earthquake", "cracked ground"),
    ("heatwave", "hot sun"), ("pollution", "smog city"), ("smog", "smog city"), ("fog", "fog winter morning"), ("mining", "mining"),
    ("virus", "virus laboratory"), ("hospital", "hospital"), ("vaccine", "vaccine"), ("health", "healthcare"), ("doctor", "doctor stethoscope"),
    ("film festival", "film festival cinema"), ("box office", "movie theater"), ("film", "cinema"), ("ott", "streaming tv"),
    ("artificial intelligence", "artificial intelligence"), ("ai ", "artificial intelligence"), ("chatbot", "chatbot"),
    ("robot", "robot"), ("whatsapp", "smartphone chat"), ("google", "search engine laptop"), ("smartphone", "smartphone"),
    ("youtube", "video streaming"), ("instagram", "social media phone"), ("social media", "social media phone"), ("meta", "social media phone"),
    ("semiconductor", "computer chip"), ("chip", "computer chip"), ("data centre", "data center servers"), ("cyber", "cyber security"),
    ("electric vehicle", "electric car charging"), ("ev ", "electric car charging"), ("car", "car"), ("motorcycle", "motorcycle"),
    ("bank", "indian bank branch"), ("msme", "small business workshop"), ("startup", "startup team office"), ("it ", "software office"),
    ("jobs", "office workers"), ("election", "election voting"), ("vote", "election voting"), ("constitution", "constitution"),
    ("supreme court", "court justice"), ("court", "court justice"), ("police", "police"), ("school", "school classroom"),
    ("university", "university students"), ("farmer", "farmer field"), ("agriculture", "agriculture field"), ("water", "water"),
    ("budget", "money budget"), ("tariff", "trade containers"), ("trade", "trade"), ("oil", "oil refinery"), ("drone", "drone"),
    ("army", "army"), ("military", "army"), ("war", "army"), ("summit", "handshake flags"), ("agreement", "handshake agreement"),
    ("deal", "handshake agreement"), ("parliament", "parliament building"), ("lok sabha", "parliament building"),
]
# Vijay, 27 Nov: "when it is india related bank news show indian related banks, currencies etc not dollar or other
# country essence" – clips for Indian stories must never show foreign money, flags or cities.
FOREIGN_TAGS = ("dollar", "dollars", "usd", "euro", "pound sterling", "british pound", "yen", "yuan", "renminbi", "won",
                "american flag", "us flag", "usa flag", "united states", "america", "wall street", "new york", "manhattan",
                "london", "british", "england", "chinese", "china", "japan", "japanese", "europe", "european", "germany",
                "france", "canada", "australia", "dubai", "saudi", "russia", "brazil", "mexico", "bitcoin", "crypto")
INDIA_WORDS = ("india", "indian", "bhopal", "lucknow", "ahmedabad", "patna", "chandigarh", "amritsar", "srinagar", "kochi",
               "guwahati", "agra", "udaipur", "bhubaneswar", "jaipur", "varanasi", "mizoram", "nagaland", "manipur", "meghalaya", "delhi", "mumbai", "bengaluru", "bangalore", "chennai", "kolkata", "hyderabad", "pune",
               "kerala", "karnataka", "tamil nadu", "maharashtra", "gujarat", "punjab", "bihar", "uttar pradesh", "rajasthan",
               "assam", "odisha", "telangana", "andhra", "goa", "jammu", "kashmir", "rbi", "sebi", "isro", "rupee", "lok sabha",
               "rajya sabha", "sensex", "nifty", "bcci", "iit", "aiims", "infosys", "tcs", "wipro", "reliance", "tata", "adani", "hdfc", "sbi", "ಕರ್ನಾಟಕ", "ಬೆಂಗಳೂರು", "ಭಾರತ")
def is_india(s):
    """True when the story is about India (all NATIONAL stories, and any other story whose place/headline is Indian)."""
    if s.get("tag") in ("NATIONAL", "ರಾಜ್ಯ", "ರಾಷ್ಟ್ರೀಯ"): return True
    if s.get("tag") in ("INTERNATIONAL", "ಅಂತರರಾಷ್ಟ್ರೀಯ"): return False
    t = (s.get("place", "") + " " + s.get("headline", "")).lower()
    return any(w in t for w in INDIA_WORDS)

TAG_DEFAULT = {"NATIONAL": "india", "INTERNATIONAL": "world globe", "BUSINESS": "stock market", "SPORTS": "sports stadium",
               "CINEMA": "cinema film", "TECH": "technology", "SCIENCE": "science laboratory"}


# the clip's tags MUST contain one of these words (Vijay, 26 Nov: hockey story showed football)
REQUIRE = {"field hockey": ["hockey"], "football match": ["football", "soccer"], "cricket match": ["cricket"],
           "kabaddi": ["kabaddi"], "badminton": ["badminton"], "tennis": ["tennis"], "chess": ["chess"],
           "fighter jet": ["jet", "aircraft", "airplane", "plane", "air show"], "elephants": ["elephant"], "tiger": ["tiger"]}
EXCLUDE = {"indian bank branch": ["river", "bank of", "shore"], "field hockey": ["ice", "puck", "soccer", "football"], "football match": ["american football", "rugby"], "cricket match": ["insect"], "fighter jet": ["toy"]}
STOP = {"and", "the", "of", "a", "in", "city", "match", "india", "indian", "players", "training", "field", "stock", "footage", "video", "clip", "news"}


def _fits(q, tags):
    """The clip's own tags must contain a main word of the query, and none of the excluded words."""
    t = (tags or "").lower()
    if any(x in t for x in EXCLUDE.get(q, [])): return False
    base = q[7:] if q.startswith("indian ") else q
    if base in REQUIRE: return any(x in t for x in REQUIRE[base]) and not any(x in t for x in EXCLUDE.get(base, []))
    # Vijay, 27 Nov: hockey story showed tennis – a sport named in the search MUST be in the clip's tags,
    # and a clip tagged with a different sport is rejected
    SPORTS = ["hockey", "cricket", "football", "soccer", "tennis", "badminton", "kabaddi", "chess", "basketball",
              "volleyball", "baseball", "golf", "rugby", "athletics", "wrestling", "boxing"]
    ql = base.lower(); want = [sp for sp in SPORTS if sp in ql]
    if want:
        if not any(sp in t for sp in want): return False
        if any(sp in t for sp in SPORTS if sp not in want and not (sp == "soccer" and "football" in want)): return False
        if "hockey" in want and "ice" not in ql and any(x in t for x in ("ice", "puck", "skate", "rink")): return False   # Indian hockey = field hockey
    words = [w for w in ql.split() if w not in STOP]
    return not words or any(w.rstrip('s')[:6] in t for w in words)


def queries(s):
    out = []
    for q in list(s.get("image_queries") or [])[:1] + [s.get("image_query")]:
        if q and q not in out: out.append(q)
    text = (s.get("headline", "") + " " + s.get("body", "")).lower() + " "
    hits = sorted(((text.find(k), v) for k, v in KW if k in text), key=lambda x: x[0])
    for _, v in hits[:2]:
        if v not in out: out.append(v)
    out.append(TAG_DEFAULT.get(s.get("tag", ""), "news"))
    return out


def _get(url):
    r = subprocess.run(["curl", "-sSfL", "-m", "30", url], capture_output=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout else {}


def _download(url, dest):
    if os.path.exists(dest): return True
    r = subprocess.run(["curl", "-sSfL", "-m", "120", "-o", dest + ".part", url])
    if r.returncode == 0 and os.path.exists(dest + ".part") and os.path.getsize(dest + ".part") > 20000:
        os.replace(dest + ".part", dest); return True
    try: os.remove(dest + ".part")
    except OSError: pass
    return False


def fetch(s, used, broll_dir, want_video=True, photos=True, qlist=None, need=None):
    """Order (Vijay, 27 Nov: videos, Indian where the story is Indian): Indian video -> general video ->
    Indian photo -> general photo. Returns (path, "video"|"photo") or (None, None)."""
    if not os.path.exists(KEYFILE): return None, None
    key = open(KEYFILE).read().strip()
    os.makedirs(broll_dir, exist_ok=True)
    qs = _indian_first(s, qlist or queries(s)); india = is_india(s)
    def ok(q, h):
        t = (h.get("tags") or "").lower()
        if not _fits(q, t): return False
        if need and not any(x in t for x in need): return False
        if q.startswith("indian ") and not any(x in t for x in INDIA_TAGS): return False
        if india and any(x in t for x in FOREIGN_TAGS): return False   # no dollars, foreign flags or cities for Indian news
        return True
    if india and not need and os.environ.get("VN_INDIA_STRICT", "1") == "1":
        # Vijay, 27 Nov: Indian stories must LOOK Indian – try Indian-tagged clips first, then an Indian-tagged
        # PHOTO (slow zoom) – only then a general clip. A real rupee photo beats an unrelated animation.
        r = fetch(s, used, broll_dir, want_video=want_video, photos=photos, qlist=qlist, need=INDIA_TAGS)
        if r[0]: return r
    if want_video:
        for q in qs:
            d = _get(f"https://pixabay.com/api/videos/?key={key}&q={urllib.parse.quote(q)}&safesearch=true&per_page=15&order=popular")
            for h in d.get("hits", []):
                vid = "pxv_%s" % h.get("id")
                if vid in used or h.get("duration", 0) < 5 or not ok(q, h): continue
                # Vijay, 27 Nov: "very relevant and near to real" – real camera footage only, no cartoons/animations/textures
                if h.get("type", "film") != "film" or any(x in (h.get("tags") or "").lower() for x in FAKE_TAGS): continue
                v = h.get("videos", {})   # clips play full screen – take the HD (medium, ~1920x1080) file
                hd = v.get("medium") if (v.get("medium") or {}).get("width", 0) <= 1920 else None
                u = (hd or v.get("small") or v.get("tiny") or {}).get("url")
                if not u: continue
                dest = os.path.join(broll_dir, vid + ("_hd" if hd else "") + ".mp4")
                if _download(u, dest):
                    used.add(vid); print(f"pixabay video for '{q}': {vid}", flush=True); return dest, "video"
    if photos:
        for q in qs:
            d = _get(f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(q)}&image_type=photo&orientation=horizontal&safesearch=true&per_page=15&order=popular")
            for h in d.get("hits", []):
                pid = "pxp_%s" % h.get("id")
                if pid in used or not ok(q, h) or any(x in (h.get("tags") or "").lower() for x in FAKE_TAGS): continue
                u = h.get("largeImageURL") or h.get("webformatURL")
                if not u: continue
                dest = os.path.join(broll_dir, pid + ".jpg")
                if _download(u, dest):
                    used.add(pid); print(f"pixabay photo for '{q}': {pid}", flush=True); return dest, "photo"
    return None, None


def still_from_video(path):
    """A still frame (for the vertical Shorts, which use pictures)."""
    out = path[:-4] + "_still.jpg"
    if not os.path.exists(out):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", path, "-frames:v", "1", "-q:v", "3", out])
    return out if os.path.exists(out) else None


# Vijay, 27 Nov: "for mentioning ASSAM or BENGALURU ... show one signage video clip or place's landmark", and
# "show 2-3 short clips for one story" (e.g. USA rain: rain, a US landmark, vehicles stuck in rain).
# English place word -> (search, tag words the clip MUST have, so we never show the wrong city)
PLACES = [
    ("bengaluru", "bangalore city", ["bangalore", "bengaluru"]), ("bangalore", "bangalore city", ["bangalore", "bengaluru"]),
    ("mysuru", "mysore palace", ["mysore", "mysuru"]), ("karnataka", "karnataka", ["karnataka", "hampi", "mysore", "bangalore"]),
    ("new delhi", "india gate delhi", ["delhi", "india gate"]), ("delhi", "india gate delhi", ["delhi", "india gate"]),
    ("mumbai", "mumbai city", ["mumbai"]), ("chennai", "chennai", ["chennai"]), ("hyderabad", "hyderabad charminar", ["hyderabad", "charminar"]),
    ("kolkata", "kolkata howrah bridge", ["kolkata", "howrah"]), ("assam", "assam tea garden", ["assam"]), ("kerala", "kerala backwaters", ["kerala"]),
    ("goa", "goa beach", ["goa"]), ("tamil nadu", "tamil nadu temple", ["tamil", "chennai", "madurai"]), ("varanasi", "varanasi ghats", ["varanasi"]),
    ("jaipur", "jaipur", ["jaipur"]), ("rajasthan", "rajasthan", ["rajasthan", "jaipur"]),
    ("bhopal", "bhopal city", ["bhopal"]), ("lucknow", "lucknow", ["lucknow"]), ("ahmedabad", "ahmedabad", ["ahmedabad"]),
    ("pune", "pune city", ["pune"]), ("patna", "patna", ["patna"]), ("chandigarh", "chandigarh", ["chandigarh"]),
    ("amritsar", "amritsar golden temple", ["amritsar", "golden temple"]), ("srinagar", "srinagar dal lake", ["srinagar", "dal lake"]),
    ("kochi", "kochi kerala", ["kochi", "kerala"]), ("guwahati", "guwahati", ["guwahati", "assam"]), ("agra", "taj mahal agra", ["taj mahal", "agra"]),
    ("udaipur", "udaipur", ["udaipur"]), ("bhubaneswar", "odisha temple", ["odisha", "bhubaneswar", "konark"]),
    ("washington", "washington capitol", ["washington", "capitol"]), ("new york", "new york city", ["new york", "manhattan"]),
    ("united states", "new york city skyline", ["new york", "manhattan", "usa", "america"]), ("us ", "new york city skyline", ["new york", "manhattan", "usa", "america"]),
    ("london", "london big ben", ["london"]), ("britain", "london big ben", ["london"]), ("uk ", "london big ben", ["london"]),
    ("paris", "paris eiffel tower", ["paris", "eiffel"]), ("france", "paris eiffel tower", ["paris", "eiffel"]),
    ("japan", "tokyo city", ["tokyo", "japan"]), ("china", "shanghai city", ["china", "shanghai", "beijing"]),
    ("dubai", "dubai skyline", ["dubai"]), ("uae", "dubai skyline", ["dubai", "abu dhabi"]), ("singapore", "singapore skyline", ["singapore"]),
    ("australia", "sydney opera house", ["sydney", "australia"]), ("indonesia", "indonesia", ["indonesia", "jakarta", "bali"]),
    ("germany", "berlin city", ["berlin", "germany"]), ("canada", "toronto city", ["toronto", "canada"]), ("russia", "moscow kremlin", ["moscow", "kremlin", "russia"]),
]


def place_clip(s, used, broll_dir):
    """A landmark / skyline clip of the story's place (s["place_query"] from the bulletin writer wins)."""
    if s.get("place_query"):
        GENERIC = {"city", "skyline", "street", "palace", "garden", "tea", "gate", "opera", "house", "sign", "beach",
                   "tower", "bridge", "temple", "building", "aerial", "view", "night", "the", "of", "big", "marine", "drive"}
        need = [w for w in s["place_query"].lower().split() if w not in GENERIC][:1]   # the place's own name must be in the clip's tags
        return fetch(s, used, broll_dir, photos=False, qlist=[s["place_query"]], need=need or None)[0]
    # Vijay, 28 Nov: the story's PLACE decides (an India-vs-China match in Bhopal must not get Shanghai);
    # the headline is only read when the place is empty or not an Indian place.
    place = (s.get("place", "") or "").lower() + " "
    for k, q, need in PLACES:
        if k in place:
            return fetch(s, used, broll_dir, photos=False, qlist=[q], need=need)[0]
    if place.strip() and is_india({"place": place}): return None
    if place.strip() and not s.get("tag") in ("INTERNATIONAL", "WORLD"): return None
    txt = (place + " " + s.get("headline", "")).lower() + " "
    for k, q, need in PLACES:
        if k in txt:
            return fetch(s, used, broll_dir, photos=False, qlist=[q], need=need)[0]
    return None


def extra_clips(s, used, broll_dir, first_path, n=3):
    """Up to n clips for one story: [topic clip, place landmark clip, second topic clip]."""
    clips = [first_path]
    try:
        pc = place_clip(s, used, broll_dir)
        if pc: clips.append(pc)
    except Exception as e: print("place clip skipped:", e, flush=True)
    if len(clips) < n:
        qs = list(s.get("image_queries") or [])[1:] + queries(s)
        try:
            p2, k2 = fetch(s, used, broll_dir, photos=False, qlist=qs)
            if p2: clips.append(p2)
        except Exception as e: print("second clip skipped:", e, flush=True)
    return clips[:n]


def _indian_first(s, qs):
    """Vijay, 27 Nov: Indian stories must look Indian ("Indian bank videos, very relevant and near to real") –
    for Karnataka/India stories try an Indian version of every search first, then the plain one."""
    if not is_india(s): return qs
    out = []
    for q in qs:
        if q and not any(w in q.lower() for w in ("india", "bangalore", "bengaluru", "mysore", "karnataka", "kerala", "delhi", "mumbai", "assam")):
            out.append("indian " + q)
        out.append(q)
    return out
