# Keep the Fire Burning

A cinematic lyric film, a matching interactive visualizer, and upload assets for the supplied song.

## Deliverables

- **`Keep the Fire Burning - Lyric Visualizer.mp4`** — 3840×2160 (4K), 30 fps H.264/AAC export; lyric/title type is rendered at full output resolution.
- **`YouTube Thumbnail.jpg`** — 1280×720 title-frame thumbnail.
- **`YouTube upload info.txt`** — suggested upload title, description, and notes.
- **`lyrics/Keep the Fire Burning.txt`** — clean lyrics transcript.
- **`lyrics/Keep the Fire Burning.srt`** and **`.lrc`** — lyric subtitle/timecode sidecars.
- **`visualizer/`** — self-contained WebGL player with audio-reactive ribbons, scene transitions, title, and centered lyrics.
- **`assets/`** — new no-human cosmic title, dual-horizon Lahore, gold-cloud infinity, and moonlit-garden scenes; local Allura and Cormorant Garamond fonts with their OFL licenses.
- **`scripts/render_lyric_video.py`** — reproducible 4K renderer with audio feature analysis for ribbons, ripples, and particles.

The video itself contains only the song title during the opening, then one or two supplied lyric lines at a time; it contains no people, labels, credits, or added captions. It fades to black at the end.

## Preview the interactive visualizer

From the repository root:

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000/visualizer/` and press play.

## Re-render

Python 3.10+ is recommended:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/render_lyric_video.py
```

The renderer analyzes the original audio for amplitude, spectral onsets, low-band pulses, and a violin-range pitch contour; these drive the animated lighting and ribbons. **Lyric cue times are still provisional phrase-level cues, not forced-aligned word timestamps.** This environment has no speech-alignment model, so the exact sung-word timing must be supplied or verified before claiming karaoke-level synchronization.
