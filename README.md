# Keep the Fire Burning

A YouTube-ready lyric video and a lightweight, interactive audio-reactive visualizer for the uploaded song.

## Deliverables

- **`Keep the Fire Burning - Lyric Visualizer.mp4`** — 1280×720 H.264/AAC lyric video, ready to upload to YouTube.
- **`YouTube Thumbnail.jpg`** — 1280×720 still from the video for the YouTube thumbnail.
- **`YouTube upload info.txt`** — suggested title, description, hashtags, and timing note.
- **`lyrics/Keep the Fire Burning.txt`** — clean lyrics transcript.
- **`lyrics/Keep the Fire Burning.srt`** — subtitles used as the video's on-screen lyric cues.
- **`lyrics/Keep the Fire Burning.lrc`** — timestamped lyrics for compatible music players.
- **`visualizer/`** — self-contained WebGL visualizer with playback controls, audio-reactive background, and lyrics.
- **`scripts/render_lyric_video.py`** — reproducible video renderer.

## Preview the interactive visualizer

From the repository root, start a small static web server:

```sh
python3 -m http.server 8000
```

Then open `http://localhost:8000/visualizer/`. Press play to hear the included MP3 and see the WebGL scene react to the audio. (Browsers generally block audio playback when opening the HTML directly as a `file://` URL.)

## Re-render the MP4

Python 3.10+ is recommended. Install the renderer's dependencies in a virtual environment, then run:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/render_lyric_video.py
```

The renderer reads the MP3 in the repository root and regenerates the MP4 plus the SRT/LRC lyric files. The lyric placements in the MP4 and timecoded files are **estimated from the supplied song structure**, not verified against a vocal stem; adjust the timestamps in `scripts/render_lyric_video.py` if frame-accurate karaoke timing is needed.
