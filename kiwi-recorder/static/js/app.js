/* KCC16: Complete clean app.js */
const POLL=500;
let LS=null,RC=[],CH=null,LV=-1,allLogs=[];

const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const post=async(p,b)=>{const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):'{}'});try{return await r.json()}catch{return{}}};
const get=async p=>(await fetch(p)).json();
const badge=(k,t,c='')=>{const e=$(`.bd[data-key="${k}"]`);if(e){e.textContent=t;e.className='bd'+(c?' '+c:'')}};
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const flash=(b,t)=>{const o=b.textContent;b.textContent=t;setTimeout(()=>b.textContent=o,1e3)};

// ═══════════════════════════════════════
// CAMERAS
// ═══════════════════════════════════════
function renderCams(c,st){
  if(!(c.length===RC.length&&c.every((x,i)=>x===RC[i]))){
    const r=$('#cam-row');r.innerHTML='';
    c.forEach(n=>{const d=document.createElement('div');d.className='cm';
      d.innerHTML=`<img src="/camera/${n}.mjpg"/><span class="cl">observation.images.${n}</span><span class="cs" data-cs="${n}">live</span>`;
      r.appendChild(d)});RC=c.slice();
  }
  $$('.cm').forEach(t=>{t.classList.toggle('xv',st==='review');t.classList.toggle('xr',st==='recording')});
  $$('[data-cs]').forEach(e=>{const r=st==='recording',v=st==='review';
    e.textContent=r?'rec':v?'preview':'live';e.className='cs '+(r?'recording':v?'review':'live')});
}

// ═══════════════════════════════════════
// STATUS POLLING
// ═══════════════════════════════════════
async function poll(){try{const s=await get('/status');LS=s;sync(s)}catch{badge('state','offline','er')}setTimeout(poll,POLL)}

function sync(s){
  badge('state',s.state,s.state==='recording'?'er':s.state==='review'?'wn':'teleop finished'.includes(s.state)?'li':'error disconnected'.includes(s.state)?'er':'');
  badge('cameras',s.cameras.join(', ')||'—',s.cameras.length?'ok':'wn');
  badge('dataset',s.dataset_initialized?`${s.hf_org}/${s.hf_repo_name}`:'—',s.dataset_initialized?'ok':'');
  renderCams(s.cameras,s.state);
  const ri=$('#ri');if(ri){ri.className=s.state;ri.querySelector('.rt').textContent=s.state}
  const rm=$('#rm');if(rm)rm.textContent=`${s.current_episode_seconds.toFixed(1)}s · ${s.episodes_done}/${s.target_episodes}`;
  const u=(id,v)=>{const e=document.getElementById(id);if(e&&document.activeElement!==e)e.value=v};
  u('ep_done',s.episodes_done);u('ep_tgt',s.target_episodes);u('ep_nxt',s.episodes_done+1);
  const pf=$('#pf');if(pf)pf.style.width=(s.target_episodes>0?Math.min(100,s.episodes_done/s.target_episodes*100):0)+'%';
  const I=s.state==='idle',T=s.state==='teleop',R=s.state==='recording',V=s.state==='review',E='error disconnected'.includes(s.state);
  const d=(id,v)=>{const e=$(id);if(e)e.disabled=v};const h=(id,v)=>{const e=$(id);if(e)e.hidden=v};
  h('#btn-rec',R);h('#btn-stop',!R);d('#btn-rec',!(I||T)||!s.dataset_initialized||E);d('#btn-stop',!R);
  h('#rv',!V);d('#btn-ini',R||V);h('#btn-recon',!E);
  d('#btn-tl-on',!(I&&!E));d('#btn-tl-off',!T);
  if(s.episodes_done>LV&&s.dataset_initialized&&s.state==='idle'){LV=s.episodes_done;fetchStats()}
  if(s.log_tail){allLogs=s.log_tail;const l=$('#log');if(l){l.innerHTML=s.log_tail.slice(-6).map(x=>`<div class="line">${esc(x)}</div>`).join('');l.scrollTop=l.scrollHeight}}
}

