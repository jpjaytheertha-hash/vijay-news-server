# Vijay News English — Channel Rules (STRICT, ONE PACKAGE)

Taken over from the Vijay News Kannada rulebook on 28 Nov 2026 (Vijay: "bring all the strict rules there in the kannada channel to this channel too and have a qc in place"; "get all the rule book from the project Vijay News Kannada and just change the script to english and audio to english. and news coverage should be national and international at india level and international level news").

**Every rule here is STRICT and mandatory, and all of them apply together as ONE package.** No bulletin, promo, Short, card, reel, image or fix goes out if it breaks one, and no Claude session or scheduled task may skip or relax a rule. If a task prompt (`TASK_PROMPT.md`) and this file disagree, THIS FILE WINS. A rule changes only when Vijay asks.

**Deliver, don't explain.** When something is blocked (no stock clip, a login wall, a cooldown, a video only as a stream, faces in footage), find the next way and finish: another official source, our own graphic, an AI picture, a different angle of the same keyword. Report a limit only when no way exists, with the exact cause and what was done instead.

**Kept separate from Kannada:** own folder (`english/` in the repo, `VijayNews/English/` on the Mac), own keys, own release (`english-live`), own stream service (`vijaynews-stream@english`), own channel (@VijayNewsEnglish, UCxjASXuE7XMOMKaCPmML0Cw). Never touch the Kannada files from English work.

## 0. Change control
- **Once the news is running fine, do not change it.** Only fix what Vijay reports, or a clear break (wrong visuals, a voice glitch, the stream down).
- **Never change without asking Vijay first:** music (`audio2/`), the end card ("A VIJAY MELPAL PRODUCTION"), the voice, the layout.
- **Work from one chat at a time.** Log every change in the commit message (the repo history is the change log).
- **A change is "done" only when it is ON AIR.** After every requested change: say which edition is on air now and what it does NOT yet have; get the fixed edition QC'd and on air; confirm on the live stream (Studio preview / frame check) before saying "done".
- Re-render only for real fixes; batch fixes into one render.

## 1. QC before publishing (automatic gate – `qc.py`, workflow step "QC")
Every render is checked before it is published. A **FAIL holds the render** (it is not uploaded; the last good bulletin stays on air). The report `qc_report.txt` and a contact sheet `qc_sheet.jpg` (one frame every 20 s) are uploaded to the `english-live` release after every render.
- FAIL: video missing/short; not 1920x1080 25 fps; no audible voice; any non-English script in English text; asking to subscribe / like / share / press the bell; "morning and evening", "twice a day", bulletin times; "first/only AI channel" claims; "see you again"; a story not checked in 2 sources (`sources_checked`); a news outlet named or "reported" attribution anywhere said or shown; a story without a place; a spoken date or weekday; no NATIONAL or no INTERNATIONAL story; a foreign place clip on an Indian story.
- WARN (published, reviewed): length outside 25–30 min; fewer than ~26 stories; a story without a clip/photo; bitrate under 9 Mbps.
- A human (Claude in a chat, or Vijay) also looks at `qc_sheet.jpg` with the shot checklist (2a) whenever a new edition is made, and sends Vijay a pointer-wise report (PASS / FIXED / LIMIT, story number) when he asks.

