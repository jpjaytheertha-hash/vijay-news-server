> **Shots (script and pictures must match):** every story has `"shots": [{"line": "<first words of the sentence>", "query": "<stock search for exactly that line>", "need": ["<tag that must be in the clip>", …]}, …]` – one per sentence (max 4), or `{"line":…, "image": "https://<official photo/video>", "credit": "PIB (X)"}` for an official picture. QC fails a story whose sentences have no planned shot.
>
> **No news sources on air:** check every story in 2+ reliable sources and list them only in `"sources_checked"` (never shown or spoken); write the story completely in our own words – never "Reuters reported", never a "Source:" line. Credits only for pictures/video.
>
> **Read `english/CHANNEL_RULES.md` first – it is STRICT and wins over anything below** (26 stories / 25–30 min, 2 sources checked per story but never named on air, no spoken date, one shot per line, QC gate).

# Vijay News ENGLISH – instructions for the scheduled bulletin task
(Read by the scheduled task "Vijay News ENGLISH – morning & evening bulletin" at 7:21 AM and 6:21 PM IST.)

Write the next edition of the "Vijay News English" news bulletin (YouTube channel @VijayNewsEnglish, channel id UCxjASXuE7XMOMKaCPmML0Cw, owner Vijay, vijaymelpal@gmail.com). On 27 Nov 2026 Vijay asked for an English channel "for english, India level news, all national level and international level, good quality news, same as we did for 'vijaynews kannada'", with Kannada and English kept in separate folders "so no confusion and no mess ups". It follows the same rules Vijay set for the Kannada channel: "not just political news" – the USP is "unique and quality news" incl. technology, digital media (search, Google, Meta), IT, AI, robots, automotive; sports and unique cinema stories (no gossip); never ask viewers to subscribe; the X step is compulsory; real-looking video clips for every story; the video runs in a loop all day. Work unattended; ask no questions.

EDITION: if the current IST time is before 14:00 this is the MORNING edition (archive suffix _am), otherwise the EVENING edition (suffix _pm).

WHERE THINGS LIVE (cloud – the Mac is NOT needed): the English channel is produced in the public GitHub repository jpjaytheertha-hash/vijay-news-server, folder english/. Attach it with mcp__claude-code-remote__add_repo (owner jpjaytheertha-hash, repo vijay-news-server, access push) and clone it (git clone --depth 1). You only write english/bulletin.json (and an archive copy); do NOT edit any other file. Pushing english/bulletin.json to main starts the GitHub Actions workflow "English bulletin render", which makes the video (Microsoft Indian-English voice, free Pixabay clips) and publishes it to the release "english-live"; a small Oracle server streams it 24x7. NEVER touch the Kannada channel (root folder of the repo and the Mac folders /Volumes/One Touch/VijayNews/vijay-news/ and /archive/).

STEP 1 – Previous bulletins: read english/bulletin.json and the newest 1–2 files in english/archive/ of the repository. Do not repeat their stories unless there is a real new development; do not reuse the previous TECH sub-topics or the same film.

STEP 2 – X FIRST (compulsory, ~10 minutes). Load the Chrome tools in ONE ToolSearch call (tabs_context_mcp, tabs_create_mcp, navigate, get_page_text, computer, tabs_close_mcp). tabs_context_mcp (createIfEmpty true), open ONE new tab. Vijay's Chrome (on his Mac) is signed in to X; if the Mac/Chrome is not reachable, use WebSearch instead and say so. For each page: navigate, wait ~5 s, get_page_text, note posts from the last ~14 hours: https://x.com/PMOIndia, https://x.com/narendramodi, https://x.com/PIB_India, https://x.com/MEAIndia, https://x.com/RBI, https://x.com/isro, https://x.com/RailMinIndia, https://x.com/DRDO_India, https://x.com/ECISVEEP, https://x.com/IMDWeather, and https://x.com/explore/tabs/trending (India trends that are real news topics). Check each account is the official one (verified badge, matching name); skip otherwise. Never sign in, post, like, repost, follow, reply or open DMs; close your tab. If Chrome does not answer after one retry, use WebSearch for news reports of those posts and say so in the notification.
What becomes news: official decisions, schemes, appointments, launches, diplomatic statements, RBI/ISRO/Railway/weather announcements with real public impact, and the most-discussed real news topic on X (only if a reliable outlet confirms it – "trending on X"; never invent view counts). NOT greetings, birthday wishes, campaigning or attacks on opponents (unless it is the main political news – then report both sides neutrally). Target: at least 2 of the 12 stories come from X when such posts exist. Never name the outlet or the post on air; record what you checked in "sources_checked" ("PMO India (X), The Hindu"). An official advisory plus one more reliable source confirms a story. Write every line yourself – never copy a post's wording.

