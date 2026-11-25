# Vijay News – bulletin generator (A Vijaymelpal Production)

Makes a finished Kannada news bulletin MP4: opening title + theme music, headline list,
a "sting" sound + transition before every headline, story cards with ticker, closing card + theme.
All music is synthesised from scratch (no copyright claims).

## One-time setup on Mac
```bash
brew install ffmpeg fribidi harfbuzz python
cd vijay-news
python3 -m venv .venv && source .venv/bin/activate
pip install pillow numpy scipy edge-tts
python3 music.py audio          # regenerates the music cues (already included)
```

## Make a bulletin
1. Edit `bulletin.json` (intro, outro, 5 stories: headline, spoken body, facts, stat, source).
2. Run:
```bash
python3 make_bulletin.py bulletin.json vijay_news_$(date +%Y%m%d_%H%M).mp4
```
Voice: uses the Microsoft neural Kannada voice via edge-tts (`kn-IN-SapnaNeural`, female).
For the male voice: `VN_VOICE=kn-IN-GaganNeural python3 make_bulletin.py ...`
If edge-tts can't connect it falls back to espeak-ng (robotic; `brew install espeak-ng`).

## Rules this channel follows
- Facts gathered from several outlets, script written fresh; no clips, audio or graphics from other channels.
- No photorealistic AI images of real events or real people. Graphics are clearly illustrative.
- Each card shows its source; the "AI ಧ್ವನಿ" label stays on screen.
- On upload: YouTube Studio → Details → "Altered content": answer honestly (a realistic synthetic voice → Yes is the safe choice).

## AI presenter (HeyGen)
1. Sign in at heygen.com (vijaymelpal@gmail.com). A paid plan gives 1080p with no watermark.
2. For each block in `HEYGEN_SCRIPTS.txt` (7 blocks), create a new video:
   - Size 16:9 (landscape), 1080p.
   - Avatar: a formal, news-style presenter from HeyGen's library (don't use a real person's face without their consent).
   - Background: solid colour **#00FF00** (bright green).
   - Script: paste the block's Kannada text. Voice: filter by language **Kannada** and pick a native voice. Use the same avatar and voice for all 7.
3. Download each video and name it exactly as shown: intro.mp4, s0.mp4 … s4.mp4, outro.mp4
4. Put all 7 files in the `anchor` folder next to this README, then run MAKE_BULLETIN.command.
   The presenter is cut out of the green background and placed in the studio; the voice comes from the clips.
   If HeyGen gives you a transparent .webm instead, that works too (same names, .webm).
On YouTube upload: Altered content → **Yes** (realistic AI presenter).
