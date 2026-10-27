#!/usr/bin/env python3
"""Render a 4K cinematic lyric film with audio-reactive procedural art.
Requires Pillow, NumPy, and imageio-ffmpeg. The uploaded MP3 remains the audio source.
"""
from __future__ import annotations
import math
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "Keep the Fire Burning (Remastered).mp3"
OUTPUT = ROOT / "Keep the Fire Burning - Lyric Visualizer.mp4"
ASS_PATH = ROOT / "lyrics" / "lyrics.ass"
WIDTH, HEIGHT, FPS = 1280, 720, 30
OUT_WIDTH, OUT_HEIGHT, OUT_FPS = 3840, 2160, 30
DURATION = 224.832

# Phrase-level cues. Lyrics are exact; these are not presented as forced-aligned word times.
LINES = [
    (13.0, 18.0, "The morning light is breaking in Lahore,"),
    (18.0, 23.0, "While midnight settles on your distant shore."),
    (23.0, 28.0, "I know you're pulling down the window blinds,"),
    (28.0, 33.0, "And leaving all the heavy day behind."),
    (33.0, 37.5, "I trace the little pixels on the screen,"),
    (37.5, 42.0, "The most beautiful face I've ever seen."),
    (44.0, 49.0, "A half a world away, a different sky..."),
    (49.0, 54.0, "But I can hear the softness in your sigh..."),
    (56.0, 61.5, "I will keep the fire burning till you come back home!"),
    (61.5, 67.0, "You never have to walk this heavy road alone!"),
    (67.0, 72.5, "I carry every promise that we ever made!"),
    (72.5, 78.0, "A quiet kind of love that never fades!"),
    (78.0, 82.0, "Aaaahhh huh haaaa!"),
    (82.0, 86.0, "Laaa la la laaaa!"),
    (91.0, 96.0, "I leave the phone right next to me in bed,"),
    (96.0, 101.0, "Just so I can hear you breathing deep."),
    (101.0, 106.0, "It closes up the thousands of miles,"),
    (106.0, 111.0, "To know I'm right beside you when you sleep."),
    (111.0, 116.0, "We share the day and pass the sun along,"),
    (116.0, 121.0, "You are the only place where I belong."),
    (123.0, 128.0, "A half a world away, a different sky..."),
    (128.0, 133.0, "But I can hear the softness in your sigh..."),
    (135.0, 140.5, "I will keep the fire burning till you come back home!"),
    (140.5, 146.0, "You never have to walk this heavy road alone!"),
    (146.0, 151.5, "I carry every promise that we ever made!"),
    (151.5, 157.0, "A quiet kind of love that never fades!"),
    (157.0, 161.0, "Aaaahhh huh haaaa!"),
    (161.0, 165.0, "Laaa la la laaaa!"),
    (165.0, 169.0, "Aaaahhh huh haaaa!"),
    (174.0, 181.0, "I don't need a crowded room or fancy things..."),
    (181.0, 188.0, "I only need the peace your voice brings..."),
    (191.0, 197.5, "I will keep the fire burning till you come back home!"),
    (197.5, 204.0, "You never have to walk this heavy road alone!"),
    (204.0, 210.5, "I carry every promise that we ever made!"),
    (210.5, 217.0, "A quiet kind of love that never fades!"),
    (217.0, 220.5, "Aaaahhh huh haaaa!"),
    (220.5, 222.5, "Laaa la la laaaa!"),
    (222.5, 224.832, "Come back home..."),
]

# No people or silhouettes; scenes follow the broad musical arc.
SCENES = [
    (0.0, "celestial-ocean.jpg", "title"),
    (12.0, "two-skies.jpg", "verse"),
    (43.0, "celestial-ocean.jpg", "pre"),
    (55.0, "celestial-ocean.jpg", "chorus"),
    (87.0, "moonlit-garden.jpg", "verse2"),
    (122.0, "celestial-ocean.jpg", "pre"),
    (135.0, "celestial-ocean.jpg", "chorus"),
    (170.0, "celestial-ocean.jpg", "bridge"),
    (190.0, "celestial-ocean.jpg", "final"),
    (217.0, "celestial-ocean.jpg", "outro"),
]
FONT_SERIF = ROOT / "assets/fonts/CormorantGaramond-SemiBold.ttf"
FONT_SCRIPT = ROOT / "assets/fonts/Allura-Regular.ttf"


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
    for start, end, text in LINES:
        chorus = any(a <= start < b for a,b in ((56,87),(135,170),(191,222.5)))
        bridge = 174 <= start < 190
        vocalise = text.startswith(("Aaa", "Laaa"))
        size = 300 if chorus else (275 if bridge else (290 if vocalise else 360))
        fnt = ImageFont.truetype(str(FONT_SERIF), size)
        rows = wrap_balanced(text, fnt, 3000)
        while len(rows) > 2 and size > 220:
            size -= 10
            fnt = ImageFont.truetype(str(FONT_SERIF), size)
            rows = wrap_balanced(text, fnt, 3000)
        if start == 13.0:
            rows = ["The morning light", "is breaking in Lahore,"]
            escaped = ("{\\fnAllura\\fs450\\1c&H0038DFFF&\\bord1}The morning light"
                       "\\N{\\rLyrics\\fs360}is breaking in Lahore,")
        else:
            escaped = "\\N".join(rows).replace("{", "\\{").replace("}", "\\}")
        gold = "\\1c&H00A1D7F4&" if chorus else ""
        italic = "\\i1" if bridge or vocalise else ""
        tags = (f"{{\\an5\\pos(1920,1080)\\fs{size}{gold}{italic}\\blur2.2\\bord5\\shad8"
                f"\\fad(420,420)\\t(0,400,\\blur0.25)}}")
        ass.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Lyrics,,0,0,0,,{tags}{escaped}")
    ASS_PATH.write_text("\n".join(ass)+"\n", encoding="utf-8")