// ═══════════════════════════════════════
// DATA INSPECTOR
// ═══════════════════════════════════════
async function fetchStats(){try{const s=await get('/dataset_stats');if(!s.ok)return;
  const sv=(id,v,cls)=>{const e=$(id);if(e){e.textContent=v;if(cls)e.className='iv '+cls}};
  sv('#i-ep',s.total_episodes,s.total_episodes>0?'ok':'');
  sv('#i-fr',s.total_frames);
  sv('#i-dur',s.last_ep_duration?s.last_ep_duration.toFixed(1)+'s':'—');
  sv('#i-arm',s.arm_range||'—');
  sv('#i-wh',s.wheel_range||'—',s.wheels_still?'ok':'wn');
  sv('#i-ent',s.entanglement!=null?'E='+s.entanglement.toFixed(3):'—',s.entanglement!=null&&s.entanglement<0.05?'ok':s.entanglement>0.3?'wn':'');
  sv('#i-pq',s.parquet_ok?'OK':'—',s.parquet_ok?'ok':'er');
  sv('#i-vid',s.videos_ok?'OK':'—',s.videos_ok?'ok':'er');
  if(s.last_ep_actions?.length)updateChart(s.last_ep_actions);
}catch(e){console.error(e)}}

// ═══════════════════════════════════════
// CHART
// ═══════════════════════════════════════
function initChart(){const x=$('#action-chart');if(!x)return;
  const n=['s_pan','s_lift','elbow','w_flex','w_roll','grip'],c=['#E05A47','#47A05E','#4785C4','#D4953A','#9D6AC4','#2DB5A0'];
  CH=new Chart(x,{type:'line',data:{labels:[],datasets:n.map((l,i)=>({label:l,data:[],borderColor:c[i],borderWidth:1.2,pointRadius:0,tension:0.3}))},
    options:{responsive:true,maintainAspectRatio:false,animation:false,
      plugins:{legend:{position:'bottom',labels:{font:{size:7,family:'JetBrains Mono'},boxWidth:7,padding:3}}},
      scales:{x:{ticks:{font:{size:6},maxTicksLimit:5}},y:{ticks:{font:{size:6}}}}}});}
function updateChart(a){if(!CH)return;const s=Math.max(1,Math.floor(a.length/100)),d=a.filter((_,i)=>i%s===0);
  CH.data.labels=d.map((_,i)=>(i*s/30).toFixed(1));for(let j=0;j<6;j++)CH.data.datasets[j].data=d.map(r=>r[j]);CH.update()}

// ═══════════════════════════════════════
// 3D ARM — Luxury Minimalist LeRobot Style
let sc3=null,cam3=null,ren3=null;
let armJoints=[],gripL=null,gripR=null;
let orb={t:0.6,p:0.45,d:0.42,drag:false,x:0,y:0};
let armState=[0,-45,-30,20,0,0,0,0,0]; // default visible pose

const ARMCFG=[
  {h:0.04,r:0.014,c:0x9C958C},  // base — warm stone
  {h:0.10,r:0.010,c:0xC47060},  // shoulder — dusty rose
  {h:0.10,r:0.009,c:0x6EA87A},  // elbow — sage
  {h:0.08,r:0.008,c:0x7090B8},  // wrist — slate
  {h:0.05,r:0.006,c:0xC09860},  // end — warm sand
];

