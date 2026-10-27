#!/usr/bin/env python3
"""Render the supplied track as a 720p lyric video. Requires Pillow, NumPy, and imageio-ffmpeg."""
from __future__ import annotations
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "Keep the Fire Burning (Remastered).mp3"
OUTPUT = ROOT / "Keep the Fire Burning - Lyric Visualizer.mp4"
WIDTH, HEIGHT, FPS = 1280, 720, 12
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

SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def make_backdrop() -> Image.Image:
    # Painterly two-world dusk: Lahore's amber dawn meets a deep, blue midnight.
    w, h = 640, 360
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    left = np.array([197, 104, 71], np.float32)
    right = np.array([24, 37, 84], np.float32)
    mix = np.clip((u - 0.28) / 0.72, 0, 1)[..., None]
    base = left * (1 - mix) + right * mix
    glow1 = np.exp(-(((u - .13) / .42) ** 2 + ((v - .39) / .52) ** 2) * 2.0)[..., None]
    glow2 = np.exp(-(((u - .82) / .48) ** 2 + ((v - .22) / .52) ** 2) * 2.2)[..., None]
    base += glow1 * np.array([53, 35, 14]) + glow2 * np.array([12, 22, 48])
    base -= (v ** 1.7)[..., None] * np.array([56, 46, 33])
    im = Image.fromarray(np.uint8(np.clip(base, 0, 255))).resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    # Horizon glow and distant ridge.
    d.ellipse((-170, 384, 580, 720), fill=(239, 176, 110, 26))
    d.ellipse((730, 390, 1510, 730), fill=(85, 113, 186, 24))
    d.line([(0, 510), (210, 483), (430, 515), (655, 500), (870, 520), (1060, 489), (1280, 504)], fill=(255, 204, 143, 58), width=2)
    # Stylized skyline: minarets and low rooftops, silhouetted at the bottom.
    d.polygon([(0,590),(80,578),(112,585),(150,550),(188,575),(224,563),(252,585),(290,568),(328,590),(385,578),(420,590),(480,570),(530,588),(585,560),(640,590),(700,575),(740,590),(790,566),(825,585),(880,572),(920,590),(968,555),(1007,580),(1045,570),(1090,592),(1150,566),(1188,581),(1224,562),(1280,580),(1280,720),(0,720)], fill=(13,20,41,172))
    # iconic minaret silhouettes
    for x, scale in [(190,1.0),(606,.74),(1080,.9)]:
        d.rectangle((x-10*scale, 476, x+10*scale, 596), fill=(13,20,41,205))
        d.polygon([(x-19*scale,480),(x,452),(x+19*scale,480)], fill=(13,20,41,205))
        d.line((x,455,x,432), fill=(13,20,41,205), width=max(2,int(3*scale)))
        d.ellipse((x-3*scale,428,x+3*scale,434), fill=(13,20,41,215))
        d.line((x-16*scale,505,x+16*scale,505), fill=(231,176,124,80), width=2)
    # Warm light trail joins both horizons.
    d.arc((105, 358, 1200, 720), 190, 350, fill=(255,206,147,74), width=3)
    # A sparse, stable star field.
    rng = np.random.default_rng(19)
    for x,y,r in zip(rng.integers(20,1260,90),rng.integers(25,470,90),rng.choice([1,1,2],90)):
        alpha=int(rng.integers(40,130))
        d.ellipse((int(x-r),int(y-r),int(x+r),int(y+r)),fill=(255,232,194,alpha))
    return im


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

    base = make_backdrop()
    small_font = font(SANS_BOLD, 17)
    title_font = font(SERIF_BOLD, 57)
    subtitle_font = font(SANS, 20)
    lyric_font = font(SERIF, 33)
    lyric_small = font(SERIF, 27)
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
        level = levels[frame]
        img = base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        # Breathing halo, concentric rings, and floating lights.
        cx, cy = 640, 384
        radius = 102 + 14 * math.sin(t * 1.05) + 23 * float(level)
        d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius), outline=(255,205,147,24+int(20*level)), width=2)
        radius2 = radius + 24 + 8*math.sin(t*.62)
        d.ellipse((cx-radius2,cy-radius2,cx+radius2,cy+radius2), outline=(200,218,255,15+int(10*level)), width=1)
        for x,y,phase,r in particles:
            yy = y + 13*math.sin(t*.48+phase)
            xx = x + 12*math.cos(t*.25+phase)
            a = int(35 + 95*(.5+.5*math.sin(t*1.1+phase)))
            d.ellipse((xx-r,yy-r,xx+r,yy+r), fill=(255,218,173,a))
        # A gentle audio-reactive waveform across the central light bridge.
        mid_y = 397
        points = []
        for j in range(121):
            x = 220 + j * 7
            envelope = math.exp(-((j-60)/43)**2)
            wave = math.sin(j*.34-t*2.2)*(.17+.83*level) + .38*math.sin(j*.13+t*.85)
            points.append((x, mid_y + wave * 58 * envelope))
        d.line(points, fill=(255,220,174,125), width=2)
        for j in range(56):
            x = 350 + j*10
            amp = (8 + 36*level) * (0.25 + .75*abs(math.sin(j*.19+t*.72)))
            d.line((x, mid_y-amp, x, mid_y+amp), fill=(255,218,175,42+int(88*level)), width=2)

        # Brand/title always present, restrained like a cinematic lyric film.
        d.text((72,58), "A DISTANCE MADE SMALL", font=small_font, fill=(255,220,183,210), stroke_width=0)
        d.line((72,89,180,89), fill=(255,205,147,125), width=2)
        current = None
        while line_index < len(LINES) and t >= LINES[line_index][1]:
            line_index += 1
        if line_index < len(LINES):
            st, en, section, lyric = LINES[line_index]
            if st <= t < en:
                current = (section, lyric, min((t-st)/.55, (en-t)/.45, 1.0))
        if current:
            section, lyric, fade = current
            alpha = max(0, min(255, int(255*fade)))
            sf = small_font
            box = d.textbbox((0,0), section, font=sf)
            d.text(((WIDTH-(box[2]-box[0]))/2, 522), section, font=sf, fill=(255,215,168,int(alpha*.85)))
            use_font = lyric_font if len(lyric) <= 48 else lyric_small
            box = d.textbbox((0,0), lyric, font=use_font, stroke_width=1)
            x = (WIDTH - (box[2]-box[0])) / 2
            d.rounded_rectangle((90, 556, 1190, 644), radius=18, fill=(8,13,31,int(alpha*.36)), outline=(255,222,184,int(alpha*.12)), width=1)
            d.text((x, 576), lyric, font=use_font, fill=(255,249,236,alpha), anchor=None, stroke_width=1, stroke_fill=(22,23,39,int(alpha*.8)))
        elif t < 12:
            # Opening title card
            title = "Keep the Fire\nBurning"
            d.multiline_text((WIDTH/2, 260), title, font=title_font, fill=(255,243,223,238), anchor="mm", align="center", spacing=5, stroke_width=1, stroke_fill=(66,38,38,140))
            d.text((WIDTH/2, 387), "A LOVE THAT CROSSES EVERY MILE", font=subtitle_font, fill=(255,220,183,220), anchor="mm")
        # Persistent small song title.
        d.text((72, HEIGHT-48), "KEEP THE FIRE BURNING", font=small_font, fill=(247,225,202,140))
        d.text((WIDTH-72, HEIGHT-48), "LYRIC VISUALIZER", font=small_font, fill=(247,225,202,140), anchor="ra")
        try:
            encoder.stdin.write(img.tobytes())
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
