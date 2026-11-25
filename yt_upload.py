#!/usr/bin/env python3
"""Vijay News - upload the previous day's bulletins (morning + 6 PM) as normal YouTube videos.

Uses only the Python standard library and the official YouTube Data API v3.
  python3 yt_upload.py auth      one-time Google sign-in (opens the browser; saves a token on this Mac)
  python3 yt_upload.py daily     upload every finished day's editions that are not uploaded yet
  python3 yt_upload.py dry       show what would be uploaded, upload nothing

Which file is which edition (times are IST, from the file name vijay_news_YYYYMMDD_HHMM.mp4):
  morning edition of day D = newest video made between D 05:00 and D 17:30
  evening edition of day D = newest video made between D 17:30 and D+1 05:00
A day is uploaded only after D+1 06:00, so late re-renders are included.
Uploaded files are recorded in uploaded_videos.txt (one line each; never re-uploaded).
"""
import datetime as dt, glob, http.server, json, os, re, secrets, socket, sys, threading
import time, urllib.error, urllib.parse, urllib.request, webbrowser, hashlib, base64

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.join(HERE, "archive") if os.path.isdir(os.path.join(HERE, "archive")) else os.path.join(os.path.dirname(HERE), "archive")
CLIENT = os.path.expanduser("~/.vijaynews_yt_client.json")
TOKEN = os.path.expanduser("~/.vijaynews_yt_token.json")
DONE = os.path.join(HERE, "uploaded_videos.txt")
LOCK = os.path.join(HERE, ".uploading")
LOG = os.path.join(HERE, "upload.log")
CHANNEL_ID = "UCU6Jmy4g_BcI4o7QvPehLdg"          # Vijay News (@VijayNewsKannada) - never any other channel
FIRST_DAY = dt.date(2026, 11, 25)                 # start with the bulletins of 25 Nov 2026
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
KN_MONTHS = "ಜನವರಿ ಫೆಬ್ರವರಿ ಮಾರ್ಚ್ ಏಪ್ರಿಲ್ ಮೇ ಜೂನ್ ಜುಲೈ ಆಗಸ್ಟ್ ಸೆಪ್ಟೆಂಬರ್ ಅಕ್ಟೋಬರ್ ನವೆಂಬರ್ ಡಿಸೆಂಬರ್".split()
KN_DAYS = "ಸೋಮವಾರ ಮಂಗಳವಾರ ಬುಧವಾರ ಗುರುವಾರ ಶುಕ್ರವಾರ ಶನಿವಾರ ಭಾನುವಾರ".split()   # Monday first
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def log(msg):
    line = f"{dt.datetime.now(IST):%Y-%m-%d %H:%M} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------- OAuth
def _client():
    with open(CLIENT, encoding="utf-8") as f:
        c = json.load(f)
    return c.get("installed") or c.get("web") or c


