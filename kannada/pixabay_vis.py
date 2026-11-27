"""Vijay News – free stock visuals from Pixabay (Pixabay Content License: free, no attribution required;
we still show "Pixabay" in the label). Vijay, 26 Nov 2026: "for each news bit we could use relevant images" /
"or short AI videos for each news bit and play it in loop until the script reading is done".

fetch(story, used, broll_dir) -> (path, kind) where kind is "video" or "photo", or (None, None).
Key: ~/.vijaynews_pixabay_key (typed by Vijay). Query: story["image_query"] (English, written by the bulletin
task) or keywords mapped from the Kannada headline/body below.
"""
import json, os, re, subprocess, urllib.parse

KEYFILE = os.path.expanduser("~/.vijaynews_pixabay_key")
FAKE_TAGS = ("cartoon", "animation", "animated", "3d", "render", "illustration", "vector", "texture", "abstract", "background",
             "motion graphic", "particles", "loop", "icon", "clipart", "drawing", "emoji", "fractal", "digital art")
INDIA_TAGS = ("india", "indian", "bangalore", "bengaluru", "mumbai", "delhi", "kerala", "rajasthan", "kolkata", "chennai",
              "hyderabad", "mysore", "karnataka", "goa", "varanasi", "jaipur", "hindu", "rupee", "assam")

# Kannada word (stem) -> English search words, most specific first
KW = [
    ("ಹಾಕಿ", "field hockey"), ("ಕ್ರಿಕೆಟ್", "cricket match"), ("ಫುಟ್ಬಾಲ್", "football match"), ("ಕಬಡ್ಡಿ", "kabaddi"),
    ("ಬ್ಯಾಡ್ಮಿಂಟನ್", "badminton"), ("ಟೆನಿಸ್", "tennis"), ("ಚೆಸ್", "chess"), ("ಒಲಿಂಪಿಕ್", "athletics stadium"),
    ("ವೈಮಾನಿಕ", "fighter jet"), ("ಏರೋ ಇಂಡಿಯಾ", "fighter jet"), ("ವಿಮಾನ", "airplane"), ("ರಾಕೆಟ್", "rocket launch"),
    ("ಇಸ್ರೋ", "rocket launch"), ("ಉಪಗ್ರಹ", "satellite space"), ("ಬಾಹ್ಯಾಕಾಶ", "space satellite"),
    ("ಸೆನ್ಸೆಕ್ಸ್", "stock market"), ("ನಿಫ್ಟಿ", "stock market"), ("ಷೇರು", "stock market"), ("ಚಿನ್ನದ ಬೆಲೆ", "gold jewellery"),
    ("ಬಂದರು", "container port"), ("ಹಡಗು", "cargo ship"), ("ರೈಲು", "train india"), ("ಮೆಟ್ರೋ", "metro train"),
    ("ಸಂಚಾರ", "city traffic"), ("ಟ್ರಾಫಿಕ್", "city traffic"), ("ರಸ್ತೆ", "road traffic"), ("ಸುರಂಗ", "tunnel road"),
    ("ಆನೆ", "elephants"), ("ಹುಲಿ", "tiger"), ("ಅರಣ್ಯ", "forest"), ("ವಿದ್ಯುತ್", "power lines"),
    ("ಮಳೆ", "heavy rain"), ("ಪ್ರವಾಹ", "flood water"), ("ಚಂಡಮಾರುತ", "storm clouds"), ("ಭೂಕಂಪ", "cracked ground"),
    ("ಬಿಸಿಲು", "hot sun"), ("ಚಳಿ", "fog winter morning"), ("ತಾಪಮಾನ", "thermometer weather"), ("ಗಣಿ", "mining"),
    ("ಎಬೋಲಾ", "virus laboratory"), ("ಸೋಂಕು", "virus laboratory"), ("ಆಸ್ಪತ್ರೆ", "hospital"), ("ಲಸಿಕೆ", "vaccine"),
    ("ಆರೋಗ್ಯ", "healthcare"), ("ವೈದ್ಯ", "doctor stethoscope"),
    ("ಚಲನಚಿತ್ರೋತ್ಸವ", "film festival cinema"), ("ಸಿನಿಮಾ", "cinema"), ("ಚಿತ್ರಮಂದಿರ", "movie theater"), ("ಒಟಿಟಿ", "streaming tv"),
    ("ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ", "artificial intelligence"), ("ಎಐ", "artificial intelligence"), ("ಚಾಟ್‌ಬಾಟ್", "chatbot"),
    ("ರೋಬೋ", "robot"), ("ವಾಟ್ಸ್‌ಆ್ಯಪ್", "smartphone chat"), ("ಸಂದೇಶ", "smartphone message"), ("ಗೂಗಲ್", "search engine laptop"),
    ("ಯೂಟ್ಯೂಬ್", "video streaming"), ("ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್", "social media phone"), ("ಸಾಮಾಜಿಕ ಜಾಲತಾಣ", "social media phone"),
    ("ವಿದ್ಯುತ್ ಚಾಲಿತ", "electric car charging"), ("ಇವಿ", "electric car charging"), ("ಕಾರು", "car"), ("ಬೈಕ್", "motorcycle"),
    ("ಬ್ಯಾಂಕ್", "indian bank branch"), ("ಎಂಎಸ್‌ಎಂಇ", "small business workshop"), ("ಸಣ್ಣ ಉದ್ದಿಮೆ", "small business workshop"), ("ಉದ್ದಿಮೆ", "small scale industry"),
    ("ಸ್ಟಾರ್ಟ್‌ಅಪ್", "startup team office"), ("ಐಟಿ", "software office"), ("ಉದ್ಯೋಗ", "office workers"), ("ಆಟಿಕೆ", "toys"),
    ("ಜಾಹೀರಾತು", "billboards city"), ("ಚುನಾವಣೆ", "election voting"), ("ಮತದಾನ", "election voting"), ("ಸಂವಿಧಾನ", "constitution"),
    ("ನ್ಯಾಯಾಲಯ", "court justice"), ("ಪೊಲೀಸ್", "police"), ("ಶಾಲೆ", "school classroom"), ("ಕಾಲೇಜು", "university students"),
    ("ರೈತ", "farmer field"), ("ಕೃಷಿ", "agriculture field"), ("ನೀರು", "water"), ("ಕೆರೆ", "lake"), ("ಬಜೆಟ್", "money budget"),
    ("ಸುಂಕ", "trade containers"), ("ವ್ಯಾಪಾರ", "trade"), ("ತೈಲ", "oil refinery"), ("ಡ್ರೋನ್", "drone"), ("ಸೇನೆ", "army"),
    ("ಭದ್ರತಾ ಒಪ್ಪಂದ", "handshake flags"), ("ಒಪ್ಪಂದ", "handshake agreement"), ("ಸಂಸತ್", "parliament building"),
]
TAG_DEFAULT = {"ರಾಜ್ಯ": "bangalore city", "ರಾಷ್ಟ್ರೀಯ": "india", "ಅಂತರರಾಷ್ಟ್ರೀಯ": "world globe", "ಕ್ರೀಡೆ": "sports stadium",
               "ಸಿನಿಮಾ": "cinema film", "ಟೆಕ್": "technology"}


