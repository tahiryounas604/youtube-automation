# youtube-automation

A Python pipeline for a faceless YouTube channel: write a narration script
from a topic outline, generate a voiceover, assemble a 720p video with
ffmpeg, make a thumbnail, generate SEO metadata, upload via the YouTube
Data API v3, and schedule videos in a JSON queue.

Part of the [Tytechlabs](https://www.linkedin.com/in/tahiryounas604)
open-source line. License: GPL-3.0.

## Features

- **Script builder** — assembles a narration script from a topic + outline
  (headings + bullet points) using templates. No paid AI; see
  `src/youtube_automation/script_builder.py` for how to plug in an LLM later.
  Also builds timed captions for burned-in subtitles.
- **Voiceover** — Piper TTS when installed (`--model voice.onnx`); otherwise
  generates a **timed silent track** of the exact spoken length and says so
  honestly in its output. Never presented as real speech.
- **Video assembly** — ffmpeg Ken Burns slow-zoom over slides, burned-in
  captions, voiceover mixed in, 1280x720, H.264 + AAC.
- **Thumbnails** — 1280x720 PNG via Pillow: gradient background, wrapped
  bold title, accent bar, optional subtitle.
- **Metadata / SEO** — three title variants (≤100 chars), description with
  section list, tags from topic + headings (≤500 chars total), category
  Education.
- **Uploader** — YouTube Data API v3 resumable upload (OAuth 2.0).
  Uploads private by default. See "Upload setup".
- **Scheduler queue** — JSON file: schedule videos, list them, mark
  done/failed, list what's due.

## Install

Requires Python 3.10+, ffmpeg (with ffprobe), and Pillow.

```bash
sudo apt-get install -y ffmpeg
pip install --break-system-packages -r requirements.txt
pip install --break-system-packages pytest   # to run the tests
```

Optional, only for `upload`:

```bash
pip install --break-system-packages google-api-python-client google-auth-oauthlib google-auth-httplib2
```

Optional, for real voiceover instead of a silent track: install
[Piper TTS](https://github.com/rhasspy/piper) and download a voice model
(`.onnx`).

## Usage

All commands run from this directory as `python3 -m youtube_automation ...`
(or `youtube-automation ...` after `pip install -e .`).

```bash
# 1. Write an outline (see examples/topic_outline.json), then build the script
python3 -m youtube_automation script examples/topic_outline.json -o script.json

# 2. Voiceover (Piper if available, else a timed silent track)
python3 -m youtube_automation voice script.json -o voiceover.wav
python3 -m youtube_automation voice script.json -o voiceover.wav --model en_US-amy-medium.onnx

# 3. Thumbnail + metadata
python3 -m youtube_automation thumb "How DNS Works" -o thumbnail.png --subtitle "Explained Simply"
python3 -m youtube_automation meta "How DNS Works" --script script.json -o metadata.json

# 4. Assemble the video (slides are made by the pipeline; own photos work too)
python3 -m youtube_automation assemble slide_1.png slide_2.png -o video.mp4 \
    --audio voiceover.wav --captions captions.json

# 5. Or run everything at once
python3 -m youtube_automation pipeline examples/topic_outline.json -o output
python3 -m youtube_automation pipeline examples/topic_outline.json -o output \
    --schedule 2026-11-13T10:00:00Z

# 6. Queue
python3 -m youtube_automation queue --queue queue.json list
python3 -m youtube_automation queue --queue queue.json due
python3 -m youtube_automation queue --queue queue.json done --id <id>

# 7. Upload (see setup below)
python3 -m youtube_automation upload video.mp4 --title "How DNS Works Explained Simply" \
    --description "..." --tags dns networking --privacy private
```

## Upload setup

1. In [Google Cloud Console](https://console.cloud.google.com/), create a
   project, enable the **YouTube Data API v3**, and create **OAuth 2.0
   credentials (Desktop app)**.
2. Download the client JSON and save it as `client_secrets.json` in the
   directory you run the upload from. **Never commit this file, and never
   commit `token.json`** (created on first sign-in).
3. Run the `upload` command; a browser window opens once for Google sign-in.
   Uploads default to **private** — publish manually after review.

## Tests

```bash
python3 -m pytest -v
```

36 tests: script builder, captions, metadata, thumbnails, voiceover
(silent-track timing), video assembly (including a real 2-second ffmpeg
clip, probed with ffprobe), queue logic, uploader guards, and a full
CLI pipeline run. All 36 pass.

## Honest limits

- **Live upload NOT tested.** The upload code path is real (Google API
  client, resumable upload), but no upload to a real YouTube channel has
  been performed — it needs the creator's own OAuth credentials and channel.
  `upload` fails fast with a clear error when credentials or the client
  library are missing; nothing is uploaded silently.
- **Voiceover is silent unless Piper is installed.** Without Piper + a voice
  model, `voice` produces a timed silent WAV. The output always states
  which engine was used.
- **Scripts are template-assembled, not AI-written.** Quality depends on
  the outline you write. An LLM plug-in point is documented in
  `script_builder.py`.
- **Slides are title cards, not footage.** The pipeline renders heading
  slides with a Ken Burns zoom; use your own photos/video as slides for
  richer visuals (pass image paths to `assemble`).
- **No YouTube policy compliance checking.** The tool does not check
  copyright, monetisation, or community-guideline rules — that is the
  creator's responsibility.
- **CI is not verified on GitHub yet.** `.github/workflows/ci.yml` runs the
  tests on push, but no run has happened until the repo is created and
  pushed.

## Project layout

```
src/youtube_automation/
  script_builder.py   narration + captions from topic/outline
  voiceover.py        Piper TTS or timed silent WAV
  video.py            slides + ffmpeg Ken Burns assembly (720p)
  thumbnail.py        1280x720 Pillow thumbnails
  metadata.py         titles / description / tags
  uploader.py         YouTube Data API v3 upload
  queue.py            JSON scheduling queue
  cli.py              argparse CLI (script/voice/thumb/meta/assemble/queue/upload/pipeline)
examples/topic_outline.json
tests/                pytest suite (36 tests)
```

Built by Tahir Younas — Penetration Tester & Application Security Engineer — https://www.linkedin.com/in/tahiryounas604 | Tytechlabs
