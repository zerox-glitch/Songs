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

  const lyrics = [
    [13,18,'The morning light is breaking in Lahore,'],[18,23,'While midnight settles on your distant shore.'],
    [23,28,"I know you're pulling down the window blinds,"],[28,33,'And leaving all the heavy day behind.'],
    [33,37.5,'I trace the little pixels on the screen,'],[37.5,42,"The most beautiful face I've ever seen."],
    [44,49,'A half a world away, a different sky...'],[49,54,'But I can hear the softness in your sigh...'],
    [56,61.5,'I will keep the fire burning till you come back home!'],[61.5,67,'You never have to walk this heavy road alone!'],
    [67,72.5,'I carry every promise that we ever made!'],[72.5,78,'A quiet kind of love that never fades!'],
    [78,82,'Aaaahhh huh haaaa!'],[82,86,'Laaa la la laaaa!'],
    [91,96,'I leave the phone right next to me in bed,'],[96,101,'Just so I can hear you breathing deep.'],
    [101,106,'It closes up the thousands of miles,'],[106,111,"To know I'm right beside you when you sleep."],
    [111,116,'We share the day and pass the sun along,'],[116,121,'You are the only place where I belong.'],
    [123,128,'A half a world away, a different sky...'],[128,133,'But I can hear the softness in your sigh...'],
    [135,140.5,'I will keep the fire burning till you come back home!'],[140.5,146,'You never have to walk this heavy road alone!'],
    [146,151.5,'I carry every promise that we ever made!'],[151.5,157,'A quiet kind of love that never fades!'],
    [157,161,'Aaaahhh huh haaaa!'],[161,165,'Laaa la la laaaa!'],[165,169,'Aaaahhh huh haaaa!'],
    [174,181,"I don't need a crowded room or fancy things..."],[181,188,'I only need the peace your voice brings...'],
    [191,197.5,'I will keep the fire burning till you come back home!'],[197.5,204,'You never have to walk this heavy road alone!'],
    [204,210.5,'I carry every promise that we ever made!'],[210.5,217,'A quiet kind of love that never fades!'],
    [217,220.5,'Aaaahhh huh haaaa!'],[220.5,222.5,'Laaa la la laaaa!'],[222.5,224.832,'Come back home...']
  ];
  const sceneTimeline=[[0,'title-cosmic.jpg'],[12,'lyric-lahore-panorama.jpg'],[43,'celestial-ocean.jpg'],[55,'chorus-golden-infinity.jpg'],[87,'moonlit-garden.jpg'],[122,'celestial-ocean.jpg'],[135,'chorus-golden-infinity.jpg'],[170,'celestial-ocean.jpg'],[190,'chorus-golden-infinity.jpg'],[217,'celestial-ocean.jpg']];
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