# the clip's tags MUST contain one of these words (Vijay, 26 Nov: hockey story showed football)
REQUIRE = {"field hockey": ["hockey"], "football match": ["football", "soccer"], "cricket match": ["cricket"],
           "kabaddi": ["kabaddi"], "badminton": ["badminton"], "tennis": ["tennis"], "chess": ["chess"],
           "fighter jet": ["jet", "aircraft", "airplane", "plane", "air show"], "elephants": ["elephant"], "tiger": ["tiger"]}
EXCLUDE = {"indian bank branch": ["river", "bank of", "shore"], "field hockey": ["ice", "puck", "soccer", "football"], "football match": ["american football", "rugby"], "cricket match": ["insect"], "fighter jet": ["toy"]}
STOP = {"and", "the", "of", "a", "in", "city", "match", "using", "with", "people", "india", "indian", "players", "training", "field"}


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
    # Vijay, 27 Nov: ASHA strike headline showed a factory worker and a market street – topic words in the search
    # now REQUIRE matching tags on the clip (health worker -> medical tags, protest -> protest tags, women -> woman tags)
    topical = False
    # health/medical searches must never get gym or fitness footage (ASHA story got a women's workout clip)
    if any(w in ql for w in ("health", "nurse", "medical", "hospital", "asha")) and \
       any(x in t for x in ("fitness", "gym", "workout", "exercise", "yoga", "aerobic", "training", "sport", "beauty", "spa")): return False
    for qwords, need in TOPIC_NEED:
        if any(w in ql for w in qwords):
            if not any(n in t for n in need): return False
            topical = True
    if topical: return True
    words = [w for w in ql.split() if w not in STOP]
    # Vijay, 27 Nov: one loose word was enough (fish for "small business workshop", paper for "parliament meeting hall")
    # -> at least two of the query's main words must be in the clip's tags (one, for one-word queries)
    hits = sum(w.rstrip('s')[:6] in t for w in words)
    return not words or hits >= min(2, len(words))


