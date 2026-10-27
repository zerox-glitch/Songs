#!/usr/bin/env python3
"""Render a 4K cinematic lyric film with audio-reactive procedural art.
Requires Pillow, NumPy, and imageio-ffmpeg. The uploaded MP3 remains the audio source.
"""
from __future__ import annotations
import json
import math
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "Keep the Fire Burning (Remastered).mp3"
OUTPUT = ROOT / "Keep the Fire Burning - Lyric Visualizer.mp4"
ASS_PATH = ROOT / "lyrics" / "lyrics.ass"
TIMELINE_PATH = ROOT / "lyrics" / "timeline.json"
WIDTH, HEIGHT, FPS = 1280, 720, 30
OUT_WIDTH, OUT_HEIGHT, OUT_FPS = 3840, 2160, 30
TIMELINE = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
DURATION = float(TIMELINE["duration"])
LINES = [(float(item["start"]), float(item["end"]), item["text"]) for item in TIMELINE["lyrics"]]

# The shared JSON timeline keeps scene cuts identical in the exported film and web player.
SCENES = [(float(item["start"]), item["image"], item["mode"]) for item in TIMELINE["scenes"]]
FONT_SERIF = ROOT / "assets/fonts/CormorantGaramond-SemiBold.ttf"
FONT_SCRIPT = ROOT / "assets/fonts/Allura-Regular.ttf"
# Each row stays verbatim, while one emotional phrase is set in gold calligraphy.
EMPHASIS = {
    "The morning light is breaking in Lahore,": ("The morning light", "is breaking in Lahore,"),
    "While midnight settles on your distant shore.": ("While midnight settles", "on your distant shore."),
    "I know you're pulling down the window blinds,": ("I know you're pulling down", "the window blinds,"),
    "And leaving all the heavy day behind.": ("And leaving all the", "heavy day behind."),
    "I trace the little pixels on the screen,": ("I trace the little", "pixels on the screen,"),
    "The most beautiful face I've ever seen.": ("The most beautiful", "face I've ever seen."),
    "A half a world away, a different sky...": ("A half a world away,", "a different sky..."),
    "But I can hear the softness in your sigh...": ("But I can hear the", "softness in your sigh..."),
    "I will keep the fire burning till you come back home!": ("I WILL KEEP THE FIRE BURNING", "TILL YOU COME BACK HOME!"),
    "You never have to walk this heavy road alone!": ("YOU NEVER HAVE TO WALK THIS", "HEAVY ROAD ALONE!"),
    "I carry every promise that we ever made!": ("I CARRY EVERY PROMISE", "THAT WE EVER MADE!"),
    "A quiet kind of love that never fades!": ("A QUIET KIND OF LOVE", "THAT NEVER FADES!"),
    "I leave the phone right next to me in bed,": ("I leave the phone right", "next to me in bed,"),
    "Just so I can hear you breathing deep.": ("Just so I can hear you", "breathing deep."),
    "It closes up the thousands of miles,": ("It closes up the", "thousands of miles,"),
    "To know I'm right beside you when you sleep.": ("To know I'm right beside", "you when you sleep."),
    "We share the day and pass the sun along,": ("We share the day and", "pass the sun along,"),
    "You are the only place where I belong.": ("You are the only place", "where I belong."),
    "I don't need a crowded room or fancy things...": ("I don't need a crowded room", "or fancy things..."),
    "I only need the peace your voice brings...": ("I only need the", "peace your voice brings..."),
}
VOCALISES = {"Aaaahhh huh haaaa!", "Laaa la la laaaa!", "Come back home..."}


def ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, r = divmod(cs, 360000); m, r = divmod(r, 6000); s, cs = divmod(r, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000); m, ms = divmod(ms, 60_000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def wrap_balanced(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    if fnt.getlength(text) <= max_width:
        return [text]
    words = text.split()
    candidates = []
    for i in range(1, len(words)):
        left, right = " ".join(words[:i]), " ".join(words[i:])
        lw, rw = fnt.getlength(left), fnt.getlength(right)
        if max(lw, rw) <= max_width:
            candidates.append((abs(lw-rw) + .08*max(lw,rw), left, right))
    if candidates:
        _, left, right = min(candidates)
        return [left, right]
    # Keep all text visible if an unusually long line requires a third row.
    rows, line = [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if line and fnt.getlength(candidate) > max_width:
            rows.append(line); line = word
        else:
            line = candidate
    if line: rows.append(line)
    return rows


def font_size_to_fit(text: str, font_path: Path, start: int, max_width: int = 2860, min_size: int = 170) -> int:
    size = start
    while size > min_size and ImageFont.truetype(str(font_path), size).getlength(text) > max_width:
        size -= 8
    return size


def write_subtitles() -> None:
    srt = []
    for i, (start, end, lyric) in enumerate(LINES, 1):
        srt.extend((str(i), f"{srt_time(start)} --> {srt_time(end)}", lyric, ""))
    (ROOT / "lyrics" / "Keep the Fire Burning.srt").write_text("\n".join(srt), encoding="utf-8")
    lrc = ["[ti:Keep the Fire Burning]", "[length:03:44.832]", ""]
    for start, _, lyric in LINES:
        m, s = divmod(start, 60)
        lrc.append(f"[{int(m):02}:{s:05.2f}]{lyric}")
    (ROOT / "lyrics" / "Keep the Fire Burning.lrc").write_text("\n".join(lrc)+"\n", encoding="utf-8")

    ass = [
        "[Script Info]", "ScriptType: v4.00+", "WrapStyle: 2", "ScaledBorderAndShadow: yes",
        f"PlayResX: {OUT_WIDTH}", f"PlayResY: {OUT_HEIGHT}", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Lyrics,Cormorant Garamond Light SemiBold,360,&HE5F4FF,&H00A1D7F4,&HC8071326,&H00000000,0,0,0,0,100,100,0,0,1,4,6,5,220,220,160,1",
        "Style: Title,Allura,450,&H0038DFFF,&H00A1D7F4,&HAA100704,&H00000000,0,0,0,0,100,100,1,0,1,3,8,5,160,160,260,1", "",
        "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        # The title is the only opening text; it gracefully gathers and dissolves.
        f"Dialogue: 1,{ass_time(0)},{ass_time(12)},Title,,0,0,0,,{{\\an5\\move(1920,1140,1920,1040,0,2600)\\blur2.5\\fad(1300,1900)\\t(0,1400,\\blur0\\fscx105\\fscy105)}}Keep the Fire Burning",
    ]
    for index, (start, end, text) in enumerate(LINES):
        first_lyric = index == 0
        chorus = any(a <= start < b for a,b in ((56,87),(135,170),(191,222.5)))
        bridge = 174 <= start < 190
        if text in VOCALISES:
            size = font_size_to_fit(text, FONT_SCRIPT, 470, 3000)
            escaped = f"{{\\fnAllura\\fs{size}\\1c&H0038DFFF&\\bord2\\shad8}}{text}"
        else:
            plain, script = EMPHASIS[text]
            if not first_lyric and chorus:
                plain, script = plain.upper(), script.upper()
            normal_start = 330 if chorus else (300 if bridge else 360)
            script_start = 340 if chorus else (320 if bridge else 350)
            normal_size = font_size_to_fit(plain, FONT_SERIF, normal_start, 2860)
            script_size = 450 if first_lyric else font_size_to_fit(script, FONT_SCRIPT, script_start, 2860)
            if first_lyric:
                escaped = (f"{{\\fnAllura\\fs{script_size}\\1c&H0038DFFF&\\bord2\\shad8}}{plain}"
                           f"\\N{{\\rLyrics\\fs{normal_size}}}{script}")
            else:
                escaped = (f"{{\\rLyrics\\fs{normal_size}}}{plain}"
                           f"\\N{{\\fnAllura\\fs{script_size}\\1c&H0038DFFF&\\bord2\\shad8}}{script}")
        if bridge:
            escaped = "{\\i1}" + escaped
        tags = (f"{{\\an5\\pos(1920,1080)\\blur2.0\\bord5\\shad8"
                f"\\fad(420,420)\\t(0,400,\\blur0.2)}}")
        ass.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Lyrics,,0,0,0,,{tags}{escaped}")
    ASS_PATH.write_text("\n".join(ass)+"\n", encoding="utf-8")


def load_scenes() -> dict[str, Image.Image]:
    photos = {}
    for _, name, _ in SCENES:
        if name not in photos:
            image = Image.open(ROOT / "assets" / name).convert("RGB")
            image = ImageOps.fit(image, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS, centering=(.5,.48))
            image = ImageEnhance.Color(image).enhance(1.10)
            image = ImageEnhance.Contrast(image).enhance(1.07)
            photos[name] = image
    return photos


def camera_frame(photo: Image.Image, t: float, scene_start: float, scene_end: float, index: int) -> Image.Image:
    progress = min(1.0, max(0.0, (t-scene_start)/max(1.0,scene_end-scene_start)))
    zoom = 1.01 + .045*progress
    image = photo.resize((int(WIDTH*zoom), int(HEIGHT*zoom)), Image.Resampling.LANCZOS)
    mx, my = image.width-WIDTH, image.height-HEIGHT
    direction = 1 if index%2 == 0 else -1
    x = int(mx*(.18+.64*progress)) if direction>0 else int(mx*(.82-.64*progress))
    y = int(my*(.30+.35*math.sin(progress*math.pi)))
    return image.crop((x,y,x+WIDTH,y+HEIGHT))


def scene_at(t: float, photos: dict[str,Image.Image]) -> tuple[Image.Image,str]:
    index = max(i for i,(start,_,_) in enumerate(SCENES) if start<=t)
    start,name,mode = SCENES[index]
    end = SCENES[index+1][0] if index+1<len(SCENES) else DURATION
    current = camera_frame(photos[name],t,start,end,index)
    fade = 3.0
    if index+1<len(SCENES) and t>end-fade:
        next_name = SCENES[index+1][1]
        next_end = SCENES[index+2][0] if index+2<len(SCENES) else DURATION
        target = camera_frame(photos[next_name],t,end,next_end,index+1)
        current = Image.blend(current,target,min(1.0,max(0.0,(t-end+fade)/fade)))
    return current,mode


def audio_features(ffmpeg: str) -> dict[str,np.ndarray]:
    """Analyze actual source audio for RMS, spectral flux, bands, and violin-range pitch."""
    rate,hop,nfft = 12000,400,2048
    raw = subprocess.run([ffmpeg,"-v","error","-i",str(AUDIO),"-f","f32le","-ac","1","-ar",str(rate),"pipe:1"],check=True,stdout=subprocess.PIPE).stdout
    samples = np.frombuffer(raw,dtype=np.float32)
    count = math.ceil(DURATION*FPS)
    window = np.hanning(nfft).astype(np.float32)
    freq = np.fft.rfftfreq(nfft,1/rate)
    masks = [(freq>=40)&(freq<180),(freq>=180)&(freq<2200),(freq>=2200)&(freq<6000),(freq>=330)&(freq<1900)]
    rms,low,mid,high,pitch,flux = [np.zeros(count,np.float32) for _ in range(6)]
    previous = np.zeros(len(freq),np.float32)
    for i in range(count):
        center=i*hop; begin=center-nfft//2
        segment=np.zeros(nfft,np.float32)
        a,b=max(0,begin),min(len(samples),begin+nfft)
        if b>a: segment[a-begin:b-begin]=samples[a:b]
        rms[i]=np.sqrt(np.mean(segment*segment))
        mag=np.abs(np.fft.rfft(segment*window)).astype(np.float32)
        low[i]=np.sqrt(np.mean(mag[masks[0]]**2)); mid[i]=np.sqrt(np.mean(mag[masks[1]]**2)); high[i]=np.sqrt(np.mean(mag[masks[2]]**2))
        flux[i]=np.maximum(mag-previous,0).sum()/(previous.sum()+1e-5)
        ids=np.flatnonzero(masks[3]); pitch[i]=freq[ids[int(np.argmax(mag[masks[3]]))]]
        previous=mag
    def norm(x:np.ndarray)->np.ndarray:
        return np.clip(x/(float(np.percentile(x,96)) or 1),0,1)
    def smooth(x:np.ndarray,n:int=7)->np.ndarray:
        return np.convolve(x,np.ones(n,np.float32)/n,mode="same").astype(np.float32)
    return {"rms":smooth(norm(rms)),"low":smooth(norm(low)),"mid":smooth(norm(mid)),"high":smooth(norm(high)),
            "onset":smooth(norm(flux),3),"pitch":smooth(np.clip((np.log2(np.maximum(pitch,200))-8.4)/2.2,0,1),9)}


def make_grade() -> Image.Image:
    y,x=np.mgrid[0:HEIGHT,0:WIDTH].astype(np.float32)
    yn=(y/HEIGHT-.51)/.29; xn=(x/WIDTH-.5)/.62
    center=np.exp(-.5*yn**2)*np.exp(-.20*xn**4)
    edges=np.clip((np.abs(x/WIDTH-.5)*2)**2*28,0,24)
    alpha=np.clip(12+center*70+edges,0,110).astype(np.uint8)
    rgba=np.zeros((HEIGHT,WIDTH,4),np.uint8);rgba[...,:3]=(3,8,20);rgba[...,3]=alpha
    return Image.fromarray(rgba,"RGBA")


def main() -> None:
    if not AUDIO.exists(): raise SystemExit(f"Missing audio: {AUDIO}")
    write_subtitles()
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe(); photos=load_scenes(); features=audio_features(ffmpeg); grade=make_grade()
    total_frames=math.ceil(DURATION*FPS)
    with tempfile.TemporaryDirectory(prefix="fireburning-") as tmp:
        background_video=Path(tmp)/"art-only.mp4"
        cmd=[ffmpeg,"-y","-v","error","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{WIDTH}x{HEIGHT}","-framerate",str(FPS),"-i","pipe:0",
             "-an","-c:v","libx264","-preset","ultrafast","-crf","17","-pix_fmt","yuv420p","-movflags","+faststart",str(background_video)]
        encoder=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        # Fixed blue-noise-like point layout: positions are deterministic; brightness is audio-driven.
        dust=[((i*379+53)%WIDTH,(i*197+41)%HEIGHT,(i*2.399963229728653)%(2*math.pi),1+i%3) for i in range(84)]
        cached_background = None
        cached_mode = None
        for frame in range(total_frames):
            t=frame/FPS; level=float(features["rms"][frame]); low=float(features["low"][frame])
            mid=float(features["mid"][frame]); high=float(features["high"][frame]); onset=float(features["onset"][frame]); pitch=float(features["pitch"][frame])
            # Camera drift is refreshed at 15 fps; audio-driven light still updates every output frame.
            if cached_background is None or frame % 2 == 0:
                photo, cached_mode = scene_at(t,photos)
                cached_background=Image.alpha_composite(photo.convert("RGBA"),grade)
            mode=cached_mode
            rgba=cached_background.copy()
            effects=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
            draw=ImageDraw.Draw(effects,"RGBA")

            # Violin-led silk ribbon: the tracked pitch lifts or lowers the curve while its measured band blooms.
            pitch_y=194-pitch*86; ribbon=[]
            for j in range(180):
                x=-12+j*7.3; u=j/179; envelope=math.sin(math.pi*u)**.45
                y=pitch_y+envelope*((17+62*mid)*math.sin(u*9.5-t*1.5))+9*math.sin(u*23+t*.72)
                ribbon.append((x,y))
            if mode!="bridge":
                draw.line(ribbon,fill=(238,174,87,18+int(28*mid)),width=14)
                draw.line(ribbon,fill=(255,229,184,38+int(72*mid)),width=2)
            else:
                strand=[(x,472+7*math.sin(x*.011-t*.25)) for x in range(-20,WIDTH+20,8)]
                draw.line(strand,fill=(244,205,146,42+int(55*mid)),width=2)

            # Measured low-band pulses ripple through the lake beneath the centered lyric-safe area.
            if mode not in ("title","bridge","outro"):
                cx,cy=WIDTH//2,565
                for ring in range(3):
                    radius=14+ring*32+24*low
                    alpha=int((18+45*low)*(1 if ring==0 else .55))
                    draw.ellipse((cx-radius*1.9,cy-radius*.38,cx+radius*1.9,cy+radius*.38),
                                 outline=(239,191,121,alpha),width=2)

            # The chorus infinity breathes with measured energy; positioned above lyrics for clean readability.
            if mode in ("chorus","chorus_alt","final"):
                energy=min(1,.28*low+.45*mid+.27*level)
                rx,ry=365+45*energy,92+18*energy;loop=[]
                for j in range(720):
                    a=2*math.pi*j/719;den=1+math.sin(a)**2
                    loop.append((WIDTH/2+rx*math.cos(a)/den,190+ry*math.sin(a)*math.cos(a)/den))
                draw.line(loop,fill=(236,170,78,16+int(12*energy)),width=13)
                draw.line(loop,fill=(255,218,153,35+int(28*energy)),width=2)

            # Fixed dust positions; measured onset/high-band energy determines glow and scale.
            if mode not in ("bridge","outro"):
                for i,(px,py,phase,base_r) in enumerate(dust):
                    if mode!="title" and 185<px<WIDTH-185 and 242<py<465: continue
                    if mode=="title":
                        attract=min(1,t/4);px=px*(1-attract*.35)+WIDTH*.5*(attract*.35);py=py*(1-attract*.24)+HEIGHT*.48*(attract*.24)
                    xx=(px+10*math.sin(t*.18+phase))%WIDTH;yy=(py-8*math.sin(t*.14+phase))%HEIGHT
                    alpha=int(min(135,8+70*onset+35*high));radius=base_r+.3+1.2*onset
                    draw.ellipse((xx-radius,yy-radius,xx+radius,yy+radius),fill=(255,218,159,alpha))

            # Fine vocal waveform is a single continuous filament, never a bar spectrum.
            if mode not in ("title","bridge","outro"):
                wave=[]
                for j in range(180):
                    u=j/179;x=74+u*(WIDTH-148);env=math.sin(math.pi*u)**.55
                    y=633+env*(8+33*mid)*math.sin(u*18-t*2.3)+env*(3+8*high)*math.sin(u*43-t*1.7)
                    wave.append((x,y))
                draw.line(wave,fill=(247,215,170,24+int(76*mid)),width=2)

            rgba=Image.alpha_composite(rgba,effects)
            # Fade to true black at the very end, with no added tail.
            if t>220:
                fade=min(1,(t-220)/4.832)
                rgba=Image.blend(rgba,Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,255)),fade)
            try: encoder.stdin.write(rgba.convert("RGB").tobytes())
            except BrokenPipeError as exc: raise RuntimeError("Background encoder stopped") from exc
            if frame and frame%(FPS*30)==0: print(f"Rendered art {t:0.0f}s / {DURATION:.0f}s",flush=True)
        encoder.stdin.close()
        if encoder.wait(): raise SystemExit("Background encoding failed")

        ass_abs=ASS_PATH.resolve().as_posix();fonts_abs=(ROOT/"assets/fonts").resolve().as_posix()
        vf=f"scale={OUT_WIDTH}:{OUT_HEIGHT}:flags=lanczos,subtitles=filename={ass_abs}:fontsdir={fonts_abs}"
        final=[ffmpeg,"-y","-v","error","-i",str(background_video),"-i",str(AUDIO),"-map","0:v:0","-map","1:a:0","-vf",vf,"-t",str(DURATION),
               "-r",str(OUT_FPS),"-c:v","libx264","-preset","veryfast","-tune","animation","-b:v","2600k","-maxrate","3000k","-bufsize","6000k","-pix_fmt","yuv420p",
               "-c:a","aac","-b:a","320k","-ar","48000","-movflags","+faststart","-metadata","title=Keep the Fire Burning",
               "-metadata","comment=Cinematic 4K lyric film",str(OUTPUT)]
        subprocess.run(final,check=True)
    print(f"Created 4K master: {OUTPUT} ({OUTPUT.stat().st_size/1_000_000:.1f} MB)")

if __name__=="__main__": main()
