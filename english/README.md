# Vijay News ENGLISH (@VijayNewsEnglish) – runs fully in the cloud, ₹0

Kept completely separate from the Kannada channel (repo root / Vijay's Mac).

1. **Script** – the scheduled task "Vijay News ENGLISH – morning & evening bulletin" (7:21 AM / 6:21 PM IST) researches
   the news (instructions: `TASK_PROMPT.md`) and pushes `english/bulletin.json` (+ `english/archive/`).
2. **Video** – GitHub Actions workflow `.github/workflows/english-render.yml` (free for public repos) renders it with
   `make_bulletin.py` (Microsoft Indian-English voice `en-IN-PrabhatNeural`, or Google Gemini if the secret
   `GEMINI_EN_KEY` is set; free Pixabay clips with the secret `PIXABAY_KEY`) and publishes to release **english-live**:
   `bulletin.mp4`, `promo.mp4`, `short_1..4.mp4`, `status.txt`.
3. **Live 24x7** – a free Oracle "Always Free" micro server runs `server/stream.sh english`: it downloads the newest
   bulletin + promo and relays them to YouTube without re-encoding. Set up with `server/stream_setup.sh english`,
   stream key typed by Vijay with `server/stream_keys.sh english` (never stored in git).

Secrets (GitHub → Settings → Secrets and variables → Actions): `PIXABAY_KEY` (same free key as the Kannada channel),
optional `GEMINI_EN_KEY` (a second free Google AI Studio key from a NEW Google Cloud project, so the Kannada
channel's free voice quota is not shared).