## 2. Visuals: think like a news editor, one shot per line
- **The script and the pictures must match** (Vijay, 28 Nov 15:18): one shot per sentence, planned in bulletin.json `shots` (`line` = the sentence's first words, `query` + `need` for stock, or `image` + `credit` for an official picture); each clip starts when its line is read (`MultiBRoll` start points). QC fails a story whose sentences have no planned shot and lists every SHOT MISSING.
- One shot per sentence (or part of a long sentence), 2–6 shots per story, each showing that line's WHO, WHAT and WHERE (city, state, country).
- Mix the kinds: moving video, numbers graphic, real photo of the person named, scene of the people affected. Never a generic filler.
- **Indian stories LOOK Indian:** Indian banks, rupee notes, Indian streets, Indian people. Never dollars, foreign flags or foreign cities on an Indian story (`pixabay_vis.py` India-strict pass). The story's PLACE decides the place clip (an India-vs-China match in Bhopal never gets Shanghai).
- **Show WHO is in the sentence:** police → Indian police in khaki; court → court building; health → Indian doctors/hospital; school → Indian classroom; farmers → Indian fields; sport → that sport, Indian players for Indian teams; weather → the actual weather. A landmark is one shot, never the whole story.
- **Real people and real events get the ORIGINAL official image/video first**, credited: PIB (@PIB_India), PMO (@PMOIndia), MEA (@MEAIndia), President's Secretariat (@rashtrapatibhvn), Sansad TV, ministries, RBI/SEBI, ISRO, federations (BCCI, Hockey India, SAI Media…), film production houses, company newsrooms, foreign governments' official handles for international stories. Stock or AI only when no official image exists.
- **Keyword-by-keyword asset plan for EVERY story:** list every keyword (person, organisation, BOTH teams, place, event, object, number) and for each use, in order: its own official account/website → our own number graphic → matching stock (topic + geography) → an AI picture for exactly that keyword and place. Every named thing gets its own image on the line where it is named. Events get the organiser's own photos/videos.
- Accused persons' faces are blurred; victims, minors and anything graphic are never shown.
- **Headline rundown background = that story's own real clip** (`make_bulletin.py roll_video`).
- **No front text over a picture that has its own text** (posters, press notes: `"textimg": true`).
- **Photo framing:** every still is shown whole (contain-fit over a blurred fill); the main person's face is never cut.

### 2a. Shot checklist (before generating and again at QC; any "no" → replace or drop)
1. Why does it exist? 2. Relevant? 3. Right place (India looks Indian; foreign stories show that country)? 4. Accurate (numbers in 2 sources; old photo labelled "File photo")? 5. Legal (approved source, correct credit)? 6. Clean (no other channel's logos/tickers, no garbled text, no real person in AI, nothing graphic)? 7. Labelled right ("AI illustrative visual", "Representative visual • Pixabay", "Photo: <source>", "Vijay News Graphics")?

### 2b. Sources, in this order (free and legal only)
1. Official photos/video from government, ministry, police, civic, federation, company and film handles/websites, credited "<account> (X)" / "Photo: <body>". Never other news channels, papers, journalists, influencers, fan or private accounts.
2. Our own explainer graphics for numbers, prices, counts, comparisons.
3. Pixabay stock: topic tags must match; real camera footage only (no cartoons/3D/abstract); landmark shots need the place name in tags.
4. AI pictures/video when stock has nothing relevant: realistic, labelled "AI illustrative visual", no brand logos; our logo added by us exactly as it is.

### 2c. Promo
- Order: (AI presenter, when Vijay's Gemini clips exist) → Indian tricolour / INDIA | WORLD | BUSINESS over an Indian landmark → verified news over Parliament / Rashtrapati Bhavan → checked across many sources, then written in our own words → fully AI 24x7 over an Indian city → 100% AI → call to action (@VijayNewsEnglish) → Vijay News office walkthrough (`branding/office_walkthrough_en.mp4`) → end card ("A VIJAY MELPAL PRODUCTION").
- Backgrounds: real full-HD footage (Indian flag, Parliament, landmarks), fetched at render time (nothing extra stored).
- Never say or show "morning and evening", "twice a day" or bulletin times anywhere.

### 2d. Branding, LIVE label, date and time, news strip
- "English" appears ONCE near the logo: the gold ENGLISH edition tag centred under VIJAY NEWS between hairline rules (`brand.wordmark`). Under it: "● LIVE 24x7" and the tagline "India & the World • Accurate. Verified. Fast."; the handle @VijayNewsEnglish only on end cards, small.
- Time stamp: every bulletin carries "UPDATED <dd-mm-yyyy> | <hh:mm AM/PM> IST" at the bottom left (render time, IST). The cloud stream copies the video without re-encoding, so a ticking clock is not possible on the free server; the stamp is the honest equivalent.
- The top-right corner stays clear; never bake a fixed date anywhere else.
- **The headline strip scrolls smoothly** (Vijay, 28 Nov 15:30: "breaking n cuts, strain to eyes"): exactly 5 px every frame (125 px/s, `TICK_PX`), never a fractional speed.

## 3. Voice: human Indian-English reading
- Voice chosen by Vijay (28 Nov): Microsoft **en-IN-NeerjaExpressiveNeural**, rate **+10%**. A Google Gemini voice is used only with the English channel's OWN key (`GEMINI_EN_KEY` secret, typed by Vijay) – never the Kannada key.
- Announcements slightly above the music (voice gain 1.3, music bed 0.18).
- Flow: spoken English, short sentences, one idea each, natural connectors; complete spoken headlines (`headline_spoken`); numbers and dates as words; ₹ → "rupees", Rs → "rupees", PM/CM spelled out by `tts.normalize()`.
- **No spoken date or weekday** (the loop runs past midnight): `spoken_intro()` drops any intro sentence with a month or weekday.
- The outro says "Keep watching Vijay News English" once.
- Every word Vijay reports as mispronounced gets a permanent fix the same day (`tts.normalize`) and is listed here.

## 4. Content: India-level national + international
- **Bulletin length 25–30 minutes, about 26 stories:** 6 national, 6 international, 3 business/markets, 3 sport, 2 cinema, 5 tech (AI, digital platforms, IT/startups, space, gadgets), 1 viral people story (last). Each body 75–110 words, 5–6 sentences (why it matters, a figure, the reaction, what happens next) – never padding.
- **Never name a news source** (Vijay, 28 Nov 15:26: "do not mention news sources, you may refer from multiple sources but do not mention the source, only for images and video you mention, you have to rewrite the news after you refer many sources"). Check every story in **at least 2 reliable sources** (kept only in bulletin.json `sources_checked`, never shown or spoken), then REWRITE it completely in our own words – no "Reuters reported", no "Source:" line, no outlet names. Newsmakers may still be quoted ("says Piyush Goyal", "the ministry said"). Credits stay ONLY for pictures and video ("Photo: PIB (X)", "Representative visual • Pixabay"). A story that can't be confirmed in 2 sources is dropped. A trending post is a lead, not a source. Neutral politics; empathy for workers, women and farmers.
- Market wording: "rose / fell / gained / lost", with the exact figures checked at the close.
- Sport scores refreshed right before the render; a match in progress is reported as "at the time of this report".
- X check of official handles (PIB, PMO, MEA, ministries, police, federations) is compulsory.
- Never ask viewers to subscribe; never "see you again"; say "fully AI-produced", never "India's first AI channel".
- Shorts: one story each; upload only to @VijayNewsEnglish.

## 5. Safety
- No passwords, stream keys, API keys or payments by Claude – Vijay types them. Oracle Cloud stays ₹0 (never Pay As You Go).
- Keep the same live URL: never leave the feed down; the server restarts the stream by itself (`server/stream.sh`). Share youtube.com/@VijayNewsEnglish/live.