function init3D(){
  const ct=$('#arm-ct');
  if(!ct||typeof THREE==='undefined'){console.warn('KCC16: Three.js not loaded');return}
  const W=ct.clientWidth,H=ct.clientHeight;
  if(W<10||H<10){console.warn('KCC16: arm container too small',W,H);return}

  sc3=new THREE.Scene();
  sc3.background=new THREE.Color(0xEDE8E2);

  cam3=new THREE.PerspectiveCamera(40,W/H,0.01,10);
  updCam3();

  ren3=new THREE.WebGLRenderer({antialias:true});
  ren3.setSize(W,H);
  ren3.setPixelRatio(Math.min(window.devicePixelRatio,2));
  ren3.shadowMap.enabled=true;
  ren3.shadowMap.type=THREE.PCFSoftShadowMap;
  ren3.toneMapping=THREE.ACESFilmicToneMapping;
  ren3.toneMappingExposure=1.3;
  ct.appendChild(ren3.domElement);

  // Soft cinematic lighting
  sc3.add(new THREE.AmbientLight(0xC8C0B8,0.55));
  const key=new THREE.DirectionalLight(0xFFF0E0,0.6);key.position.set(0.4,0.8,0.3);key.castShadow=true;sc3.add(key);
  const fill=new THREE.DirectionalLight(0xA8B0C8,0.25);fill.position.set(-0.3,0.4,-0.5);sc3.add(fill);
  const rim=new THREE.PointLight(0xD0C8B8,0.12,0.8);rim.position.set(0,0.3,0);sc3.add(rim);

  // Ground — warm light
  const gndMat=new THREE.MeshStandardMaterial({color:0xE2DCD4,roughness:0.85,metalness:0.05});
  const gnd=new THREE.Mesh(new THREE.PlaneGeometry(0.6,0.6),gndMat);
  gnd.rotation.x=-Math.PI/2;gnd.receiveShadow=true;sc3.add(gnd);

  // Grid — very subtle
  const grid=new THREE.GridHelper(0.5,12,0xD0C8BE,0xDBD4CA);
  grid.position.y=0.001;sc3.add(grid);

  // Build arm — hierarchical cylinders + spheres
  armJoints=[];
  let parent=sc3;
  let yOff=0;

  ARMCFG.forEach((cfg,i)=>{
    const group=new THREE.Group();
    group.position.y=yOff;
    parent.add(group);

    // Cylinder link
    const cyl=new THREE.Mesh(
      new THREE.CylinderGeometry(cfg.r*0.9,cfg.r,cfg.h,12),
      new THREE.MeshStandardMaterial({color:cfg.c,roughness:0.55,metalness:0.2})
    );
    cyl.position.y=cfg.h/2;
    cyl.castShadow=true;
    group.add(cyl);

    // Joint sphere
    const sph=new THREE.Mesh(
      new THREE.SphereGeometry(cfg.r*1.3,12,12),
      new THREE.MeshStandardMaterial({color:0xC8C0B5,roughness:0.4,metalness:0.15,emissive:0xE0D8D0,emissiveIntensity:0.05})
    );
    group.add(sph);

    armJoints.push(group);
    parent=group;
    yOff=cfg.h;
  });

  // Gripper — soft sage
  const gMat=new THREE.MeshStandardMaterial({color:0x70B8A0,roughness:0.5,metalness:0.15,emissive:0xA0D0C0,emissiveIntensity:0.05});
  gripL=new THREE.Mesh(new THREE.BoxGeometry(0.003,0.022,0.007),gMat);
  gripL.position.set(-0.007,ARMCFG[4].h+0.01,0);
  gripR=gripL.clone();gripR.position.x=0.007;
  armJoints[4].add(gripL);armJoints[4].add(gripR);

  // Mouse orbit
  const cv=ren3.domElement;
  cv.addEventListener('mousedown',e=>{orb.drag=true;orb.x=e.clientX;orb.y=e.clientY});
  cv.addEventListener('mousemove',e=>{if(!orb.drag)return;orb.t+=(e.clientX-orb.x)*0.007;orb.p=Math.max(0.1,Math.min(1.4,orb.p+(e.clientY-orb.y)*0.007));orb.x=e.clientX;orb.y=e.clientY;updCam3()});
  cv.addEventListener('mouseup',()=>orb.drag=false);
  cv.addEventListener('mouseleave',()=>orb.drag=false);
  cv.addEventListener('wheel',e=>{orb.d=Math.max(0.15,Math.min(0.8,orb.d+e.deltaY*0.0008));updCam3();e.preventDefault()},{passive:false});

  new ResizeObserver(()=>{const w=ct.clientWidth,h=ct.clientHeight;if(w>10&&h>10){cam3.aspect=w/h;cam3.updateProjectionMatrix();ren3.setSize(w,h)}}).observe(ct);
  console.log('KCC16b: Luxury arm initialized');
}

function updCam3(){
  if(!cam3)return;
  cam3.position.set(orb.d*Math.cos(orb.p)*Math.sin(orb.t),orb.d*Math.sin(orb.p)+0.08,orb.d*Math.cos(orb.p)*Math.cos(orb.t));
  cam3.lookAt(0,0.12,0);
}