STEP 3 – Research (WebSearch; WebFetch the articles you use). 12 stories in total (incl. X stories), all from the last ~14 hours (morning edition: overnight + this morning; evening: today), in EXACTLY this order and mix:
- 4 × NATIONAL (India-level: governance, Parliament, courts, economy-policy, infrastructure, weather, science, education, health; at least one from a state other than Karnataka; avoid purely local city news),
- 3 × INTERNATIONAL (world – biggest stories, with an India angle where one exists),
- 1 × BUSINESS (markets, RBI, economy, big Indian companies, startups – confirmed numbers only),
- 1 × SPORTS (biggest result/event for Indian fans – cricket, football, hockey, kabaddi, badminton, tennis, chess, athletics, Olympic sports; women's and men's alike; final results or officially confirmed news only, no rumours, betting or fantasy),
- 1 × CINEMA (ONE unique, genuinely interesting film story – Indian cinema of any language, then world cinema: breakthrough small films, confirmed box-office/OTT milestones, festival selections and awards, restorations, filmmaking technology, certification/policy, debut directors, landmark anniversaries. AVOID trailer/poster/song launches, gossip, personal lives, rumoured casting, fan wars, paid promotion),
- 2 × TECH (the USP): (a) AI / robotics, (b) rotating: digital media & platforms (Google, Meta, YouTube, X, search, online rules) OR IT industry (Infosys, TCS, Wipro, GCCs, hiring) OR automotive/EV OR gadgets/space tech – not the same sub-topic as the previous bulletin.
Prefer stories viewers feel connected to and enjoy: things that affect daily life in India (prices, jobs, travel, weather, exams), proud moments, genuinely surprising facts – always true, sourced, not sensational.
Sources: cross-check every story in at least two reliable sources (PTI/ANI via outlets, The Hindu, Indian Express, Hindustan Times, Times of India, NDTV, Mint, Economic Times, Business Standard, Moneycontrol, Reuters, AP, BBC, Al Jazeera, official government/UN sites; tech: The Verge, TechCrunch, Ars Technica; sports: ESPNcricinfo, Sportstar, official boards; cinema: official statements, festival sites, Variety, The Hollywood Reporter, Film Companion). Drop anything you cannot confirm. No graphic violence details, no unverified claims, no speculation about private individuals, no names of victims or minors. Politics: neutral, report each side, no opinions.
COPYRIGHT: never copy wording from any outlet or post; write every line yourself in clear broadcast English. Facts only.

STEP 4 – Write english/bulletin.json in exactly this structure (UTF-8, valid JSON):
{
 "channel": "Vijay News English", "channel_en": "VIJAY NEWS ENGLISH", "byline": "A Vijay Melpal Production",
 "date_en": "<Weekday>, <day> <Month> <year>",
 "intro": "Hello and welcome to Vijay News English. It is <weekday>, the <day in words> of <Month>. Here are the top stories from India and around the world, with business, sports, cinema and technology.",
 "outro": "Those were the top stories right now. We will be back shortly with the latest updates. Keep watching Vijay News English.",
 "stories": [ 12 × {
   "section": "National News" | "International News" | "Business News" | "Sports News" | "Cinema News" | "Tech News",
   "tag": "NATIONAL" | "INTERNATIONAL" | "BUSINESS" | "SPORTS" | "CINEMA" | "TECH",
   "place": "<city / state / country>",
   "headline": "<max ~60 characters, a natural complete phrase: subject + what happened; no ; or |>",
   "headline_spoken": "<the headline as one natural spoken sentence ending with a full stop>",
   "stat": "<one key number, max 6 characters, e.g. 56, 12.1°, 98%, 3-1, $4bn>",
   "stat_label": "<label for the number, max ~32 characters>",
   "icon": "calendar" | "pin" | "thermo" | "globe",
   "facts": ["<3 fact lines – see FACT LINES>"],
   "sources_checked": "<2+ outlets / official accounts you checked – internal only, never shown or spoken>",
   "body": "<the spoken script, 60–95 words, 3–4 sentences>",
   "image_query": "<main clip, 2–5 English words – see STEP 4b>",
   "image_queries": ["<main clip, same as image_query>", "<second clip: another real angle of the same story>"],
   "place_query": "<landmark / skyline / signage of the place, or \"\">"
 } ]
}
The intro and outro are always exactly those sentences (no "good morning/evening" – the video loops all day; never "see you tomorrow"). NEVER ask viewers to subscribe, like, share or press the bell.
FACT LINES: each of the 3 facts is a short COMPLETE statement a viewer understands without the voice – subject + what happened/what it means + the key number, time, place or name (e.g. "RBI keeps the repo rate unchanged at 5.5%"). 30–60 characters each; never a fragment or a bare list; the facts add information beyond the headline and do not repeat each other.
BODY (read aloud by a TTS voice): natural spoken broadcast English, warm and engaging – open with what matters to people, say why it matters in one simple line; write "rupees" instead of ₹ or Rs; spell out abbreviations on first mention ("the Reserve Bank of India"); full names on first mention; attribute claims ("…, the ministry said", "…, Reuters reported"). Markets: "rose / gained / fell / slipped", with the number.
On-screen text (headline, facts, stat, place): no emoji or arrows; ₹ is fine on screen.

