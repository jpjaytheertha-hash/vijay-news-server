# Vijay News – handover note (25 Nov 2026, 00:40 IST)

Start a new Claude chat and say: "Continue Vijay News – read /Volumes/One Touch/VijayNews/vijay-news/HANDOFF.md"

## What exists
- YouTube channel: Vijay News (@VijayNewsKannada), account vijaymelpal@gmail.com. Live streaming access opened ~00:31 IST 25 Nov.
- Project folder: /Volumes/One Touch/VijayNews/vijay-news/ (external drive "One Touch").
- Kannada bulletin renderer: make_bulletin.py (reads bulletin.json, makes vijay_news_<date>.mp4).
- Voice: Google Gemini TTS, voice **Puck** (chosen by Vijay – "always"), free AI Studio key saved at ~/.vijaynews_gemini_key.
  3 requests per bulletin (free tier ~10/day). Retries ~10 min; backup = Microsoft kn-IN-GaganNeural (male).
- Promo: promo.py + promo_clips/ (Gemini-made clips), plays after each bulletin.
- GO_LIVE.command: loops latest bulletin + promo to YouTube (stream key saved at ~/.vijaynews_streamkey after first run).
- INSTALL_AUTOSTART.command: starts GO_LIVE at login (run after GO_LIVE works).

## Story mix (from 25 Nov 2026) – 10 stories
3 ರಾಜ್ಯ, 2 ರಾಷ್ಟ್ರೀಯ, 2 ಅಂತರರಾಷ್ಟ್ರೀಯ, 3 ಟೆಕ್ (AI/robots; digital media – Google/search/Meta/YouTube; rotating automotive / IT industry / gadgets-space).
USP: unique, quality news, not just politics. Facts from 2+ reliable sources, original Kannada wording.

## Scheduled tasks (Claude app → Scheduled)
- "Vijay News – morning Kannada bulletin (with drive)" 6:31 AM IST – ACTIVE, has the One Touch folder.
- "Vijay News – evening 6 PM Kannada bulletin" 5:31 PM IST – ACTIVE, has the folder.
- OLD "Vijay News – morning Kannada bulletin" (no folder) – Vijay to switch OFF manually.

## Open items
1. Render tonight's bulletin with the Puck voice: in a NEW Terminal window run
   bash "/Volumes/One Touch/VijayNews/vijay-news/MAKE_BULLETIN.command"
   (it now writes make_bulletin.log in the project folder). Last attempts did not start – check the log / Terminal text.
2. Go live: run GO_LIVE.command, paste the stream key from YouTube Studio → Go live → Stream (never paste it in chat),
   set title/description, Altered content = Yes. Then run INSTALL_AUTOSTART.command.
3. Keep the Mac awake, the One Touch drive connected and the Claude app open for the scheduled bulletins.
4. Branding claim: do NOT say "first Kannada AI news channel" (Power TV's Soundarya, News First's Maya came earlier, 2023).
   Use "Karnataka's fully AI-produced 24×7 Kannada news channel".

## Working rules
- Never take full-screen screenshots of Vijay's Mac; only single-app background views, and ask first.
- Never enter passwords, API keys or stream keys; Vijay types them into Terminal himself.
- No payments.

## Status 25 Nov 00:52 IST
- GO_LIVE is running (stream key saved). Fix that made it work: Terminal needed Removable Volumes / Full Disk Access.
- Streaming vijay_news_20261124_2338.mp4; Puck re-render + promo building in background (render.log, promo.log).
- Next: check YouTube preview/title/Altered content, then run INSTALL_AUTOSTART.command.