function updateArm3D(){
  if(!armJoints.length)return;
  const d=Math.PI/180,s=armState;
  if(armJoints[0])armJoints[0].rotation.y=(s[0]||0)*d*0.02;
  if(armJoints[1])armJoints[1].rotation.z=(s[1]||0)*d*0.012;
  if(armJoints[2])armJoints[2].rotation.z=(s[2]||0)*d*0.01;
  if(armJoints[3])armJoints[3].rotation.z=(s[3]||0)*d*0.008;
  if(armJoints[4])armJoints[4].rotation.y=(s[4]||0)*d*0.01;
  if(gripL&&gripR){const g=Math.max(0.003,Math.abs((s[5]||0)*0.0002));gripL.position.x=-g;gripR.position.x=g}
}

function animate3D(){requestAnimationFrame(animate3D);if(!ren3||!sc3||!cam3)return;updateArm3D();ren3.render(sc3,cam3)}

// Telemetry
async function pollTelemetry(){
  try{const r=await get('/telemetry');if(r.ok&&r.state)armState=r.state}catch{}
  setTimeout(pollTelemetry,66);
}

// ═══════════════════════════════════════
// LOG COPY / EXPORT
// ═══════════════════════════════════════
function copyLog(){navigator.clipboard?.writeText(allLogs.join('\n')).then(()=>{const b=$('#btn-lc');if(b)flash(b,'✓')})}
function exportLog(){const b=new Blob([allLogs.join('\n')],{type:'text/plain'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=`kcc_log_${new Date().toISOString().slice(0,16).replace(/:/g,'-')}.txt`;a.click()}

// ═══════════════════════════════════════
// ACTIONS
// ═══════════════════════════════════════
const cs=()=>({hf_org:$('#hf_org').value.trim(),hf_repo_name:$('#hf_repo').value.trim(),task_description:$('#hf_task').value,target_episodes:parseInt($('#ep_tgt').value,10)});

const A={
  toggleRec(){if(LS?.state==='recording')post('/stop_recording');else post('/start_recording')},
  save(){post('/save')},discard(){post('/discard')},rerecord(){post('/rerecord')},
  toggleTeleop(){if(LS?.state==='teleop')post('/stop_teleop');else post('/start_teleop')},
  verify(){fetchStats()},
  epUp(){post('/set_episode_count',{count:+$('#ep_done').value+1})},
  epDown(){post('/set_episode_count',{count:Math.max(0,+$('#ep_done').value-1)})},
  reconnect(){post('/reconnect')},
  init(){post('/settings',cs()).then(()=>post('/init_dataset',cs()).then(r=>{if(!r.ok)alert(r.error||'');else fetchStats()}))},
};

// ═══════════════════════════════════════
// KEYBOARD
// ═══════════════════════════════════════
document.onkeydown=e=>{
  if(e.target.tagName==='INPUT')return;
  // Escape closes popup first
  if(e.key==='Escape'){
    e.preventDefault();
    const m=$('#gp-modal');
    if(m&&m.style.display!=='none'){gpCloseModal();return}
    A.discard();return;
  }
  const map={' ':A.toggleRec,'F2':A.toggleRec,'Enter':A.save,'F3':A.save,'F4':A.discard,
    'r':A.rerecord,'R':A.rerecord,'F6':A.rerecord,'t':A.toggleTeleop,'T':A.toggleTeleop,'F7':A.toggleTeleop,
    'v':A.verify,'V':A.verify,'i':A.init,'I':A.init,'F8':A.epDown,'F9':A.epUp};
  if(map[e.key]){e.preventDefault();map[e.key]()}
};

// ═══════════════════════════════════════
// GAMEPAD CONFIG SYSTEM
// ═══════════════════════════════════════
const GP_ACTIONS=[
  {id:'toggleRec',label:'Record Toggle',fn:()=>A.toggleRec()},
  {id:'save',label:'Save Episode',fn:()=>A.save()},
  {id:'discard',label:'Discard',fn:()=>A.discard()},
  {id:'rerecord',label:'Rerecord',fn:()=>A.rerecord()},
  {id:'toggleTeleop',label:'Teleop Toggle',fn:()=>A.toggleTeleop()},
  {id:'verify',label:'Verify Dataset',fn:()=>A.verify()},
  {id:'epDown',label:'Episode -1',fn:()=>A.epDown()},
  {id:'epUp',label:'Episode +1',fn:()=>A.epUp()},
  {id:'reconnect',label:'Reconnect',fn:()=>A.reconnect()},
];
const GP_DEFAULTS={0:'toggleRec',1:'save',2:'discard',3:'rerecord',4:'toggleTeleop',5:'verify',6:'epDown',7:'epUp',8:'reconnect'};
let gpMap={},gpConnected=false,gpName='',gpMapping=false,gpWizIdx=0,gpRemapTgt=null,gpPrev=new Array(20).fill(false);

function gpLoad(id){try{const s=localStorage.getItem('kcc_gp_'+id.replace(/[^a-zA-Z0-9]/g,'_').slice(0,50));if(s){gpMap=JSON.parse(s);return true}}catch{}return false}
function gpSave(id){try{localStorage.setItem('kcc_gp_'+id.replace(/[^a-zA-Z0-9]/g,'_').slice(0,50),JSON.stringify(gpMap))}catch{}}
function gpLoadDef(){gpMap={};for(const[b,a]of Object.entries(GP_DEFAULTS))gpMap[parseInt(b)]=a}

function gpUpdBadge(){const b=$('#gp-badge');if(!b)return;if(gpMapping){b.textContent='🎮 mapping...';b.className='bd gp-badge mapping'}else if(gpConnected){b.textContent='🎮 '+gpName.slice(0,18);b.className='bd gp-badge connected'}else{b.textContent='🎮 none';b.className='bd gp-badge'}}

function gpOpenModal(){const m=$('#gp-modal');if(m){m.style.display='flex';gpRenderPopup()}}
function gpCloseModal(){const m=$('#gp-modal');if(m)m.style.display='none';gpMapping=false;gpUpdBadge()}

function gpRenderPopup(){
  const body=$('#gp-popup-body');if(!body)return;
  if(!gpConnected){body.innerHTML='<div class="gp-no">No gamepad connected right now.</div><div class="gp-note">Plug in a gamepad anytime — detected automatically.<br><br>⌨ Keyboard works perfectly without a gamepad.</div>';return}
  if(gpMapping){
    const act=gpRemapTgt?GP_ACTIONS.find(a=>a.id===gpRemapTgt):GP_ACTIONS[gpWizIdx];
    body.innerHTML=`<div class="gp-name">${gpName}</div><div class="gp-wizard"><div class="gp-wizard-hint">Press the button for:</div><div class="gp-wizard-action">${act.label}</div><div class="gp-wizard-waiting">Waiting... ${gpRemapTgt?'':'('+( gpWizIdx+1)+'/'+GP_ACTIONS.length+')'}</div></div><div class="gp-btns">${gpRemapTgt?'<button class="gp-btn-ghost" onclick="gpRemapTgt=null;gpMapping=false;gpUpdBadge();gpRenderPopup()">Cancel</button>':'<button class="gp-btn-ghost" onclick="gpWizSkip()">Skip</button><button class="gp-btn-ghost" onclick="gpWizCancel()">Cancel</button>'}</div><div class="gp-note">⌨ Keyboard works as usual even with joystick mapped.</div>`;
    return;
  }
  let rows='';for(const a of GP_ACTIONS){const b=Object.entries(gpMap).find(([k,v])=>v===a.id);rows+=`<div class="gp-map-row"><span class="gp-map-action">${a.label}</span><span><span class="gp-map-btn">${b?'Button '+b[0]:'—'}</span><button class="gp-remap" onclick="gpRemapOne('${a.id}')">remap</button></span></div>`}
  body.innerHTML=`<div class="gp-name">Connected: ${gpName}</div>${Object.keys(gpMap).length?'<div class="gp-preset">✓ Loaded saved preset</div>':''}<div class="gp-map-list">${rows}</div><div class="gp-btns"><button class="gp-btn-accent" onclick="gpStartWiz()">Remap All</button><button class="gp-btn-ghost" onclick="gpLoadDef();gpSave(gpName);gpRenderPopup()">Reset</button><button class="gp-btn-ghost" onclick="gpCloseModal()">Done</button></div><div class="gp-note">⌨ Keyboard works as usual even with joystick mapped.</div>`;
}

function gpStartWiz(){gpMap={};gpMapping=true;gpWizIdx=0;gpRemapTgt=null;gpUpdBadge();gpRenderPopup()}
function gpWizSkip(){gpWizIdx++;if(gpWizIdx>=GP_ACTIONS.length){gpMapping=false;gpSave(gpName);gpUpdBadge()}gpRenderPopup()}
function gpWizCancel(){gpMapping=false;gpLoadDef();gpUpdBadge();gpRenderPopup()}
function gpRemapOne(aid){gpRemapTgt=aid;gpMapping=true;gpUpdBadge();gpRenderPopup()}

function gpPoll(){
  const gps=navigator.getGamepads?.();const gp=gps?.[0]||gps?.[1]||gps?.[2]||gps?.[3];
  if(!gp){if(gpConnected){gpConnected=false;gpName='';gpUpdBadge()}requestAnimationFrame(gpPoll);return}
  if(!gpConnected){
    gpConnected=true;gpName=gp.id||'Unknown';
    const had=gpLoad(gpName);if(!had){gpLoadDef();gpSave(gpName);gpUpdBadge();gpOpenModal()}else{gpUpdBadge()}
  }
  const btn=i=>gp.buttons[i]?.pressed,was=i=>gpPrev[i];
  if(gpMapping){
    for(let i=0;i<gp.buttons.length;i++){
      if(btn(i)&&!was(i)){
        if(gpRemapTgt){Object.keys(gpMap).forEach(k=>{if(gpMap[k]===gpRemapTgt)delete gpMap[k]});gpMap[i]=gpRemapTgt;gpRemapTgt=null;gpMapping=false;gpSave(gpName);gpUpdBadge();gpRenderPopup()}
        else{Object.keys(gpMap).forEach(k=>{if(gpMap[k]===GP_ACTIONS[gpWizIdx].id)delete gpMap[k]});gpMap[i]=GP_ACTIONS[gpWizIdx].id;gpWizIdx++;if(gpWizIdx>=GP_ACTIONS.length){gpMapping=false;gpSave(gpName);gpUpdBadge()}gpRenderPopup()}
        break;
      }
    }
  } else {
    for(const[bi,aid]of Object.entries(gpMap)){const i=parseInt(bi);if(btn(i)&&!was(i)){const a=GP_ACTIONS.find(x=>x.id===aid);if(a)a.fn()}}
  }
  gpPrev=Array.from({length:20},(_,i)=>btn(i));
  requestAnimationFrame(gpPoll);
}

// ═══════════════════════════════════════
// BUTTON WIRING
// ═══════════════════════════════════════
function wire(){
  const on=(id,fn)=>{const e=$(id);if(e)e.onclick=fn};
  on('#btn-rec',A.toggleRec);on('#btn-stop',A.toggleRec);
  on('#btn-sav',A.save);on('#btn-dis',()=>{if(confirm('discard?'))A.discard()});on('#btn-redo',A.rerecord);
  on('#btn-recon',A.reconnect);
  on('#btn-apl',async()=>{const r=await post('/settings',cs());flash($('#btn-apl'),r.ok?'OK':'err')});
  on('#btn-ini',A.init);
  on('#btn-tl-on',()=>post('/start_teleop'));on('#btn-tl-off',()=>post('/stop_teleop'));
  on('#btn-sd',async()=>{await post('/set_episode_count',{count:+$('#ep_done').value});flash($('#btn-sd'),'✓')});
  on('#btn-st',async()=>{await post('/settings',{target_episodes:+$('#ep_tgt').value});flash($('#btn-st'),'✓')});
  on('#btn-sn',async()=>{await post('/set_next_episode',{next:+$('#ep_nxt').value});flash($('#btn-sn'),'✓')});
  on('#btn-ver',A.verify);
  on('#btn-lc',copyLog);on('#btn-le',exportLog);
}

// ═══════════════════════════════════════
// BOOT
// ═══════════════════════════════════════
wire();
initChart();
init3D();
animate3D();
poll();
gpPoll();
pollTelemetry();
gpUpdBadge();