def load_scenes() -> dict[str, Image.Image]:
    photos = {}
    for _, name, _ in SCENES:
        if name not in photos:
            image = Image.open(ROOT / "assets" / name).convert("RGB")
            image = ImageOps.fit(image, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS, centering=(.5,.48))
            image = ImageEnhance.Color(image).enhance(.90)
            image = ImageEnhance.Contrast(image).enhance(1.04)
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
        for frame in range(total_frames):
            t=frame/FPS; level=float(features["rms"][frame]); low=float(features["low"][frame])
            mid=float(features["mid"][frame]); high=float(features["high"][frame]); onset=float(features["onset"][frame]); pitch=float(features["pitch"][frame])
            photo,mode=scene_at(t,photos)
            rgba=Image.alpha_composite(photo.convert("RGBA"),grade)
            glow=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0));gd=ImageDraw.Draw(glow,"RGBA");draw=ImageDraw.Draw(rgba,"RGBA")

            # Violin-led liquid-gold string: pitch moves the arc; measured band energy drives its bloom.
            pitch_y=194-pitch*86; ribbon=[]
            for j in range(180):
                x=-12+j*7.3; u=j/179; envelope=math.sin(math.pi*u)**.45
                y=pitch_y+envelope*((17+62*mid)*math.sin(u*9.5-t*1.5))+9*math.sin(u*23+t*.72)
                ribbon.append((x,y))
            if mode!="bridge":
                gd.line(ribbon,fill=(238,174,87,24+int(38*mid)),width=11+int(24*mid))
                rgba=Image.alpha_composite(rgba,glow.filter(ImageFilter.GaussianBlur(12)));draw=ImageDraw.Draw(rgba,"RGBA")
                draw.line(ribbon,fill=(246,211,155,42+int(95*mid)),width=2)
            else:
                strand=[(x,472+7*math.sin(x*.011-t*.25)) for x in range(-20,WIDTH+20,8)]
                draw.line(strand,fill=(244,205,146,70+int(60*mid)),width=2)

            # Low-band pulses create soft lake ripples. Bridge stays nearly still.
            if mode not in ("title","bridge","outro"):
                cx,cy=WIDTH//2,515
                for ring in range(3):
                    radius=22+ring*34+28*low;alpha=int((18+42*low)*(1 if ring==0 else .55))
                    draw.ellipse((cx-radius*1.9,cy-radius*.44,cx+radius*1.9,cy+radius*.44),outline=(239,191,121,alpha),width=2)

            # Chorus infinity, gently expanding with the measured low/mid-band energy.
            if mode in ("chorus","final"):
                energy=min(1,.28*low+.45*mid+.27*level);rx,ry=365+48*energy,156+28*energy;loop=[]
                for j in range(720):
                    a=2*math.pi*j/719;den=1+math.sin(a)**2
                    loop.append((WIDTH/2+rx*math.cos(a)/den,HEIGHT/2+ry*math.sin(a)*math.cos(a)/den))
                aura=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
                ImageDraw.Draw(aura,"RGBA").line(loop,fill=(236,170,78,int(22+24*energy)),width=15)
                rgba=Image.alpha_composite(rgba,aura.filter(ImageFilter.GaussianBlur(12)));draw=ImageDraw.Draw(rgba,"RGBA")
                draw.line(loop,fill=(245,202,133,int(34+65*energy)),width=2)

            # Sparkles are spatially deterministic and respond to detected onsets / high-frequency energy.
            if mode not in ("bridge","outro"):
                for i,(px,py,phase,base_r) in enumerate(dust):
                    if 185<px<WIDTH-185 and 242<py<465: continue
                    if mode=="title":
                        attract=min(1,t/4);px=px*(1-attract*.35)+WIDTH*.5*(attract*.35);py=py*(1-attract*.24)+HEIGHT*.48*(attract*.24)
                    xx=(px+10*math.sin(t*.18+phase))%WIDTH;yy=(py-8*math.sin(t*.14+phase))%HEIGHT
                    alpha=int(min(145,12+96*onset+32*high));radius=base_r+.4+1.4*onset
                    draw.ellipse((xx-radius,yy-radius,xx+radius,yy+radius),fill=(255,218,159,alpha))

            # Delicate continuous vocal trace, tucked beneath the central lyric-safe zone.
            if mode not in ("title","bridge","outro"):
                wave=[]
                for j in range(180):
                    u=j/179;x=74+u*(WIDTH-148);env=math.sin(math.pi*u)**.55
                    y=633+env*(8+33*mid)*math.sin(u*18-t*2.3)+env*(3+8*high)*math.sin(u*43-t*1.7)
                    wave.append((x,y))
                draw.line(wave,fill=(247,215,170,28+int(94*mid)),width=2)

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