TOPIC_NEED = [
    (("health worker", "nurse", "healthcare", "hospital", "doctor", "medical", "asha", "anganwadi", "vaccin"),
     ("nurse", "medical", "doctor", "hospital", "clinic", "vaccin", "patient", "medicine", "healthcare", "stethoscope", "ambulance")),
    (("protest", "strike", "rally", "dharna", "agitation", "demonstration"),
     ("protest", "strike", "demonstrat", "activis", "slogan", "placard", "banner")),
    (("women", "woman"), ("woman", "women", "female", "girl", "lady", "ladies", "mother")),
    (("farmer",), ("farmer", "farm", "agricultur", "field", "crop", "village")),
    (("school", "student", "classroom"), ("school", "student", "class", "children", "education", "study")),
]


def queries(s):
    out = []
    for q in list(s.get("image_queries") or [])[:1] + [s.get("image_query")]:
        if q and q not in out: out.append(q)
    text = s.get("headline", "") + " " + s.get("body", "")
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


# Vijay, 27 Nov: "mahila hockey shows football video" – no hockey clip matched, so a generic "sports stadium"
# fallback was used. Now a sports story is LOCKED to its sport: every clip (all queries, fallbacks, photos)
# must carry that sport's tag and no other sport's; fallbacks are sport-specific; women's sport tries women first.
SPORT_KN = [("ಹಾಕಿ", "hockey", ["field hockey", "hockey stick ball", "hockey"]),
            ("ಕ್ರಿಕೆಟ್", "cricket", ["cricket match", "cricket bat ball", "cricket"]),
            ("ಫುಟ್ಬಾಲ್", "football", ["football match", "soccer ball", "football"]),
            ("ಕಬಡ್ಡಿ", "kabaddi", ["kabaddi", "kabaddi india"]),
            ("ಬ್ಯಾಡ್ಮಿಂಟನ್", "badminton", ["badminton match", "badminton shuttlecock", "badminton"]),
            ("ಟೆನಿಸ್", "tennis", ["tennis match", "tennis ball racket", "tennis"]),
            ("ಚೆಸ್", "chess", ["chess game", "chess board", "chess"]),
            ("ಚದುರಂಗ", "chess", ["chess game", "chess board", "chess"]),
            ("ಬಾಸ್ಕೆಟ್‌ಬಾಲ್", "basketball", ["basketball game", "basketball"]),
            ("ವಾಲಿಬಾಲ್", "volleyball", ["volleyball match", "volleyball"]),
            ("ಕುಸ್ತಿ", "wrestling", ["wrestling match", "wrestling"]),
            ("ಬಾಕ್ಸಿಂಗ್", "boxing", ["boxing match", "boxing"]),
            ("ಗಾಲ್ಫ್", "golf", ["golf course", "golf"])]
ALL_SPORTS = ["hockey", "cricket", "football", "soccer", "tennis", "badminton", "kabaddi", "chess", "basketball",
              "volleyball", "baseball", "golf", "rugby", "wrestling", "boxing", "table tennis", "skating", "swimming"]


def story_sport(s):
    """(sport, fallback queries) of a sports story, else (None, [])."""
    text = s.get("headline", "") + " " + (s.get("headline_spoken") or "") + " " + s.get("body", "")
    qtxt = " ".join([s.get("image_query") or ""] + list(s.get("image_queries") or [])).lower()
    hits = sorted((text.find(k), sp, fb) for k, sp, fb in SPORT_KN if k in text)
    if hits: return hits[0][1], hits[0][2]
    for k, sp, fb in SPORT_KN:
        if sp in qtxt: return sp, fb
    return None, []


def _sport_ok(sport, t):
    if sport == "football": mine = ("football", "soccer")
    else: mine = (sport,)
    if not any(x in t for x in mine): return False
    others = [o for o in ALL_SPORTS if o not in mine and not (sport == "tennis" and o == "table tennis")]
    if sport == "tennis" and "table tennis" in t: return False
    if any(o in t for o in others): return False
    if sport == "hockey" and any(x in t for x in ("ice", "puck", "skate", "rink")): return False
    return True