STEP 4b – Real-looking video clips (the cloud render downloads free Pixabay clips and plays up to 3 per story: main → place → second). "image_query" / "image_queries"[0]: the MAIN clip – 2–5 plain English words naming the concrete, filmable real scene (e.g. "parliament building india", "stock market trading screen", "cricket match stadium", "rocket launch"). "image_queries"[1]: a SECOND real angle (e.g. "office workers computers", "cricket fans cheering", "commuters railway station"). "place_query": landmark/skyline that makes viewers recognise the place – New Delhi → "India Gate Delhi"; Mumbai → "Mumbai Marine Drive"; Bengaluru → "Bangalore city skyline"; Kolkata → "Kolkata howrah bridge"; USA → "New York city skyline" or "Washington capitol"; UK → "London Big Ben"; France → "Paris eiffel tower"; China → "Shanghai city"; Japan → "Tokyo city street"; Dubai → "Dubai skyline"; Russia → "Moscow kremlin"; "" if no specific place. For every Indian story (all NATIONAL stories and any business, sports, tech or cinema story about India) the clips must LOOK INDIAN: write Indian specifics ("indian rupee notes", "indian bank branch", "mumbai stock exchange building", "indian railway station", "indian parliament", "indian farmers field", "indian city traffic") – never dollars, euros, foreign flags or foreign city scenes; the renderer also rejects such clips. Name the sport exactly (field hockey, not hockey); concrete objects only, never abstract words; never a real person's name, team, brand, logo or film title; nothing violent; never disaster footage presented as the actual event. No Canva, no broll_url.
Validate with python3: exactly 12 stories in the order 4/3/1/1/1/2 (NATIONAL/INTERNATIONAL/BUSINESS/SPORTS/CINEMA/TECH), every field present, image_queries has 2 items, each fact 30–60 characters, no "subscribe", JSON parses.

STEP 5 – Deliver: write english/bulletin.json and english/archive/bulletin_<YYYYMMDD>_<am|pm>.json in your clone, validate, then
git add english/bulletin.json english/archive/ && git -c user.name="Vijay News Bot" -c user.email="vijaymelpal@gmail.com" commit -m "English <morning|evening> bulletin <YYYY-MM-DD>" && git -c push.negotiate=true push origin HEAD:main
(if the push is rejected because main moved: git fetch --depth=20 origin main && git rebase origin/main, then push again; never force-push). If the repository cannot be attached or pushed after one retry, push the notification "Vijay News ENGLISH bulletin NOT delivered: <reason>" and stop.

STEP 6 – Check the render: wait about 20 minutes (sleep in steps), then check the workflow run with gh (REST only): gh api "repos/jpjaytheertha-hash/vijay-news-server/actions/runs?per_page=3" --jq '.workflow_runs[] | [.name,.status,.conclusion,.head_sha,.html_url] | @tsv' – find the run for your commit. When it is completed with success, read the published status: curl -sL https://github.com/jpjaytheertha-hash/vijay-news-server/releases/download/english-live/status.txt (rendered time, voice, "visual for story N" lines). If it failed, get the failing step's log (gh api …/actions/runs/<id>/jobs) and report the reason.

NOTIFY: one PushNotification: "Vijay News ENGLISH <morning/evening> bulletin: <3 short headline keywords> — rendered in the cloud ✓ (voice <edge/gemini>, clips on <n>/12 stories) · X: <n> stories from <handles>" or "— NOT rendered: <reason>".
