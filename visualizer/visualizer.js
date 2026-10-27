(() => {
  const audio = document.querySelector('#audio');
  const canvas = document.querySelector('#visual');
  const gl = canvas.getContext('webgl', {alpha:true, antialias:true});
  const title = document.querySelector('#title');
  const lyricWrap = document.querySelector('.lyric-wrap');
  const lyricEl = document.querySelector('#lyric');
  const playButton = document.querySelector('#play');
  const playIcon = document.querySelector('#play-icon');
  const muteButton = document.querySelector('#mute');
  const seek = document.querySelector('#seek');

  let lyrics = [];
  let sceneTimeline = [[0,'title-cosmic.jpg']];
  fetch('../lyrics/timeline.json')
    .then(response => { if (!response.ok) throw new Error('Could not load visual timeline'); return response.json(); })
    .then(timeline => {
      lyrics = timeline.lyrics.map(({start,end,text}) => [start,end,text]);
      sceneTimeline = timeline.scenes.map(({start,image}) => [start,image]);
      updateScene();
      updateLyrics();
    })
    .catch(error => console.error(error));
  const photoA=document.querySelector('#photo-a'),photoB=document.querySelector('#photo-b');
  let currentPhoto=photoA,nextPhoto=photoB,activeScene=0,activeLyric=-2;
  photoA.style.backgroundImage="url('../assets/title-cosmic.jpg')";
  sceneTimeline.forEach(([,name])=>{const img=new Image();img.src=`../assets/${name}`;});
  function updateScene(){
    const t=audio.currentTime;let scene=0;
    for(let i=0;i<sceneTimeline.length;i++)if(t>=sceneTimeline[i][0])scene=i;else break;
    if(scene===activeScene)return;activeScene=scene;
    nextPhoto.style.backgroundImage=`url('../assets/${sceneTimeline[scene][1]}')`;
    nextPhoto.classList.add('visible');currentPhoto.classList.remove('visible');
    [currentPhoto,nextPhoto]=[nextPhoto,currentPhoto];
  }
  function updateLyrics(){
    const t=audio.currentTime;updateScene();
    title.classList.toggle('hidden',t>=10.5);
    let index=-1;
    if(t>=12)for(let i=0;i<lyrics.length;i++){if(t>=lyrics[i][0]&&t<lyrics[i][1]){index=i;break;}}
    if(index!==activeLyric){
      activeLyric=index;lyricEl.textContent=index<0?'':lyrics[index][2];
      lyricWrap.classList.toggle('show',index>=0);
      if(index>=0){lyricWrap.classList.remove('show');requestAnimationFrame(()=>lyricWrap.classList.add('show'));}
    }
  }
  playButton.addEventListener('click',async()=>{if(audio.paused){try{await audio.play();}catch(e){}}else audio.pause();});
  audio.addEventListener('play',()=>{playIcon.textContent='Ⅱ';playButton.setAttribute('aria-label','Pause song');});
  audio.addEventListener('pause',()=>{playIcon.textContent='▶';playButton.setAttribute('aria-label','Play song');});
  audio.addEventListener('timeupdate',()=>{if(!seek.matches(':active'))seek.value=audio.currentTime;seek.style.background=`linear-gradient(90deg,#f1c99e ${100*audio.currentTime/(audio.duration||1)}%,rgba(255,255,255,.3) 0%)`;updateLyrics();});
  audio.addEventListener('loadedmetadata',()=>{seek.max=audio.duration;});
  seek.addEventListener('input',()=>{audio.currentTime=Number(seek.value);updateLyrics();});
  muteButton.addEventListener('click',()=>{audio.muted=!audio.muted;muteButton.textContent=audio.muted?'×':'♫';});
  updateLyrics();

  if(!gl){canvas.style.display='none';return;}
  const vertex='attribute vec2 p; void main(){gl_Position=vec4(p,0.,1.);}';
  const fragment=`precision highp float;uniform vec2 resolution;uniform float time;uniform float energy;
    void main(){vec2 p=(gl_FragCoord.xy-.5*resolution)/resolution.y;
    float mask=smoothstep(-.72,-.56,p.x)*(1.0-smoothstep(.56,.72,p.x));
    float base=-.405+sin(p.x*12.0-time*1.7)*(.012+energy*.055);
    float d=abs(p.y-base);float trace=exp(-d*230.0)*(.10+energy*.42);
    float glow=exp(-d*34.0)*(.025+energy*.10);float alpha=clamp((trace+glow)*mask,0.0,.38);
    vec3 ink=mix(vec3(.98,.76,.53),vec3(.74,.82,1.0),smoothstep(-.48,.48,p.x));gl_FragColor=vec4(ink,alpha);}`;
  function shader(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))console.error(gl.getShaderInfoLog(s));return s;}
  const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);gl.useProgram(program);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.clearColor(0,0,0,0);
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
  const loc=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
  const resLoc=gl.getUniformLocation(program,'resolution'),timeLoc=gl.getUniformLocation(program,'time'),energyLoc=gl.getUniformLocation(program,'energy');
  let analyser=null,data=null,audioCtx=null;
  function resize(){const ratio=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.floor(innerWidth*ratio);canvas.height=Math.floor(innerHeight*ratio);gl.viewport(0,0,canvas.width,canvas.height);gl.uniform2f(resLoc,canvas.width,canvas.height);}
  function connectAudio(){if(!audioCtx){audioCtx=new(window.AudioContext||window.webkitAudioContext)();analyser=audioCtx.createAnalyser();analyser.fftSize=256;data=new Uint8Array(analyser.frequencyBinCount);const source=audioCtx.createMediaElementSource(audio);source.connect(analyser);analyser.connect(audioCtx.destination);}if(audioCtx.state==='suspended')audioCtx.resume();}
  audio.addEventListener('play',connectAudio);
  function draw(ms){let e=0;if(analyser){analyser.getByteFrequencyData(data);for(let i=0;i<data.length;i++)e+=data[i];e/=data.length*255;}gl.uniform1f(timeLoc,ms/1000);gl.uniform1f(energyLoc,e);gl.clear(gl.COLOR_BUFFER_BIT);gl.drawArrays(gl.TRIANGLES,0,6);requestAnimationFrame(draw);}
  window.addEventListener('resize',resize);resize();requestAnimationFrame(draw);
})();