def fetch(s, used, broll_dir, want_video=True, photos=True, qlist=None, need=None):
    """Order (Vijay, 27 Nov: videos, Indian where the story is Indian): Indian video -> general video ->
    Indian photo -> general photo. Returns (path, "video"|"photo") or (None, None)."""
    if not os.path.exists(KEYFILE): return None, None
    key = open(KEYFILE).read().strip()
    os.makedirs(broll_dir, exist_ok=True)
    qs = _indian_first(s, qlist or queries(s))
    sport, sfb = (None, []) if need else story_sport(s)   # place/landmark clips (need=…) are not sport-locked
    if sport:
        women = "ಮಹಿಳಾ" in (s.get("headline", "") + s.get("body", "")) or "women" in " ".join(qs).lower()
        extra = (["women " + sfb[0]] if women else []) + sfb
        qs = [q for q in qs if sport in q.lower() or (sport == "football" and "soccer" in q.lower())]
        qs = list(dict.fromkeys(([q if q.startswith("indian ") else "indian " + q for q in qs] if is_indian(s) else []) + qs + extra))
    def ok(q, h):
        t = (h.get("tags") or "").lower()
        if sport and not _sport_ok(sport, t): return False
        if not _fits(q, t): return False
        if need and not any(x in t for x in need): return False
        if q.startswith("indian ") and not any(x in t for x in INDIA_TAGS): return False
        if is_indian(s) and not s.get("place_query_active") and any(x in t for x in FOREIGN_TAGS): return False   # no dollars/US flags in Indian news
        return True
    def _pass(qs, want_video, photos):
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
    # Vijay, 27 Nov: bank-holiday story showed a city street + a Nokia building – a generic fallback VIDEO used to win
    # over a real topic PHOTO. Order now: topic videos -> topic photos -> generic (section/city) videos -> photos.
    generic = set(TAG_DEFAULT.values()) | {"indian " + v for v in TAG_DEFAULT.values()}
    topic = [q for q in qs if q not in generic]; gen = [q for q in qs if q in generic]
    for part in ([topic, gen] if topic and gen else [qs]):
        r_ = _pass(part, want_video, photos)
        if r_[0]: return r_
    return None, None


def still_from_video(path):
    """A still frame (for the vertical Shorts, which use pictures)."""
    out = path[:-4] + "_still.jpg"
    if not os.path.exists(out):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", path, "-frames:v", "1", "-q:v", "3", out])
    return out if os.path.exists(out) else None


# Vijay, 27 Nov: "for mentioning ASSAM or BENGALURU ... show one signage video clip or place's landmark", and
# "show 2-3 short clips for one story" (e.g. USA rain: rain, a US landmark, vehicles stuck in rain).
# Kannada place word -> (English search, tag words the clip MUST have, so we never show the wrong city)
PLACES = [
    ("ಬೆಂಗಳೂರು", "bangalore city", ["bangalore", "bengaluru"]), ("ಮೈಸೂರು", "mysore palace", ["mysore", "mysuru"]),
    ("ಮಂಗಳೂರು", "mangalore", ["mangalore"]), ("ಹಂಪಿ", "hampi", ["hampi"]), ("ಕರ್ನಾಟಕ", "karnataka", ["karnataka", "hampi", "mysore", "bangalore"]),
    ("ನವದೆಹಲಿ", "india gate delhi", ["delhi", "india gate"]), ("ದೆಹಲಿ", "india gate delhi", ["delhi", "india gate"]),
    ("ಮುಂಬೈ", "mumbai city", ["mumbai"]), ("ಚೆನ್ನೈ", "chennai", ["chennai"]), ("ಹೈದರಾಬಾದ್", "hyderabad charminar", ["hyderabad", "charminar"]),
    ("ಕೋಲ್ಕತ್ತಾ", "kolkata howrah bridge", ["kolkata", "howrah"]), ("ಅಸ್ಸಾಂ", "assam tea garden", ["assam"]),
    ("ಕೇರಳ", "kerala backwaters", ["kerala"]), ("ಗೋವಾ", "goa beach", ["goa"]), ("ತಮಿಳುನಾಡು", "tamil nadu temple", ["tamil", "chennai", "madurai"]),
    ("ವಾಷಿಂಗ್ಟನ್", "washington capitol", ["washington", "capitol"]), ("ನ್ಯೂಯಾರ್ಕ್", "new york city", ["new york", "manhattan"]),
    ("ಅಮೆರಿಕ", "new york city skyline", ["new york", "manhattan", "usa", "america"]), ("ಲಂಡನ್", "london big ben", ["london"]),
    ("ಬ್ರಿಟನ್", "london big ben", ["london"]), ("ಪ್ಯಾರಿಸ್", "paris eiffel tower", ["paris", "eiffel"]), ("ಫ್ರಾನ್ಸ್", "paris eiffel tower", ["paris", "eiffel"]),
    ("ಜಪಾನ್", "tokyo city", ["tokyo", "japan"]), ("ಚೀನಾ", "shanghai city", ["china", "shanghai", "beijing"]),
    ("ದುಬೈ", "dubai skyline", ["dubai"]), ("ಯುಎಇ", "dubai skyline", ["dubai", "abu dhabi"]), ("ಸಿಂಗಾಪುರ", "singapore skyline", ["singapore"]),
    ("ಆಸ್ಟ್ರೇಲಿಯಾ", "sydney opera house", ["sydney", "australia"]), ("ಇಂಡೋನೇಷ್ಯಾ", "indonesia", ["indonesia", "jakarta", "bali"]),
    ("ಜರ್ಮನಿ", "berlin city", ["berlin", "germany"]), ("ಕೆನಡಾ", "toronto city", ["toronto", "canada"]),
]


