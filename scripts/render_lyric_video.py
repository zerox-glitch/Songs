#!/usr/bin/env python3
"""Render the supplied track as a 720p lyric video. Requires Pillow, NumPy, and imageio-ffmpeg."""
from __future__ import annotations
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "Keep the Fire Burning (Remastered).mp3"
OUTPUT = ROOT / "Keep the Fire Burning - Lyric Visualizer.mp4"
WIDTH, HEIGHT, FPS = 1280, 720, 24
DURATION = 224.832

# Approximate placements inferred from the arrangement; adjust if exact vocal timings are known.
LINES = [
    (13.0, 18.0, "VERSE 1", "The morning light is breaking in Lahore,"),
    (18.0, 23.0, "VERSE 1", "While midnight settles on your distant shore."),
    (23.0, 28.0, "VERSE 1", "I know you're pulling down the window blinds,"),
    (28.0, 33.0, "VERSE 1", "And leaving all the heavy day behind."),
    (33.0, 37.5, "VERSE 1", "I trace the little pixels on the screen,"),
    (37.5, 42.0, "VERSE 1", "The most beautiful face I've ever seen."),
    (44.0, 49.0, "PRE-CHORUS", "A half a world away, a different sky..."),
    (49.0, 54.0, "PRE-CHORUS", "But I can hear the softness in your sigh..."),
    (56.0, 61.5, "CHORUS", "I will keep the fire burning till you come back home!"),
    (61.5, 67.0, "CHORUS", "You never have to walk this heavy road alone!"),
    (67.0, 72.5, "CHORUS", "I carry every promise that we ever made!"),
    (72.5, 78.0, "CHORUS", "A quiet kind of love that never fades!"),
    (78.0, 82.0, "CHORUS", "Aaaahhh huh haaaa!"),
    (82.0, 86.0, "CHORUS", "Laaa la la laaaa!"),
    (91.0, 96.0, "VERSE 2", "I leave the phone right next to me in bed,"),
    (96.0, 101.0, "VERSE 2", "Just so I can hear you breathing deep."),
    (101.0, 106.0, "VERSE 2", "It closes up the thousands of miles,"),
    (106.0, 111.0, "VERSE 2", "To know I'm right beside you when you sleep."),
    (111.0, 116.0, "VERSE 2", "We share the day and pass the sun along,"),
    (116.0, 121.0, "VERSE 2", "You are the only place where I belong."),
    (123.0, 128.0, "PRE-CHORUS", "A half a world away, a different sky..."),
    (128.0, 133.0, "PRE-CHORUS", "But I can hear the softness in your sigh..."),
    (135.0, 140.5, "CHORUS", "I will keep the fire burning till you come back home!"),
    (140.5, 146.0, "CHORUS", "You never have to walk this heavy road alone!"),
    (146.0, 151.5, "CHORUS", "I carry every promise that we ever made!"),
    (151.5, 157.0, "CHORUS", "A quiet kind of love that never fades!"),
    (157.0, 161.0, "CHORUS", "Aaaahhh huh haaaa!"),
    (161.0, 165.0, "CHORUS", "Laaa la la laaaa!"),
    (165.0, 169.0, "CHORUS", "Aaaahhh huh haaaa!"),
    (174.0, 181.0, "BRIDGE", "I don't need a crowded room or fancy things..."),
    (181.0, 188.0, "BRIDGE", "I only need the peace your voice brings..."),
    (191.0, 197.5, "FINAL CHORUS", "I will keep the fire burning till you come back home!"),
    (197.5, 204.0, "FINAL CHORUS", "You never have to walk this heavy road alone!"),
    (204.0, 210.5, "FINAL CHORUS", "I carry every promise that we ever made!"),
    (210.5, 217.0, "FINAL CHORUS", "A quiet kind of love that never fades!"),
    (217.0, 220.5, "FINAL CHORUS", "Aaaahhh huh haaaa!"),
    (220.5, 222.5, "FINAL CHORUS", "Laaa la la laaaa!"),
    (222.5, 224.832, "OUTRO", "Come back home..."),
]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)