## Update 25 Nov 01:15 IST
- tts.py: Puck now in small batches (≤3 stories), each finished clip cached in build/*.npy (no repeat requests),
  failed batch split in half; when gemini-3.1-flash-tts free quota is used up it switches to gemini-2.5-flash-preview-tts
  (same Puck voice, separate quota), then -pro. Backup copy: build/tts_v5_backup.py.
- Tonight: 3.1 quota (≈10/day, resets 13:30 IST) was used up by retries → old in-memory render will fall back to Microsoft.
  After it finishes, touch bulletin.json so GO_LIVE re-renders with the 2.5 Puck fallback (headlines already cached).
- make_bulletin.py: per-story AI visual. In bulletin.json add "broll": "broll/<file>" per story (.mp4 looped or .jpg/.png
  with slow zoom); shown in the left panel with label "AI ಸಾಂಕೇತಿಕ ದೃಶ್ಯ". Backup: build/make_bulletin_v6_backup.py.
  OPEN: source of visuals – Canva generate-image works but the connector only returns a 198px thumbnail; Veo video API is paid.
- Promo plays after each bulletin (playlist.txt). INSTALL_AUTOSTART not yet run (was pasted into the GO_LIVE window).
- Don't paste commands into the GO_LIVE window – ffmpeg reads them as input. Ctrl+C alone just restarts the stream; close the window to stop.
- 01:20: FREE visuals route works: Canva generate-image → create-design (YouTube Thumbnail, full-bleed) → export-design jpg 1280
  → URL goes in bulletin.json "broll_url"; make_bulletin.py downloads it on the Mac (cloud sandboxes can't reach Canva's download host).
  Morning + evening scheduled tasks updated with STEP 3b (visuals) – push message now says voice + "visuals n/10".
  Tonight's bulletin: story 1 (Bengaluru rain) has a test visual. Old no-folder morning task still ON – Vijay must switch it off.
- 01:20: Old no-folder morning task switched OFF; "(with drive)" morning + evening ON. Old render finished (Microsoft voice,
  vijay_news_20261125_0059.mp4). bulletin.json touched → GO_LIVE re-renders with new code after the current playlist pass.
  Check at 01:45 scheduled in this chat.
- 01:29: vijay_news_20261125_0123.mp4 READY – Puck voice (gemini-2.5-flash-preview-tts fallback worked) + Canva rain picture
  on story 1 (checked frame). GO_LIVE switches to it after the current loop pass.
- 01:45: CONFIRMED LIVE: vijay_news_20261125_0123.mp4 (Puck + rain picture) + promo, looping without drops.

## 25 Nov 08:15 IST
- 6:31 morning bulletin (10 stories, 10/10 Canva pictures) LIVE since 07:11 without drops – but Microsoft voice:
  all 3 Gemini TTS models' free daily quota was used by last night's re-renders. Quota window = 13:30 IST → 13:30 IST,
  so evening 17:31 + next morning 6:31 share one window. Avoid manual re-renders in that window.
- Bug fixed: picture files were named bulletin_s<i>.jpg and reused across bulletins (story 1 showed last night's rain).
  Now named v_<md5 of URL>.jpg. Re-render triggered 08:13 (Microsoft voice until quota resets).
- Never edit GO_LIVE.command while it runs (bash reads it as it goes). TODO when stopped: clean broll/ files older than 3 days.
- 08:30 Pronunciation fixes in tts.py normalize() (backup build/tts_v6_backup.py): ಡಾ.→ಡಾಕ್ಟರ್, ಪ್ರೊ.→ಪ್ರೊಫೆಸರ್; month
  abbreviations before a date (ಡಿ.4→ಡಿಸೆಂಬರ್ 4, ಜ./ಫೆ./…/ನ.); acronyms in Kannada letters read letter by letter
  (ಐಸಿಎಂಆರ್→ಐ ಸಿ ಎಂ ಆರ್, ಬಿಜೆಪಿಯ→ಬಿ ಜೆ ಪಿಯ, ಎಐ→ಎ ಐ, initials ಡಿ.ಕೆ.→ಡಿ ಕೆ); exceptions list ACR_KEEP (ಬಿಸಿ, ಸಿಡಿ…);
  ಸಿಎಂ/ಡಿಸಿಎಂ only as whole words; hyphens → spaces. Re-render triggered 08:30.
- 08:35 Promo: promo.py supports AI presenter clips promo_clips/presenter_1..4.mp4 (Gemini/Veo, man in navy suit) – uses the
  clip's own Kannada speech (rename *_vo.mp4 to use our TTS instead), "AI ನಿರೂಪಕ" label. Prompts: GEMINI_PRESENTER_PROMPTS.txt.
  Last promo segment now says "ಸಂಪೂರ್ಣವಾಗಿ ಎಐ ನಡೆಸುವ ಕನ್ನಡ ಸುದ್ದಿ ವಾಹಿನಿ"; bulletin footer: "ಸಂಪೂರ್ಣ AI ಸುದ್ದಿ ವಾಹಿನಿ • …".
  Backup build/promo_v1_backup.py. GO_LIVE rebuilds promo automatically when promo.py or a clip is newer than promo.mp4.
- 08:45 Tried Gemini Create video (Vijay's Pro account) for presenter clip 1: Gemini REFUSED ("can't make videos that could cause reputational risk or misrepresent current events") – AI news-anchor videos are blocked by Gemini's policy. Not retried with reworded prompts. Promo stays as is (Gemini b-roll clips + graphics + AI line).
- 08:50 make_bulletin.py: add_opener() – if opener/opener.mp4 exists, it is re-encoded to the bulletin format with
  "AI ನಿರೂಪಕ" label + logo and joined in front of every bulletin (tested). Backup build/make_bulletin_v7_backup.py.
  Vijay is making presenter clips in Gemini himself (Gemini refused Claude's attempt). NOTE: sed -i on this exFAT drive is
  unsafe (rename needs delete) – edit files with python read/write.
- 09:00 presenter_1.mp4 (Vijay's Gemini clip, 10 s, speech 1.3–6.8 s) copied from ~/Downloads into promo_clips/. Claude's opener attempt in the same Gemini chat was refused again; Vijay to make further clips himself.
- 09:00 New scheduled task "Vijay News – 11 AM greeting switch" (daily 11:01 IST): changes the leading ಶುಭೋದಯ in bulletin.json intro to ನಮಸ್ಕಾರ → GO_LIVE re-renders (cached voices, 1 new clip). Push only on failure.
- 09:10 End card: bulletin now ends with "A / VIJAY MELPAL / PRODUCTION" in big gold gradient letters (shine sweep, gold dust)
  with new signature music audio2/signature.wav (signature.py, C-major brass fanfare + bells). Old small grey line removed.
  Backup build/make_bulletin_v8_backup.py.
- 09:10 Vijay's Gemini clips: opener (speech 1.37–5.5 s) trimmed 0.9–6.6 s → opener/opener.mp4; promo clip 1 trimmed
  0.9–7.5 s → promo_clips/presenter_1.mp4. Originals stay in ~/Downloads (gemini_generated_video_639a3eda / _3fe05131).
  bulletin.json touched → re-render with opener + end card.
- 09:35 Claude tried promo clip 2 in Gemini (same chat): refused again. Vijay will make clips 2–4 himself; Claude downloads + trims from ~/Downloads.
- 13:45 Story mix now 11: 3 ರಾಜ್ಯ / 2 ರಾಷ್ಟ್ರೀಯ / 2 ಅಂತರರಾಷ್ಟ್ರೀಯ / 1 ಕ್ರೀಡೆ / 3 ಟೆಕ್ (morning + evening scheduled prompts updated; sports visuals: generic stadiums, no players/jerseys/logos; intro mentions ಕ್ರೀಡೆ).
- 13:55 Story mix now 12: 3/2/2/1 ಕ್ರೀಡೆ/1 ಸಿನಿಮಾ (unique film stories, no gossip/trailers)/3 ಟೆಕ್. Pacing: each headline held +2.0 s after it is read (VN_ROLL_HOLD), story title card 3.7 s (VN_STING, was 1.7) with music bed. Backup build/make_bulletin_v9_backup.py. 11 AM greeting switch ran OK (vijay_news_20261125_1112.mp4).
- 18:15 YouTube SEO (Vijay News channel UCU6Jmy4g_BcI4o7QvPehLdg – NOT "Victory Vijay", switch account first!):
  logo + banner uploaded (branding/), description (KN+EN, keywords), channel keywords (20), country India.
  Live stream T9umZz5ylSw: title "Kannada News LIVE 24x7 | ಕನ್ನಡ ನ್ಯೂಸ್ ಲೈವ್ | Karnataka & Bengaluru News | Vijay News",
  keyword description + hashtags, 19 tags, language Kannada, Altered content = Yes, custom thumbnail branding/live_thumb.jpg.
  Rename to "Vijay News Kannada" REJECTED by YouTube twice ("This name can't be used") – needs Vijay's choice of alternative.
- 18:00 Shorts: shorts.py makes shorts/short_<ts>.mp4 (1080x1920, ~30 s: story 1 + sports + cinema + tech, AI pictures, headline voices) at the end of every render (hook in make_bulletin.main). Scheduled task 'Vijay News – upload daily YouTube Short' 7:23 & 18:23 IST uploads the newest one via Chrome to Vijay News channel (checks it's not Victory Vijay), logs shorts/uploaded.txt.
- 18:20 Evening bulletin rendered in Puck (gemini) + first Short shorts/short_20261125_1805.mp4.
  New BEATS signature music (signature_beats.py → audio2/signature.wav; old brass kept as signature_brass.wav).
  make_bulletin.build_credit() now module-level (used by promo). Promo: new "100% AI / ಕನ್ನಡದ 100% AI ನ್ಯೂಸ್ ಚಾನೆಲ್" segment
  + gold Vijay Melpal Production card with beats at the end (backup build/promo_v2_backup.py). bulletin.json touched to re-render
  with the beats end card (voice clips cached → no Gemini requests).
- 18:30 Rename to 'Vijay News Kannada' refused a 3rd time (same generic toast). Likely the 2-changes-per-14-days limit (channel created ~23 Nov) – retry around 8–10 Dec, or try from the YouTube app.
- 18:35 Market wording: ಏರಿಕೆ/ಇಳಿಕೆ (not ಮೇಲೆ/ಕೆಳಗೆ) fixed in tonight's bulletin (stories 10, 12) → re-render; rule added to both scheduled prompts.
- 19:00 Special Shorts: put specials/<id>.json (id, header, script, story{tag,place,headline,stat,stat_label,broll_url}) → next render makes shorts/special_<id>.mp4 (Puck voice, marked <id>.done). Tulu film 'Pili Channe' (IFFI Goa world premiere, PIB) Short uploaded: https://youtube.com/shorts/k-6Hd6lctsA
- All Shorts now end with the gold VIJAY MELPAL PRODUCTION card + beats (shorts.py). Browser upload limit 3.8 MB → re-encode crf 27 before uploading.
- 19:25 'ಮತ್ತು' mispronounced by the voice: tts.SAY_INSTEAD speaks it as 'ಹಾಗೂ' (screen text unchanged) + native-pronunciation hint (dental double consonants) added to GEMINI_STYLE/BATCH_STYLE. Backup build/tts_v7_backup.py. Re-render triggered.
- 19:40 Vijay: keep ಮತ್ತು (SAY_INSTEAD emptied); dental 'math-thu', unstressed hint stays. From the next render.
- 21:40 Pronunciation hint: ತ/ದ dental (ಪಂದ್ಯ = pan-dhya, not pan-Da), only ಟ ಠ ಡ ಢ ಣ retroflex; no stress on dental clusters.
- 21:45 Hint extended to numbers with ತ್ತು (ಹತ್ತೊಂಬತ್ತು hath-thom-bath-thu etc.).
- 21:50 Promo voice-over now Google Puck (synth_batch, cached in build_promo) instead of Microsoft; Microsoft only as fallback. Backup build/promo_v3_backup.py. GO_LIVE rebuilds the promo at the next loop.
- 21:55 Vijay liked the Rahul Gandhi story voice (single-story request on gemini-2.5-flash-preview-tts). tts.py: primary model now 2.5-flash (then 3.1-flash, 2.5-pro); every story body is its own request (VN_BODY_GROUP=1), intro+headlines+outro one batch → ~13-15 requests per bulletin. Backup build/tts_v8_backup.py.
- 22:00 Presenter reel: promo.py plays every presenter_promos/*.mp4 (>20 KB) back-to-back at the start of the promo, trimmed to speech, AI label. Seeded with the opener (01_namaskara_swagata.mp4). New clips → touch promo.py so GO_LIVE rebuilds the promo (GO_LIVE only watches promo_clips/ and promo.py). Prompts A–E in GEMINI_PRESENTER_PROMPTS.txt.
- 22:10 Vijay: 'never ask for subscribe'. Removed from bulletin close slide (now 'ಪ್ರತಿದಿನ ಬೆಳಿಗ್ಗೆ ಮತ್ತು ಸಂಜೆ 6ಕ್ಕೆ'), spoken outro (make_bulletin strips subscribe/bell sentences even if the writer adds them), promo CTA ('24x7 ಕನ್ನಡ ನ್ಯೂಸ್ ಲೈವ್'), Shorts end card, presenter prompt E, YouTube channel + live descriptions. tts cache reuses clips recorded by any Puck model.

## 25 Nov 22:25 – X (x.com) updates added to bulletins
- Vijay asked: check x.com for India-level announcements by top politicians/influential people, police & traffic police updates, and the day's most-talked-about Bengaluru/Karnataka/India news on X.
- Both bulletin scheduled tasks (morning trig_01Uek6Zo8AkLgD7v799GUY2E, evening trig_01NvAKKwmFyAP1AuHt663QyR) now have STEP 2a: read official accounts via Claude in Chrome (fallback WebSearch), never sign in/post; at least one Bengaluru police/traffic update when real; "ಎಕ್ಸ್‌ನಲ್ಲಿ ಹೆಚ್ಚು ಚರ್ಚೆಯಾದ" only when confirmed by a reliable outlet; no invented view counts.
- Outro text in both prompts no longer has the subscribe line; "never ask to subscribe" rule added.
- Still pending: remove subscribe lines from YouTube channel description + live description (Chrome on Mac unresponsive at 22:20).

## 25 Nov ~23:00 – voice consistency + daily uploader + Mac restart
- make_bulletin.py/tts.py: if Puck quota runs out, keep Puck for all cached clips; drop stories without Puck, skip a missing intro/outro (silence); Microsoft only if < VN_MIN_PUCK_STORIES (7) stories have Puck. Backups build/*.bak_partial.
- yt_upload.py + SETUP_YOUTUBE_UPLOAD.command: YouTube Data API uploader (stdlib). Uploads day D's am/pm editions after D+1 06:00, started from make_bulletin.py __main__ (detached) when ~/.vijaynews_yt_token.json exists. Verifies channel UCU6Jmy4g_BcI4o7QvPehLdg. After both editions uploaded, deletes that day's videos (never newest/playlist). Log upload.log, record uploaded_videos.txt. Waiting for Vijay's Google Cloud OAuth client + setup.
- Mac restarted 22:5x; GO_LIVE not autostarted (no launchd.log). bulletin.json touched so the next start re-renders 25 Nov PM in Puck (outro skipped – quota).

## RULE (Vijay, 25 Nov 2026): Oracle Cloud must stay ₹0
- Only "Always Free-eligible" resources (VM.Standard.A1.Flex 2 OCPU / 12 GB). Never upgrade to Pay As You Go.
- Weekly scheduled task "Oracle Cloud ₹0 billing watch" (trig_018dFuycJkkmXni5HqEUWgha, Mondays 20:17 IST) checks Gmail for Oracle charges/budget alerts and pushes an alert.
- After the instance exists: create an Oracle Budget (Billing → Budgets) of ₹1 with an email alert at 1% actual spend.