def place_clip(s, used, broll_dir):
    """A landmark / skyline clip of the story's place (s["place_query"] from the bulletin writer wins)."""
    if s.get("place_query"):
        GENERIC = {"city", "skyline", "street", "palace", "garden", "tea", "gate", "opera", "house", "sign", "beach",
                   "tower", "bridge", "temple", "building", "aerial", "view", "night", "the", "of", "big", "marine", "drive"}
        need = [w for w in s["place_query"].lower().split() if w not in GENERIC][:1]   # the place's own name must be in the clip's tags
        return fetch(s, used, broll_dir, photos=False, qlist=[s["place_query"]], need=need or None)[0]
    txt = (s.get("place", "") + " " + s.get("headline", ""))
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


INDIAN_PLACES = ("ಬೆಂಗಳೂರು", "ಕರ್ನಾಟಕ", "ಭಾರತ", "ನವದೆಹಲಿ", "ದೆಹಲಿ", "ಮುಂಬೈ", "ಮೈಸೂರು", "ಮಂಗಳೂರು", "ಚೆನ್ನೈ", "ಹೈದರಾಬಾದ್",
                 "ಅಸ್ಸಾಂ", "ಕೇರಳ", "ಗೋವಾ", "ಕೋಲ್ಕತ್ತಾ", "ಹುಬ್ಬಳ್ಳಿ", "ಧಾರವಾಡ", "ಬೆಳಗಾವಿ", "ಕಲಬುರಗಿ", "ಭೋಪಾಲ್", "ಪುಣೆ", "ಗುಜರಾತ್")
FOREIGN_TAGS = ("dollar", "usd", "euro", "pound sterling", "yen", "yuan", "american flag", "usa", "united states", "new york",
                "london", "wall street", "us flag", "europe")
MONEY_WORDS = ("bank", "money", "finance", "financial", "budget", "cash", "currency", "tax", "price", "salary", "loan", "stock", "market", "economy")

def is_indian(s):
    """Karnataka/India stories, and tech/cinema/sport stories set in India."""
    return s.get("tag") in ("ರಾಜ್ಯ", "ರಾಷ್ಟ್ರೀಯ") or any(p in (s.get("place") or "") for p in INDIAN_PLACES)

def _indian_first(s, qs):
    """Vijay, 27 Nov: Indian stories must look Indian ("when it is india related bank news show indian related banks,
    currencies etc not dollar or other country essence") – try an Indian version of every search first (an Indian
    clip must carry an India tag), add Indian rupee notes for money stories, then the plain search."""
    if not is_indian(s): return qs
    out = []
    for q in qs:
        if q and not any(w in q.lower() for w in ("india", "bangalore", "bengaluru", "mysore", "karnataka", "kerala", "delhi", "mumbai", "assam")):
            out.append("indian " + q)
            if any(w in q.lower() for w in MONEY_WORDS) and "indian rupee notes" not in out: out.append("indian rupee notes")
        out.append(q)
    return out