SERIF = ROOT / "assets" / "fonts" / "CormorantGaramond-SemiBold.ttf"
SERIF_ITALIC = ROOT / "assets" / "fonts" / "CormorantGaramond-MediumItalic.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SCENES = [
    (0.0, "dawn-lahore.jpg"), (43.0, "shoreline-dusk.jpg"),
    (88.0, "midnight-window.jpg"), (122.0, "dawn-lahore.jpg"),
    (155.0, "shoreline-dusk.jpg"), (173.0, "midnight-window.jpg"),
    (190.0, "dawn-lahore.jpg"),
]


def load_scenes() -> dict[str, Image.Image]:
    photos = {}
    for _, name in SCENES:
        if name not in photos:
            path = ROOT / "assets" / name
            photo = Image.open(path).convert("RGB")
            photo = ImageOps.fit(photo, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS, centering=(.5, .48))
            photo = ImageEnhance.Color(photo).enhance(.92)
            photo = ImageEnhance.Brightness(photo).enhance(.82)
            photo = ImageEnhance.Contrast(photo).enhance(1.05)
            photos[name] = photo
    return photos


def camera_frame(photo: Image.Image, t: float, scene_start: float, scene_end: float, scene_index: int) -> Image.Image:
    """Slow film-like push-in and lateral drift, with framing kept inside the source photo."""
    progress = min(1.0, max(0.0, (t - scene_start) / max(1.0, scene_end - scene_start)))
    zoom = 1.015 + .045 * progress
    scaled = photo.resize((int(WIDTH * zoom), int(HEIGHT * zoom)), Image.Resampling.LANCZOS)
    max_x, max_y = scaled.width - WIDTH, scaled.height - HEIGHT
    direction = 1 if scene_index % 2 == 0 else -1
    x = int(max_x * (.20 + .60 * progress)) if direction > 0 else int(max_x * (.80 - .60 * progress))
    y = int(max_y * (.35 + .25 * math.sin(progress * math.pi)))
    return scaled.crop((x, y, x + WIDTH, y + HEIGHT))


def scene_at(t: float, photos: dict[str, Image.Image]) -> Image.Image:
    index = max(i for i, (start, _) in enumerate(SCENES) if start <= t)
    start, name = SCENES[index]
    end = SCENES[index + 1][0] if index + 1 < len(SCENES) else DURATION
    current = camera_frame(photos[name], t, start, end, index)
    # Dissolve into the following cinematic still instead of cutting between scenes.
    fade_seconds = 3.2
    if index + 1 < len(SCENES) and t > end - fade_seconds:
        next_name = SCENES[index + 1][1]
        next_start = end
        next_end = SCENES[index + 2][0] if index + 2 < len(SCENES) else DURATION
        target = camera_frame(photos[next_name], t, next_start, next_end, index + 1)
        amount = min(1.0, max(0.0, (t - (end - fade_seconds)) / fade_seconds))
        return Image.blend(current, target, amount)
    return current


