(() => {
  const audio = document.querySelector('#audio');
  const canvas = document.querySelector('#visual');
  const gl = canvas.getContext('webgl', {alpha: false, antialias: true});
  const playButton = document.querySelector('#play');
  const playIcon = document.querySelector('#play-icon');
  const muteButton = document.querySelector('#mute');
  const seek = document.querySelector('#seek');
  const now = document.querySelector('#now');
  const duration = document.querySelector('#duration');
  const lyricEl = document.querySelector('#lyric');
  const sectionEl = document.querySelector('#section');

  const lyrics = [
    [13,'VERSE 1','The morning light is breaking in Lahore,'],[18,'VERSE 1','While midnight settles on your distant shore.'],
    [23,'VERSE 1',"I know you're pulling down the window blinds,"],[28,'VERSE 1','And leaving all the heavy day behind.'],
    [33,'VERSE 1','I trace the little pixels on the screen,'],[37.5,'VERSE 1',"The most beautiful face I've ever seen."],
    [44,'PRE-CHORUS','A half a world away, a different sky...'],[49,'PRE-CHORUS','But I can hear the softness in your sigh...'],
    [56,'CHORUS','I will keep the fire burning till you come back home!'],[61.5,'CHORUS','You never have to walk this heavy road alone!'],
    [67,'CHORUS','I carry every promise that we ever made!'],[72.5,'CHORUS','A quiet kind of love that never fades!'],
    [78,'CHORUS','Aaaahhh huh haaaa!'],[82,'CHORUS','Laaa la la laaaa!'],
    [91,'VERSE 2','I leave the phone right next to me in bed,'],[96,'VERSE 2','Just so I can hear you breathing deep.'],
    [101,'VERSE 2','It closes up the thousands of miles,'],[106,'VERSE 2',"To know I'm right beside you when you sleep."],
    [111,'VERSE 2','We share the day and pass the sun along,'],[116,'VERSE 2','You are the only place where I belong.'],
    [123,'PRE-CHORUS','A half a world away, a different sky...'],[128,'PRE-CHORUS','But I can hear the softness in your sigh...'],
    [135,'CHORUS','I will keep the fire burning till you come back home!'],[140.5,'CHORUS','You never have to walk this heavy road alone!'],
    [146,'CHORUS','I carry every promise that we ever made!'],[151.5,'CHORUS','A quiet kind of love that never fades!'],
    [157,'CHORUS','Aaaahhh huh haaaa!'],[161,'CHORUS','Laaa la la laaaa!'],[165,'CHORUS','Aaaahhh huh haaaa!'],
    [174,'BRIDGE',"I don't need a crowded room or fancy things..."],[181,'BRIDGE','I only need the peace your voice brings...'],
    [191,'FINAL CHORUS','I will keep the fire burning till you come back home!'],[197.5,'FINAL CHORUS','You never have to walk this heavy road alone!'],
    [204,'FINAL CHORUS','I carry every promise that we ever made!'],[210.5,'FINAL CHORUS','A quiet kind of love that never fades!'],
    [217,'FINAL CHORUS','Aaaahhh huh haaaa!'],[220.5,'FINAL CHORUS','Laaa la la laaaa!'],[222.5,'OUTRO','Come back home...']
  ];
  let activeIndex = -1;
  function setLyric() {
    const t = audio.currentTime;
    let index = -1;
    for (let i = 0; i < lyrics.length; i++) if (t >= lyrics[i][0]) index = i; else break;
    if (index !== activeIndex) {
      activeIndex = index;
      if (index < 0) { sectionEl.textContent = t < 12 ? 'PRESS PLAY TO BEGIN' : 'INSTRUMENTAL'; lyricEl.textContent = 'A half a world away, a different sky…'; }
      else { sectionEl.textContent = lyrics[index][1]; lyricEl.textContent = lyrics[index][2]; }
    }
  }
  function fmt(value) { if (!Number.isFinite(value)) return '0:00'; const m=Math.floor(value/60), s=Math.floor(value%60); return `${m}:${String(s).padStart(2,'0')}`; }
  playButton.addEventListener('click', async () => { if (audio.paused) { try { await audio.play(); } catch (e) { sectionEl.textContent='AUDIO COULD NOT BE LOADED'; } } else audio.pause(); });
  audio.addEventListener('play',()=>{playIcon.textContent='Ⅱ';playButton.setAttribute('aria-label','Pause song');});
  audio.addEventListener('pause',()=>{playIcon.textContent='▶';playButton.setAttribute('aria-label','Play song');});
  audio.addEventListener('loadedmetadata',()=>{seek.max=audio.duration;duration.textContent=fmt(audio.duration);});
  audio.addEventListener('timeupdate',()=>{if(!seek.matches(':active'))seek.value=audio.currentTime;now.textContent=fmt(audio.currentTime);seek.style.background=`linear-gradient(90deg,#f1c99e ${100*audio.currentTime/(audio.duration||1)}%,rgba(255,255,255,.3) 0%)`;setLyric();});
  seek.addEventListener('input',()=>{audio.currentTime=Number(seek.value);});
  muteButton.addEventListener('click',()=>{audio.muted=!audio.muted;muteButton.textContent=audio.muted?'×':'♫';});

  if (!gl) { canvas.style.display='none'; return; }
  const vertex = `attribute vec2 p; void main(){gl_Position=vec4(p,0.,1.);}`;
  const fragment = `precision highp float; uniform vec2 resolution; uniform float time; uniform float energy;
    float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    void main(){vec2 uv=gl_FragCoord.xy/resolution; vec2 p=(gl_FragCoord.xy-.5*resolution)/resolution.y;
    float t=time*.13; vec3 warm=vec3(.72,.33,.22), cool=vec3(.075,.12,.29);
    float blend=smoothstep(-.58,.60,p.x); vec3 col=mix(warm,cool,blend);
    float sun=exp(-length((p-vec2(-.38,.05))*vec2(1.0,1.3))*3.4); col+=sun*vec3(.5,.23,.10);
    float halo=exp(-length(p-vec2(.18,.02))*2.1); col+=halo*vec3(.08,.12,.27);
    float r=length(p-vec2(.0,-.06)); float pulse=.34+.012*sin(time*1.2)+energy*.035;
    float ring=exp(-abs(r-pulse)*100.); col+=ring*vec3(.32,.25,.17)*.25;
    float ring2=exp(-abs(r-(pulse+.10))*68.); col+=ring2*vec3(.23,.30,.44)*.16;
    float horizon=exp(-abs(p.y+.27+sin(p.x*2.7+t)*.012)*90.); col+=horizon*vec3(.38,.24,.16)*.13;
    float grain=hash(floor(gl_FragCoord.xy*.45)+floor(time*4.)); col+=(grain-.5)*.018;
    float vignette=1.0-smoothstep(.18,1.15,length(p*vec2(.78,1.0))); col*=.58+.42*vignette;
    gl_FragColor=vec4(col,1.);}`;
  function shader(type, src) {const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))console.error(gl.getShaderInfoLog(s));return s;}
  const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);gl.useProgram(program);
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
  const loc=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
  const resLoc=gl.getUniformLocation(program,'resolution'),timeLoc=gl.getUniformLocation(program,'time'),energyLoc=gl.getUniformLocation(program,'energy');
  let analyser=null, data=null, audioCtx=null;
  function resize(){const ratio=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.floor(innerWidth*ratio);canvas.height=Math.floor(innerHeight*ratio);gl.viewport(0,0,canvas.width,canvas.height);gl.uniform2f(resLoc,canvas.width,canvas.height);}
  function connectAudio(){if(!audioCtx){audioCtx=new(window.AudioContext||window.webkitAudioContext)();analyser=audioCtx.createAnalyser();analyser.fftSize=256;data=new Uint8Array(analyser.frequencyBinCount);const source=audioCtx.createMediaElementSource(audio);source.connect(analyser);analyser.connect(audioCtx.destination);}if(audioCtx.state==='suspended')audioCtx.resume();}
  audio.addEventListener('play',connectAudio);
  function draw(ms){let e=0;if(analyser){analyser.getByteFrequencyData(data);for(let i=0;i<data.length;i++)e+=data[i];e/=data.length*255;}gl.uniform1f(timeLoc,ms/1000);gl.uniform1f(energyLoc,e);gl.drawArrays(gl.TRIANGLES,0,6);requestAnimationFrame(draw);}
  window.addEventListener('resize',resize);resize();requestAnimationFrame(draw);
})();