def _post(url, data):
    req = urllib.request.Request(url, urllib.parse.urlencode(data).encode(),
                                 {"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def auth():
    if not os.path.exists(CLIENT):
        sys.exit(f"Missing {CLIENT} - run SETUP_YOUTUBE_UPLOAD.command")
    c = _client()
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    redirect = f"http://127.0.0.1:{port}"
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state:
                got.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            ok = "code" in got
            self.wfile.write(("<h2>Vijay News: " + ("signed in - you can close this tab." if ok else
                              "sign-in did not finish, please run the setup again.") + "</h2>").encode())

        def log_message(self, *a):
            pass

    headless = sys.platform.startswith("linux") and not os.environ.get("DISPLAY")
    if headless:   # server: no browser here – Vijay opens the link on his own computer and pastes back the final address
        redirect = "http://127.0.0.1:8765"
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
            "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
            "access_type": "offline", "prompt": "consent select_account", "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256"})
        print("\n1) Open this link in Chrome on your Mac or phone:\n\n" + url +
              "\n\n2) Sign in, CHOOSE THE 'Vijay News' CHANNEL, allow access."
              "\n3) The browser then shows 'This site can't be reached' – that is expected."
              "\n   Copy the full address from the address bar (starts with http://127.0.0.1:8765/?state=...) and paste it here.\n")
        back = input("Paste the address: ").strip()
        q = urllib.parse.parse_qs(urllib.parse.urlparse(back).query)
        if q.get("state", [""])[0] != state:
            sys.exit("That address does not belong to this sign-in – run the setup again.")
        got.update({k: v[0] for k, v in q.items()})
    srv = None if headless else http.server.HTTPServer(("127.0.0.1", port), H)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent select_account", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    if headless:
        pass
    else:
      print("\nA browser window opens. Sign in, CHOOSE THE 'Vijay News' CHANNEL, and allow access.\n"
          "If it does not open, paste this link into Chrome:\n" + url + "\n")
      webbrowser.open(url)
      t0 = time.time()
      while "code" not in got and "error" not in got and time.time() - t0 < 600:
        srv.timeout = 5; srv.handle_request()
    if "code" not in got:
        sys.exit("Sign-in not completed: " + got.get("error", "timed out"))
    tok = _post("https://oauth2.googleapis.com/token", {
        "code": got["code"], "client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
        "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier})
    if "refresh_token" not in tok:
        sys.exit("Google did not return a refresh token - run the setup again.")
    fd = os.open(TOKEN, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"refresh_token": tok["refresh_token"]}, f)
    cid, title = my_channel(access_token())
    print(f"Signed in to channel: {title} ({cid})")
    if cid != CHANNEL_ID:
        os.remove(TOKEN)
        sys.exit("That is NOT the Vijay News channel. Run the setup again and choose 'Vijay News'.")
    print("OK - daily uploads are ready.")


def access_token():
    c = _client()
    with open(TOKEN) as f:
        rt = json.load(f)["refresh_token"]
    return _post("https://oauth2.googleapis.com/token", {
        "client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
        "refresh_token": rt, "grant_type": "refresh_token"})["access_token"]


def my_channel(at):
    req = urllib.request.Request("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                                 headers={"Authorization": "Bearer " + at})
    with urllib.request.urlopen(req, timeout=60) as r:
        items = json.load(r).get("items", [])
    return (items[0]["id"], items[0]["snippet"]["title"]) if items else ("", "")


# ---------------------------------------------------------------- choosing the files
def videos():
    out = []
    for p in glob.glob(os.path.join(HERE, "vijay_news_*.mp4")):
        m = re.search(r"vijay_news_(\d{8})_(\d{4})\.mp4$", p)
        if m and os.path.getsize(p) > 5_000_000:
            out.append((dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M"), p))
    return sorted(out)


def editions(now):
    vids, res = videos(), []
    if not vids:
        return res
    day = max(FIRST_DAY, vids[0][0].date() - dt.timedelta(days=1))
    while dt.datetime.combine(day + dt.timedelta(days=1), dt.time(6, 0)) <= now:
        d0 = dt.datetime.combine(day, dt.time(5, 0))
        d1 = dt.datetime.combine(day, dt.time(17, 30))
        d2 = d0 + dt.timedelta(days=1)
        for ed, a, b in (("am", d0, d1), ("pm", d1, d2)):
            inside = [p for t, p in vids if a <= t < b]
            if inside:
                res.append((day, ed, inside[-1]))
        day += dt.timedelta(days=1)
    return res


def done_names():
    if not os.path.exists(DONE):
        return set()
    with open(DONE, encoding="utf-8") as f:
        return {ln.split()[0] for ln in f if ln.strip()}


# ---------------------------------------------------------------- titles / descriptions
def bulletin_for(day, ed):
    p = os.path.join(ARCHIVE, f"bulletin_{day:%Y%m%d}_{ed}.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def metadata(day, ed):
    b = bulletin_for(day, ed)
    kn_date = f"{KN_MONTHS[day.month - 1]} {day.day}, {day.year} {KN_DAYS[day.weekday()]}"
    en_date = f"{day.day} {day:%B %Y}"
    kn_ed = "ಬೆಳಗಿನ ಸುದ್ದಿ" if ed == "am" else "ಸಂಜೆ 6ರ ಸುದ್ದಿ"
    en_ed = "Morning" if ed == "am" else "Evening 6 PM"
    title = f"{kn_ed} | {kn_date} | Vijay News Kannada"
    if len(title) > 100:
        title = f"{kn_ed} | {en_date} | Vijay News Kannada"
    lines = [f"ವಿಜಯ್ ನ್ಯೂಸ್ ಕನ್ನಡ – {kn_ed}, {kn_date}",
             f"Vijay News Kannada – {en_ed} bulletin of {day:%A}, {en_date}.", ""]
    stories = b.get("stories") or []
    if stories:
        lines.append("ಈ ಸುದ್ದಿಗಳಲ್ಲಿ:")
        lines += [f"• {s.get('tag', '')}: {s.get('headline', '')}" for s in stories]
        lines.append("")
    lines += ["24x7 ಲೈವ್: https://www.youtube.com/@VijayNewsKannada/live",
              "ಕನ್ನಡದ 100% AI ನ್ಯೂಸ್ ಚಾನೆಲ್ – AI voice and AI illustrative pictures (labelled \"AI ಸಾಂಕೇತಿಕ ದೃಶ್ಯ\"); "
              "facts checked with 2+ reliable sources.",
              "A Vijay Melpal Production.", "",
              "#KannadaNews #KannadaNewsLive #VijayNewsKannada #KarnatakaNews #BengaluruNews"]
    desc = "\n".join(lines).replace("<", "").replace(">", "")
    while len(desc.encode("utf-8")) > 4900:
        desc = desc[:-100]
    tags = ["Kannada news", "Kannada news live", "Vijay News Kannada", "Karnataka news", "Bengaluru news",
            "ಕನ್ನಡ ಸುದ್ದಿ", "ಕನ್ನಡ ನ್ಯೂಸ್", f"Kannada news {en_date}", "AI news"]
    return title, desc, tags


# ---------------------------------------------------------------- upload
def upload(path, title, desc, tags, at):
    body = {"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "25",
                        "defaultLanguage": "kn", "defaultAudioLanguage": "kn"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": True, "embeddable": True}}
    size = os.path.getsize(path)
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + at, "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    with urllib.request.urlopen(req, timeout=120) as r:
        loc = r.headers["Location"]
    chunk, pos, tries = 16 * 1024 * 1024, 0, 0
    with open(path, "rb") as f:
        while True:
            f.seek(pos); data = f.read(chunk)
            end = pos + len(data) - 1
            put = urllib.request.Request(loc, data, method="PUT", headers={
                "Content-Length": str(len(data)), "Content-Range": f"bytes {pos}-{end}/{size}"})
            try:
                with urllib.request.urlopen(put, timeout=600) as r:
                    return json.load(r)                      # 200/201 = finished
            except urllib.error.HTTPError as e:
                if e.code == 308:                             # chunk accepted, continue
                    rng = e.headers.get("Range")
                    pos = int(rng.split("-")[1]) + 1 if rng else 0
                    tries = 0; continue
                if e.code in (500, 502, 503, 504) and tries < 5:
                    tries += 1; time.sleep(10 * tries); pos = _resume_pos(loc, size); continue
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]!r}")
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if tries >= 5:
                    raise
                tries += 1; time.sleep(15 * tries); pos = _resume_pos(loc, size)


def _resume_pos(loc, size):
    req = urllib.request.Request(loc, b"", method="PUT",
                                 headers={"Content-Length": "0", "Content-Range": f"bytes */{size}"})
    try:
        urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        if e.code == 308:
            rng = e.headers.get("Range")
            return int(rng.split("-")[1]) + 1 if rng else 0
    return 0


def free_space(day):
    """Vijay (25 Nov 2026): delete the uploaded videos from the Mac. Once BOTH editions of a day are
    uploaded, delete every bulletin video of that day (incl. superseded re-renders) - but never the
    newest video and never the one in the live playlist."""
    names = done_names()
    d0 = dt.datetime.combine(day, dt.time(5, 0)); d2 = d0 + dt.timedelta(days=1)
    eds = [p for dd, e, p in editions(dt.datetime.now(IST).replace(tzinfo=None)) if dd == day]
    if not eds or any(os.path.basename(p) not in names for p in eds):
        return
    vids = videos()
    keep = {vids[-1][1]} if vids else set()
    try:
        with open(os.path.join(HERE, "playlist.txt"), encoding="utf-8") as f:
            keep |= set(re.findall(r"file '([^']+)'", f.read()))
    except OSError:
        pass
    for t, p in vids:
        if d0 <= t < d2 and p not in keep and os.path.abspath(p) not in keep:
            try:
                mb = os.path.getsize(p) // 1_000_000
                os.remove(p); log(f"deleted from Mac (uploaded): {os.path.basename(p)} ({mb} MB)")
            except OSError as ex:
                log(f"could not delete {os.path.basename(p)}: {ex}")


# ---------------------------------------------------------------- Shorts (server: replaces the Chrome upload task)
SHORTS_DONE = os.path.join(HERE, "shorts", "uploaded.txt")


def shorts_todo():
    try:
        with open(SHORTS_DONE, encoding="utf-8") as f:
            done = {ln.split()[0] for ln in f if ln.strip()}
    except OSError:
        done = set()
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "shorts", "*.mp4"))):
        n = os.path.basename(p)
        if n.startswith("upload_") or n in done or time.time() - os.path.getmtime(p) > 24 * 3600:
            continue
        if n.startswith("short_") or n.startswith("special_"):
            out.append(p)
    return out


def short_metadata(path):
    n = os.path.basename(path)
    tail = ("\n\nಪೂರ್ಣ ಸುದ್ದಿ 24x7 ಲೈವ್: https://www.youtube.com/@VijayNewsKannada/live\n"
            "Vijay News Kannada – ಕನ್ನಡದ 100% AI ನ್ಯೂಸ್ ಚಾನೆಲ್. AI voice and AI illustrative pictures "
            "(labelled \"AI ಸಾಂಕೇತಿಕ ದೃಶ್ಯ\"); facts checked with 2+ reliable sources.\nA Vijay Melpal Production.\n"
            "#Shorts #KannadaNews #KannadaNewsLive #VijayNewsKannada #KarnatakaNews")
    if n.startswith("special_"):
        sid = n[len("special_"):-4]
        try:
            with open(os.path.join(HERE, "specials", sid + ".json"), encoding="utf-8") as f:
                sp = json.load(f)
        except Exception:
            sp = {}
        st = sp.get("story", sp)
        head = st.get("headline") or sp.get("headline") or "ವಿಶೇಷ ಸುದ್ದಿ"
        title = f"{head} | Vijay News Kannada #Shorts"
        desc = (sp.get("script") or st.get("body") or head)[:600] + (f"\nSource: {sp['sources']}" if sp.get("sources") else "") + tail
    else:
        try:
            with open(os.path.join(HERE, "bulletin.json"), encoding="utf-8") as f:
                b = json.load(f)
        except Exception:
            b = {}
        st = b.get("stories") or []
        picks = st[:1] + [next((x for x in st if x.get("tag") == t), None) for t in ("ಕ್ರೀಡೆ", "ಸಿನಿಮಾ", "ಟೆಕ್")]
        picks = [x for x in picks if x]
        h = picks[0]["headline"] if picks else "ಇಂದಿನ ಪ್ರಮುಖ ಸುದ್ದಿ"
        title = f"{h} | ಇಂದಿನ ಪ್ರಮುಖ ಸುದ್ದಿ | Kannada News #Shorts"
        desc = "ಇಂದಿನ ಪ್ರಮುಖ ಸುದ್ದಿಗಳು – ವಿಜಯ್ ನ್ಯೂಸ್ ಕನ್ನಡ\n" + "\n".join(
            f"• {x.get('tag', '')}: {x.get('headline', '')}" for x in picks) + tail
    if len(title) > 100:
        title = title[:88].rstrip() + "… #Shorts"
    tags = ["Kannada news", "Kannada news live", "Vijay News Kannada", "Shorts", "ಕನ್ನಡ ಸುದ್ದಿ"]
    return title, desc.replace("<", "").replace(">", ""), tags


def upload_shorts():
    for p in shorts_todo():
        title, desc, tags = short_metadata(p)
        log(f"uploading Short {os.path.basename(p)} as '{title}'")
        try:
            v = upload(p, title, desc, tags, access_token())
            link = f"https://youtube.com/shorts/{v.get('id')}"
            with open(SHORTS_DONE, "a", encoding="utf-8") as f:
                f.write(f"{os.path.basename(p)} {link}\n")
            log(f"Short uploaded ✓ {link} ({v.get('status', {}).get('privacyStatus', '')})")
            if v.get("id"):
                os.remove(p)   # free the disk once it is on YouTube
        except Exception as ex:
            log(f"Short upload FAILED {os.path.basename(p)}: {ex}")


def daily(dry=False):
    now = dt.datetime.now(IST).replace(tzinfo=None)
    todo = [(d, e, p) for d, e, p in editions(now) if os.path.basename(p) not in done_names()]
    if dry:
        for d, e, p in todo:
            print(d, e, os.path.basename(p), "|", metadata(d, e)[0])
        return
    if not todo and not shorts_todo():
        return
    if not os.path.exists(TOKEN):
        log("upload skipped – not signed in yet (run SETUP_YOUTUBE_UPLOAD.command)"); return
    if os.path.exists(LOCK) and time.time() - os.path.getmtime(LOCK) < 3 * 3600:
        return
    open(LOCK, "w").close()
    try:
        at = access_token()
        cid, name = my_channel(at)
        if cid != CHANNEL_ID:
            log(f"upload STOPPED – token is for channel '{name}' ({cid}), not Vijay News"); return
        for d, e, p in todo:
            title, desc, tags = metadata(d, e)
            log(f"uploading {os.path.basename(p)} as '{title}'")
            try:
                v = upload(p, title, desc, tags, access_token())
                st = v.get("status", {})
                link = f"https://youtu.be/{v.get('id')}"
                with open(DONE, "a", encoding="utf-8") as f:
                    f.write(f"{os.path.basename(p)} {link} {d:%Y-%m-%d} {e} {st.get('privacyStatus', '')}\n")
                log(f"uploaded ✓ {link} ({st.get('privacyStatus', '')})")
                if v.get("id"):
                    free_space(d)
            except Exception as ex:
                log(f"upload FAILED {os.path.basename(p)}: {ex}")
                if "quotaExceeded" in str(ex) or "uploadLimitExceeded" in str(ex):
                    break
        if os.environ.get("VN_UPLOAD_SHORTS") == "1":
            upload_shorts()
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            open(LOCK, "w").close(); os.utime(LOCK, (0, 0))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if cmd == "auth":
        auth()
    elif cmd == "dry":
        daily(dry=True)
    else:
        daily()
