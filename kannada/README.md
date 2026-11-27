# Vijay News KANNADA – cloud version (no Mac needed)

Same programs as the Mac folder `/Volumes/One Touch/VijayNews/vijay-news/` (copied 27 Nov 2026, 17:40 IST).

- **Scheduled bulletin task** writes `kannada/bulletin.json` (+ archive copy in `kannada/archive/`) and pushes to `main`.
  Pictures it makes itself (Canva AI pictures, official logos) go to `kannada/pictures/` and are referenced as `"pictures/<file>.jpg"`.
- **GitHub Actions "Kannada bulletin render"** (`.github/workflows/kannada-render.yml`) renders it and publishes
  `bulletin.mp4`, `promo.mp4`, `short_1..5.mp4`, `status.txt` to the release **kannada-live**.
- **Oracle Always Free micro server** (vijay-news-stream, 129.225.114.117) runs `server/stream.sh kannada`
  and relays the newest bulletin + promo to YouTube 24x7 without re-encoding.
- Keys live only in GitHub secrets (`GEMINI_KEY` = Puck voice, `PIXABAY_KEY`) and on the server (`~/.vijaynews_streamkey`).
- English channel = `english/` folder; never mix the two.