def wrap_lyric(text: str, lyric_font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words, rows, line = text.split(), [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if line and lyric_font.getlength(candidate) > max_width:
            rows.append(line)
            line = word
        else:
            line = candidate
    if line:
        rows.append(line)
    return rows


def srt_timestamp(sec: float) -> str:
    ms = int(round(sec * 1000))
    hh, ms = divmod(ms, 3_600_000)
    mm, ms = divmod(ms, 60_000)
    ss, ms = divmod(ms, 1000)
    return f"{hh:02}:{mm:02}:{ss:02},{ms:03}"


def write_lyrics_files() -> None:
    srt = []
    lrc = ["[ti:Keep the Fire Burning]", "[ar:Lyrics supplied by the artist/uploader]", "[length:03:44.832]", ""]
    for i, (start, end, _, text) in enumerate(LINES, 1):
        srt.extend([str(i), f"{srt_timestamp(start)} --> {srt_timestamp(end)}", text, ""])
        mm, ss = divmod(start, 60)
        lrc.append(f"[{int(mm):02}:{ss:05.2f}]{text}")
    (ROOT / "lyrics" / "Keep the Fire Burning.srt").write_text("\n".join(srt), encoding="utf-8")
    (ROOT / "lyrics" / "Keep the Fire Burning.lrc").write_text("\n".join(lrc) + "\n", encoding="utf-8")


def main() -> None:
    if not AUDIO.exists():
        raise SystemExit(f"Missing audio file: {AUDIO}")
    write_lyrics_files()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    # Decode a lightweight mono track to drive the visual pulse and waveform.
    decoded = subprocess.run([ffmpeg, "-v", "error", "-i", str(AUDIO), "-f", "f32le", "-ac", "1", "-ar", "12000", "pipe:1"], check=True, stdout=subprocess.PIPE).stdout
    samples = np.frombuffer(decoded, dtype=np.float32)
    samples_per_frame = 12000 / FPS
    rms = []
    for idx in range(math.ceil(DURATION * FPS)):
        a = int(idx * samples_per_frame)
        b = min(len(samples), int((idx + 1) * samples_per_frame))
        chunk = samples[a:b]
        rms.append(float(np.sqrt(np.mean(chunk * chunk))) if len(chunk) else 0.0)
    peak = max(rms) or 1
    levels = np.clip(np.array(rms) / peak, 0, 1)

    photos = load_scenes()
    small_font = font(SANS_BOLD, 15)
    title_font = font(SERIF, 94)
    title_italic = font(SERIF_ITALIC, 91)
    subtitle_font = font(SANS, 18)
    section_font = font(SANS_BOLD, 14)
    lyric_font = font(SERIF, 68)
    lyric_italic = font(SERIF_ITALIC, 68)
    total_frames = math.ceil(DURATION * FPS)
    out_cmd = [
        ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(FPS), "-i", "pipe:0",
        "-i", str(AUDIO), "-map", "0:v:0", "-map", "1:a:0", "-t", str(DURATION),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-metadata", "title=Keep the Fire Burning — Lyric Visualizer", "-metadata", "artist=", str(OUTPUT)
    ]
    encoder = subprocess.Popen(out_cmd, stdin=subprocess.PIPE)
    particles = [(float(x), float(y), float(phase), float(radius)) for x,y,phase,radius in zip(
        np.random.default_rng(7).uniform(80,1200,36), np.random.default_rng(8).uniform(80,610,36),
        np.random.default_rng(9).uniform(0,math.tau,36), np.random.default_rng(10).uniform(1.0,3.0,36))]
    line_index = 0
    for frame in range(total_frames):
        t = frame / FPS
        level = float(levels[frame])
        photo = scene_at(t, photos)
        frame_img = Image.alpha_composite(
            photo.convert("RGBA"), Image.new("RGBA", (WIDTH, HEIGHT), (4, 8, 20, 42))
        )
        d = ImageDraw.Draw(frame_img, "RGBA")

        # Elegant, restrained film-title framing.
        d.text((72, 54), "KEEP THE FIRE BURNING", font=small_font,
               fill=(255, 244, 229, 225), stroke_width=1, stroke_fill=(12, 15, 27, 120))
        d.line((72, 84, 194, 84), fill=(241, 201, 158, 185), width=2)
        d.text((WIDTH-72, 58), "A LOVE ACROSS EVERY MILE", font=small_font,
               fill=(255, 237, 218, 198), anchor="ra", stroke_width=1, stroke_fill=(12, 15, 27, 120))

        # A quiet, audio-reactive pulse lives below the lyrics, never through the words.
        mid_y = 635
        for j in range(42):
            x = 430 + j * 10
            envelope = .25 + .75 * math.sin(math.pi * (j + 1) / 43)
            pulse = abs(math.sin(j * .42 + t * 2.5))
            amp = 3 + 18 * level * envelope * pulse
            d.line((x, mid_y-amp, x, mid_y+amp), fill=(247, 215, 177, 35 + int(70*level)), width=2)
        d.line((424, mid_y, 856, mid_y), fill=(247, 215, 177, 45), width=1)

        current = None
        while line_index < len(LINES) and t >= LINES[line_index][1]:
            line_index += 1
        if line_index < len(LINES):
            st, en, section, lyric = LINES[line_index]
            if st <= t < en:
                fade = min((t-st)/.38, (en-t)/.35, 1.0)
                current = (section, lyric, max(0.0, fade))

        if current:
            section, lyric, fade = current
            alpha = max(0, min(255, int(255*fade)))
            # Central translucent lyric slate keeps the photo visible while giving type contrast.
            d.rounded_rectangle((92, 235, 1188, 490), radius=22,
                                fill=(5, 9, 21, int(164*fade)),
                                outline=(248, 220, 183, int(105*fade)), width=2)
            d.line((476, 277, 804, 277), fill=(241, 201, 158, int(205*fade)), width=2)
            d.ellipse((634, 272, 646, 284), fill=(255, 227, 188, int(220*fade)))
            d.text((WIDTH/2, 303), f"—  {section}  —", font=section_font,
                   fill=(246, 207, 163, int(alpha*.95)), anchor="mm")
            is_vocalise = lyric.startswith(("Aaa", "Laaa"))
            use_font = lyric_italic if is_vocalise else lyric_font
            rows = wrap_lyric(lyric, use_font, 1020)
            if len(rows) > 2:
                use_font = font(SERIF_ITALIC if is_vocalise else SERIF, 58)
                rows = wrap_lyric(lyric, use_font, 1020)
            text = "\n".join(rows)
            d.multiline_text((WIDTH/2+2, 376+5), text, font=use_font,
                             fill=(0, 0, 0, int(alpha*.68)), anchor="mm", align="center",
                             spacing=4, stroke_width=2, stroke_fill=(0, 0, 0, int(alpha*.60)))
            d.multiline_text((WIDTH/2, 376), text, font=use_font,
                             fill=(255, 248, 235, alpha), anchor="mm", align="center",
                             spacing=4, stroke_width=1, stroke_fill=(23, 21, 25, int(alpha*.85)))
            d.line((520, 454, 760, 454), fill=(241, 201, 158, int(125*fade)), width=1)
        elif t < 12:
            # Photographic title card with a high-fashion editorial serif treatment.
            d.rounded_rectangle((235, 205, 1045, 495), radius=26,
                                fill=(5, 9, 21, 128), outline=(248, 220, 183, 95), width=2)
            d.text((WIDTH/2, 310), "Keep the Fire", font=title_font,
                   fill=(255, 246, 232, 245), anchor="mm", stroke_width=2, stroke_fill=(25, 19, 21, 180))
            d.text((WIDTH/2, 391), "Burning", font=title_italic,
                   fill=(248, 211, 171, 250), anchor="mm", stroke_width=2, stroke_fill=(25, 19, 21, 180))
            d.line((480, 438, 800, 438), fill=(241, 201, 158, 185), width=2)
            d.text((WIDTH/2, 466), "A LOVE ACROSS EVERY MILE", font=subtitle_font,
                   fill=(255, 235, 214, 225), anchor="mm")
        d.text((72, HEIGHT-35), "LAHORE  ·  MIDNIGHT  ·  HOME", font=small_font,
               fill=(255, 240, 222, 185), stroke_width=1, stroke_fill=(12, 15, 27, 120))
        d.text((WIDTH-72, HEIGHT-35), "LYRIC FILM", font=small_font,
               fill=(255, 240, 222, 185), anchor="ra", stroke_width=1, stroke_fill=(12, 15, 27, 120))
        try:
            encoder.stdin.write(frame_img.convert("RGB").tobytes())
        except BrokenPipeError:
            raise RuntimeError("FFmpeg stopped while encoding; inspect the ffmpeg installation.")
        if frame and frame % (FPS*20) == 0:
            print(f"Rendered {t:0.0f}s / {DURATION:.0f}s", flush=True)
    encoder.stdin.close()
    code = encoder.wait()
    if code:
        raise SystemExit(f"FFmpeg encoding failed with exit code {code}")
    print(f"Created {OUTPUT} ({OUTPUT.stat().st_size/1_000_000:.1f} MB)")

if __name__ == "__main__":
    main()
