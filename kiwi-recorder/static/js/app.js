
/* ═══════ AXIS MAPPING (built-in AntiMicro) ═══════ */
let axisMap = {};
const AXIS_DEFAULTS = {
  "0": {"neg": "a", "pos": "d", "label": "Strafe L/R"},
  "1": {"neg": "w", "pos": "s", "label": "Forward/Back"},
  "2": {"neg": "z", "pos": "x", "label": "Rotate"}
};
function loadAxisMap(){try{const s=localStorage.getItem('kcc_axis_map');if(s){axisMap=JSON.parse(s);return}}catch{}axisMap=JSON.parse(JSON.stringify(AXIS_DEFAULTS))}
function saveAxisMap(){try{localStorage.setItem('kcc_axis_map',JSON.stringify(axisMap))}catch{}}
loadAxisMap();
/* KCC Recorder — Complete App.js (Final) */
const POLL=500;
let LS=null,RC=[],CH=null,LV=-1,allLogs=[];
let armState=[0,-45,-30,20,0,0,0,0,0];
let chartBuf=[];
const CHART_WIN=150;
let _gp=null; // global gamepad reference

const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const post=async(p,b)=>{try{const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):'{}'});return await r.json()}catch{return{}}};
const get=async p=>{try{return(await fetch(p)).json()}catch{return{}}};
const badge=(k,t,c='')=>{const e=$(`.bd[data-key="${k}"]`);if(e){e.textContent=t;e.className='bd'+(c?' '+c:'')}};
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const flash=(b,t)=>{if(!b)return;const o=b.textContent;b.textContent=t;setTimeout(()=>b.textContent=o,1e3)};

/* ═══════ CAMERAS ═══════ */
function renderCams(c,st){
  if(!(c.length===RC.length&&c.every((x,i)=>x===RC[i]))){
    const r=$('#cam-row');if(!r)return;r.innerHTML='';
    c.forEach(n=>{const d=document.createElement('div');d.className='cm';
      d.innerHTML='<img src="/camera/'+n+'.mjpg"/><span class="cl">observation.images.'+n+'</span><span class="cs" data-cs="'+n+'">live</span>';
      r.appendChild(d)});RC=c.slice();
  }
  $$('.cm').forEach(t=>{t.classList.toggle('xv',st==='review');t.classList.toggle('xr',st==='recording')});
  $$('[data-cs]').forEach(e=>{const r=st==='recording',v=st==='review';
    e.textContent=r?'rec':v?'preview':'live';e.className='cs '+(r?'recording':v?'review':'live')});
}

/* ═══════ STATUS ═══════ */
async function poll(){const s=await get('/status');if(s&&s.state){LS=s;sync(s)}else badge('state','offline','er');setTimeout(poll,POLL)}
function sync(s){
  badge('state',s.state,s.state==='recording'?'er':s.state==='review'?'wn':['teleop','finished'].includes(s.state)?'li':['error','disconnected'].includes(s.state)?'er':'');
  badge('cameras',(s.cameras||[]).join(', ')||'—',(s.cameras||[]).length?'ok':'wn');
  badge('dataset',s.dataset_initialized?s.hf_org+'/'+s.hf_repo_name:'—',s.dataset_initialized?'ok':'');
  renderCams(s.cameras||[],s.state);
  const u=(id,v)=>{const e=document.getElementById(id);if(e&&document.activeElement!==e)e.value=v};
  u('ep_done',s.episodes_done);u('ep_tgt',s.target_episodes);u('ep_nxt',(s.episodes_done||0)+1);
  const pf=$('#pf');if(pf)pf.style.width=(s.target_episodes>0?Math.min(100,s.episodes_done/s.target_episodes*100):0)+'%';
  const I=s.state==='idle',T=s.state==='teleop',R=s.state==='recording',V=s.state==='review',E=['error','disconnected'].includes(s.state);
  const dis=(id,v)=>{const e=$(id);if(e)e.disabled=v};const h=(id,v)=>{const e=$(id);if(e)e.hidden=v};
  dis('#btn-rec',R||!(I||T)||!s.dataset_initialized||E);dis('#btn-stop',!R);
  h('#rv',!V);dis('#btn-ini',R||V);h('#btn-recon',!E);dis('#btn-tl-on',!(I&&!E));dis('#btn-tl-off',!T);
  if(s.episodes_done>LV&&s.dataset_initialized&&s.state==='idle'){LV=s.episodes_done;fetchStats()}
  const rm=$('#rm');if(rm)rm.textContent=(s.current_episode_seconds||0).toFixed(1)+'s · '+(s.episodes_done||0)+'/'+(s.target_episodes||50);
  if(s.log_tail){allLogs=s.log_tail;const l=$('#log');if(l){l.innerHTML=s.log_tail.slice(-6).map(x=>'<div class="line">'+esc(x)+'</div>').join('');l.scrollTop=l.scrollHeight}}
}

/* ═══════ INSPECTOR ═══════ */
async function fetchStats(){const s=await get('/dataset_stats');if(!s||!s.ok)return;
  const sv=(id,v,c)=>{const e=$(id);if(e){e.textContent=v||'—';if(c)e.className='iv '+c}};
  sv('#i-ep',s.total_episodes,s.total_episodes>0?'ok':'');sv('#i-fr',s.total_frames);
  sv('#i-dur',s.last_ep_duration?s.last_ep_duration.toFixed(1)+'s':'—');sv('#i-arm',s.arm_range);
  sv('#i-wh',s.wheel_range,s.wheels_still?'ok':'wn');
  sv('#i-ent',s.entanglement!=null?'E='+s.entanglement.toFixed(3):'—',s.entanglement!=null&&s.entanglement<0.05?'ok':s.entanglement>0.3?'wn':'');
  sv('#i-pq',s.parquet_ok?'OK':'—',s.parquet_ok?'ok':'er');sv('#i-vid',s.videos_ok?'OK':'—',s.videos_ok?'ok':'er')}

/* ═══════ LIVE CHART ═══════ */
function initChart(){const x=$('#action-chart');if(!x||typeof Chart==='undefined')return;
  const n=['s_pan','s_lift','elbow','w_flex','w_roll','grip'],c=['#E05A47','#47A05E','#4785C4','#D4953A','#9D6AC4','#2DB5A0'];
  CH=new Chart(x,{type:'line',data:{labels:Array(CHART_WIN).fill(''),datasets:n.map((l,i)=>({label:l,data:Array(CHART_WIN).fill(null),borderColor:c[i],borderWidth:1.5,pointRadius:0,tension:0.3}))},
    options:{responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{position:'bottom',labels:{font:{size:8,family:'JetBrains Mono'},boxWidth:8,padding:4}}},scales:{x:{display:false},y:{ticks:{font:{size:7}}}}}})}
function feedChart(s){if(!CH||!s||s.length<6)return;chartBuf.push(s.slice(0,6));if(chartBuf.length>CHART_WIN)chartBuf.shift();for(let j=0;j<6;j++)CH.data.datasets[j].data=chartBuf.map(r=>r[j]);CH.update()}

/* ═══════ 2D ARM CANVAS ═══════ */
let armCtx,armCanvas,armIdle=0,armHasData=false;
function initArm(){armCanvas=$('#arm-viz');if(!armCanvas)return;armCtx=armCanvas.getContext('2d');drawArm()}
function drawArm(){
  requestAnimationFrame(drawArm);if(!armCtx)return;
  const dpr=window.devicePixelRatio||1,W=armCanvas.width=armCanvas.clientWidth*dpr,H=armCanvas.height=armCanvas.clientHeight*dpr,sc=Math.min(W,H)/210,ctx=armCtx;
  const bg=ctx.createRadialGradient(W/2,H/2,0,W/2,H/2,Math.max(W,H)*0.7);bg.addColorStop(0,'#FAFAF8');bg.addColorStop(1,'#F0EEEA');ctx.fillStyle=bg;ctx.fillRect(0,0,W,H);
  ctx.fillStyle='#DDD8D0';const gap=25*sc;for(let gx=gap;gx<W;gx+=gap)for(let gy=gap;gy<H;gy+=gap){ctx.beginPath();ctx.arc(gx,gy,1,0,Math.PI*2);ctx.fill()}
  const s=armState,DEG=Math.PI/180,hasData=s.some(v=>v!==0);let angles;
  if(hasData){armHasData=true;angles=[(s[1]||0)*DEG,(s[2]||0)*DEG,(s[3]||0)*DEG,(s[4]||0)*DEG]}else{armIdle+=0.02;angles=[-0.5+Math.sin(armIdle)*0.4,Math.sin(armIdle*1.3)*0.4,Math.sin(armIdle*0.9)*0.3,Math.sin(armIdle*0.7)*0.2]}
  const LINKS=[65*sc,58*sc,50*sc,35*sc],COLORS=['#E8453C','#2EA85A','#3068D0','#E89020'],WIDTHS=[10*sc,9*sc,8*sc,6*sc],baseX=W*0.4,baseY=H*0.92;
  ctx.save();ctx.shadowColor='rgba(0,0,0,0.1)';ctx.shadowBlur=8*sc;ctx.shadowOffsetY=2*sc;ctx.fillStyle='#666';const bw=40*sc,bh=8*sc;ctx.beginPath();ctx.moveTo(baseX-bw/2,baseY);ctx.lineTo(baseX+bw/2,baseY);ctx.lineTo(baseX+bw/2-4*sc,baseY+bh);ctx.lineTo(baseX-bw/2+4*sc,baseY+bh);ctx.closePath();ctx.fill();ctx.restore();
  let x=baseX,y=baseY,angle=-Math.PI/2+angles[0];
  for(let i=0;i<4;i++){const nx=x+Math.cos(angle)*LINKS[i],ny=y+Math.sin(angle)*LINKS[i],dx=nx-x,dy=ny-y,len=Math.sqrt(dx*dx+dy*dy),ux=dx/len,uy=dy/len,lw=WIDTHS[i]/50*3,px=-uy*lw/2,py=ux*lw/2;
    ctx.save();ctx.shadowColor=COLORS[i]+'25';ctx.shadowBlur=16*sc;const g=ctx.createLinearGradient(x,y,nx,ny);g.addColorStop(0,COLORS[i]);g.addColorStop(1,COLORS[i]+'BB');ctx.fillStyle=g;ctx.beginPath();ctx.moveTo(x+px,y+py);ctx.lineTo(nx+px,ny+py);ctx.lineTo(nx-px,ny-py);ctx.lineTo(x-px,y-py);ctx.closePath();ctx.fill();ctx.strokeStyle='rgba(255,255,255,0.35)';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x+px,y+py);ctx.lineTo(nx+px,ny+py);ctx.stroke();ctx.restore();
    ctx.save();ctx.shadowColor='rgba(0,0,0,0.12)';ctx.shadowBlur=6*sc;const jr=Math.max(6,(i===0?12:9)*sc/50);ctx.fillStyle='#FFF';ctx.beginPath();ctx.arc(x,y,jr+2,0,Math.PI*2);ctx.fill();ctx.fillStyle=i===0?'#555':COLORS[i];ctx.beginPath();ctx.arc(x,y,jr,0,Math.PI*2);ctx.fill();ctx.fillStyle='rgba(255,255,255,0.4)';ctx.beginPath();ctx.arc(x-jr*0.25,y-jr*0.25,jr*0.4,0,Math.PI*2);ctx.fill();ctx.restore();
    if(i>0&&hasData){ctx.strokeStyle=COLORS[i]+'55';ctx.lineWidth=1.5;const pa=angle-angles[i],ar=15*sc/50*3;ctx.beginPath();ctx.arc(x,y,ar,pa,angle,angles[i]<0);ctx.stroke();ctx.font=Math.max(8,9*sc/50)+'px JetBrains Mono';ctx.fillStyle=COLORS[i];const mid=(pa+angle)/2;ctx.fillText(Math.round(s[i+1]||0)+'°',x+Math.cos(mid)*ar*1.5-8,y+Math.sin(mid)*ar*1.5+3)}
    x=nx;y=ny;if(i<3)angle+=angles[i+1]}
  ctx.save();ctx.shadowColor='rgba(232,40,20,0.3)';ctx.shadowBlur=12*sc;ctx.fillStyle='#E82814';ctx.beginPath();ctx.arc(x,y,Math.max(8,13*sc/50),0,Math.PI*2);ctx.fill();ctx.fillStyle='rgba(255,255,255,0.35)';ctx.beginPath();ctx.arc(x-2,y-2,Math.max(2,4*sc/50),0,Math.PI*2);ctx.fill();ctx.restore();
  const gO=(Math.abs(s[5]||30)*0.12+4)*sc/50;ctx.strokeStyle='#0EA878';ctx.lineWidth=Math.max(3,5*sc/50);ctx.lineCap='round';ctx.beginPath();ctx.moveTo(x+Math.cos(angle+0.5)*gO*3,y+Math.sin(angle+0.5)*gO*3);ctx.lineTo(x,y);ctx.lineTo(x+Math.cos(angle-0.5)*gO*3,y+Math.sin(angle-0.5)*gO*3);ctx.stroke();
  ctx.font='600 '+Math.max(9,10*sc/50)+'px JetBrains Mono';ctx.fillStyle=hasData?'#2EA85A':'#999';ctx.fillText(hasData?'● LIVE':'○ IDLE',8*sc/50,16*sc/50);
  if(hasData){const nm=['pan','lift','elbow','wrist','roll','grip'];ctx.font=Math.max(7,8*sc/50)+'px JetBrains Mono';for(let i=0;i<6;i++){ctx.fillStyle=i<4?COLORS[Math.min(i,3)]:'#888';ctx.fillText(nm[i]+': '+(s[i]||0).toFixed(1)+'°',W-65*sc/50,(12+i*11)*sc/50)}}
  const ts=$('#telem-status');if(ts)ts.textContent=hasData?'live':'waiting for data...';
}

/* ═══════ TELEMETRY ═══════ */
async function pollTelem(){const r=await get('/telemetry');if(r&&r.ok&&r.state){armState=r.state;feedChart(r.state)}setTimeout(pollTelem,100)}

/* ═══════ LOG ═══════ */
function copyLog(){navigator.clipboard?.writeText(allLogs.join('\n')).then(()=>flash($('#btn-lc'),'✓'))}
function exportLog(){const b=new Blob([allLogs.join('\n')],{type:'text/plain'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='kcc_log.txt';a.click()}

/* ═══════ ACTIONS ═══════ */
const cs=()=>({hf_org:$('#hf_org')?.value?.trim()||'',hf_repo_name:$('#hf_repo')?.value?.trim()||'',task_description:$('#hf_task')?.value||'',target_episodes:parseInt($('#ep_tgt')?.value||50,10)});
const A={
  startRec(){post('/start_recording')},stopRec(){post('/stop_recording')},save(){post('/save')},discard(){post('/discard')},
  rerecord(){post('/rerecord')},toggleTeleop(){if(LS?.state==='teleop')post('/stop_teleop');else post('/start_teleop')},
  verify(){fetchStats()},epUp(){post('/set_episode_count',{count:+(document.getElementById('ep_done')?.value||0)+1})},
  epDown(){post('/set_episode_count',{count:Math.max(0,+(document.getElementById('ep_done')?.value||0)-1)})},
  reconnect(){post('/reconnect')},
  init(){post('/settings',cs()).then(()=>post('/init_dataset',cs()).then(r=>{if(r&&!r.ok)alert(r.error||'init failed');else fetchStats()}))}
};

/* ═══════ KEYBOARD ═══════ */
document.onkeydown=e=>{if(e.target.tagName==='INPUT')return;
  if(e.key==='Escape'){e.preventDefault();const m=$('#gp-modal');if(m&&m.style.display!=='none'){gpCloseModal();return}A.discard();return}
  const map={' ':A.startRec,'F2':A.startRec,'Enter':A.save,'F3':A.save,'F4':A.discard,'r':A.rerecord,'R':A.rerecord,'F6':A.rerecord,
    't':A.toggleTeleop,'T':A.toggleTeleop,'F7':A.toggleTeleop,'v':A.verify,'V':A.verify,'i':A.init,'I':A.init,'F8':A.epDown,'F9':A.epUp};
  if(map[e.key]){e.preventDefault();map[e.key]()}};

/* ═══════ GAMEPAD SYSTEM ═══════ */
const GP_ACTIONS=[
  {id:'startRec',label:'Start Recording',fn:A.startRec},{id:'stopRec',label:'Stop Recording',fn:A.stopRec},
  {id:'save',label:'Save',fn:A.save},{id:'discard',label:'Discard',fn:A.discard},
  {id:'rerecord',label:'Rerecord',fn:A.rerecord},{id:'toggleTeleop',label:'Teleop Toggle',fn:A.toggleTeleop},
  {id:'verify',label:'Verify',fn:A.verify},{id:'epDown',label:'Episode -1',fn:A.epDown},{id:'epUp',label:'Episode +1',fn:A.epUp}
];
const GP_DEF={0:'startRec',1:'stopRec',2:'save',3:'discard',4:'rerecord',5:'toggleTeleop',6:'verify',7:'epDown',8:'epUp'};
let gpMap={},gpOn=false,gpNm='',gpMapping=false,gpWI=0,gpRT=null,gpPrev=new Array(20).fill(false);

function gpLoad(id){try{const s=localStorage.getItem('kcc_gp_'+id.replace(/[^a-zA-Z0-9]/g,'_').slice(0,50));if(s){gpMap=JSON.parse(s);return true}}catch{}return false}
function gpSave(id){try{localStorage.setItem('kcc_gp_'+id.replace(/[^a-zA-Z0-9]/g,'_').slice(0,50),JSON.stringify(gpMap))}catch{}}
function gpDefaults(){gpMap={};for(const[b,a]of Object.entries(GP_DEF))gpMap[parseInt(b)]=a}
function gpBadge(){const b=$('#gp-badge');if(!b)return;b.textContent=gpMapping?'🎮 mapping...':gpOn?'🎮 '+gpNm.slice(0,18):'🎮 none';b.className='bd gp-badge'+(gpMapping?' mapping':gpOn?' connected':'')}
function gpOpenModal(){const m=$('#gp-modal');if(m)m.style.display='flex'}
function gpCloseModal(){const m=$('#gp-modal');if(m)m.style.display='none';gpMapping=false;gpBadge();const w=$('#mapper-wizard');if(w)w.style.display='none'}

function gpStartWiz(){gpMap={};gpMapping=true;gpWI=0;gpRT=null;gpBadge();
  const a=$('#wiz-action');if(a)a.textContent=GP_ACTIONS[0]?.label||'';
  const p=$('#wiz-progress');if(p)p.textContent='1 / '+GP_ACTIONS.length;
  const w=$('#mapper-wizard');if(w)w.style.display='flex'}
function gpWizSkip(){gpWI++;if(gpWI>=GP_ACTIONS.length){gpMapping=false;gpSave(gpNm);gpBadge();const w=$('#mapper-wizard');if(w)w.style.display='none';return}
  const a=$('#wiz-action');if(a)a.textContent=GP_ACTIONS[gpWI]?.label||'';
  const p=$('#wiz-progress');if(p)p.textContent=(gpWI+1)+' / '+GP_ACTIONS.length}
function gpWizCancel(){gpMapping=false;gpDefaults();gpBadge();const w=$('#mapper-wizard');if(w)w.style.display='none'}
function gpRemapOne(aid){gpRT=aid;gpMapping=true;gpBadge();
  const a=$('#wiz-action');if(a)a.textContent=GP_ACTIONS.find(x=>x.id===aid)?.label||'';
  const p=$('#wiz-progress');if(p)p.textContent='Single remap';
  const w=$('#mapper-wizard');if(w)w.style.display='flex'}

/* ═══════ MAPPER RENDERER ═══════ */
function gpRenderMapper(){
  const dev=$('#mapper-device');
  // Fetch live state from Python joystick reader
  get('/joystick/state').then(s=>{
    if(!s||!s.ok){
      if(dev)dev.textContent='No joystick detected';
      return;
    }
    if(dev)dev.textContent=gpOn?gpNm:'Joystick connected';
    const axes=s.axes||[];
    const cfg=s.config||{};
    const axMap=cfg.axes||{};
    const dz=cfg.deadzone||0.15;

    // Render axes with mapping
    const ax=$('#mapper-axes');if(ax){let h='';
      for(let i=0;i<Math.min(axes.length,6);i++){
        const v=axes[i]||0;const pct=Math.abs(v)*50;
        const col=v>=0?'#3D348B':'#A06D1B';const dir=v>=0?'left:50%':'right:50%';
        const am=axMap[i]||{};const nk=(am.neg||'—').toUpperCase();const pk=(am.pos||'—').toUpperCase();
        const active=Math.abs(v)>dz;const lbl=am.label||'';
        h+='<div class="mapper-row'+(active?' active':'')+'"><span class="mapper-row-label">Axis '+(i+1)+(lbl?' · '+lbl:'')+'</span><span style="display:flex;align-items:center;gap:5px"><span style="font:10px JetBrains Mono;color:#666;width:36px;text-align:right">'+v.toFixed(2)+'</span><span style="width:60px;height:8px;background:#E8E4DE;border-radius:4px;position:relative;overflow:hidden"><span style="position:absolute;top:0;height:100%;background:'+col+';border-radius:4px;'+dir+';width:'+pct+'%"></span></span><span style="font:bold 10px JetBrains Mono;color:#3D348B;width:50px">-'+nk+' +'+pk+'</span><button class="mapper-row-remap" onclick="axisRemap('+i+')">keys</button></span></div>'}
      ax.innerHTML=h}

    // Render buttons
    const bt=$('#mapper-buttons');if(bt){let h='';
      for(const act of GP_ACTIONS){const en=Object.entries(gpMap).find(([k,v])=>v===act.id);
        const bi=en?parseInt(en[0]):-1;const pressed=bi>=0&&s.buttons?(s.buttons&(1<<bi)):false;
        h+='<div class="mapper-row'+(pressed?' active':'')+'"><span class="mapper-row-label"><span class="dot '+(pressed?'on':'off')+'"></span>'+act.label+'</span><span style="display:flex;align-items:center;gap:4px"><span class="mapper-row-value">'+(en?'Btn '+en[0]:'—')+'</span><button class="mapper-row-remap" onclick="gpRemapOne(\''+act.id+'\')">remap</button></span></div>'}
      bt.innerHTML=h}

    // Canvas
    drawJoystickCanvas2(axes,s.buttons||0);
  });
}

function drawJoystickCanvas(){
  const c=$('#mapper-canvas');if(!c)return;const ctx=c.getContext('2d'),dpr=window.devicePixelRatio||1;
  const W=c.width=c.clientWidth*dpr,H=c.height=c.clientHeight*dpr;
  ctx.fillStyle='#F0EDE8';ctx.fillRect(0,0,W,H);
  const gp=_gp;if(!gp){ctx.font='13px JetBrains Mono';ctx.fillStyle='#AAA';ctx.textAlign='center';ctx.fillText('No gamepad',W/2,H/2);return}
  const sc=W/260;
  ctx.fillStyle='#E0DBD4';ctx.strokeStyle='#C8C0B5';ctx.lineWidth=1.5;rr(ctx,W*.12,H*.03,W*.76,H*.94,10*sc);ctx.fill();ctx.stroke();
  // Stick
  const sx=W/2,sy=H*.22,sr=40*sc;ctx.fillStyle='#D5CEC6';ctx.beginPath();ctx.arc(sx,sy,sr,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#B8B0A5';ctx.lineWidth=1;ctx.stroke();
  ctx.strokeStyle='#C8C0BB';ctx.lineWidth=.5;ctx.beginPath();ctx.moveTo(sx-sr,sy);ctx.lineTo(sx+sr,sy);ctx.stroke();ctx.beginPath();ctx.moveTo(sx,sy-sr);ctx.lineTo(sx,sy+sr);ctx.stroke();
  const ax=gp.axes[0]||0,ay=gp.axes[1]||0;
  ctx.save();ctx.shadowColor='rgba(61,52,139,.4)';ctx.shadowBlur=8;ctx.fillStyle='#3D348B';ctx.beginPath();ctx.arc(sx+ax*sr*.75,sy+ay*sr*.75,9*sc,0,Math.PI*2);ctx.fill();ctx.restore();
  ctx.font=8*sc+'px JetBrains Mono';ctx.fillStyle='#888';ctx.textAlign='center';ctx.fillText('X:'+ax.toFixed(2)+' Y:'+ay.toFixed(2),sx,sy+sr+14*sc);
  // Twist
  if(gp.axes.length>2){const tw=gp.axes[2]||0,ty=H*.42,tw2=W*.55,th=10*sc,tx=W/2-tw2/2;ctx.fillStyle='#D5CEC6';rr(ctx,tx,ty,tw2,th,5);ctx.fill();
    const fw=Math.abs(tw)*tw2/2;ctx.fillStyle=tw>=0?'#3D348B':'#A06D1B';if(tw>=0)ctx.fillRect(W/2,ty,fw,th);else ctx.fillRect(W/2-fw,ty,fw,th);
    ctx.font=8*sc+'px JetBrains Mono';ctx.fillStyle='#888';ctx.textAlign='center';ctx.fillText('Twist: '+tw.toFixed(2),W/2,ty+th+12*sc)}
  // Buttons
  const by0=H*.56,br=11*sc,cols=4,gap2=20*sc,totalW=cols*br*2+(cols-1)*gap2,bx0=W/2-totalW/2+br;
  for(let i=0;i<Math.min(gp.buttons.length,16);i++){const row=Math.floor(i/cols),col=i%cols,bx=bx0+col*(br*2+gap2),by=by0+row*(br*2+gap2),pr=gp.buttons[i]?.pressed;
    ctx.save();if(pr){ctx.shadowColor='rgba(61,52,139,.5)';ctx.shadowBlur=8}ctx.fillStyle=pr?'#3D348B':'#D8D2CA';ctx.beginPath();ctx.arc(bx,by,br,0,Math.PI*2);ctx.fill();ctx.strokeStyle=pr?'#5548B5':'#C0B8AE';ctx.lineWidth=1;ctx.stroke();ctx.restore();
    ctx.font=(pr?'bold ':'')+8*sc+'px JetBrains Mono';ctx.fillStyle=pr?'#fff':'#888';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(''+(i+1),bx,by);
    const mp=Object.entries(gpMap).find(([k])=>parseInt(k)===i);if(mp){const an=GP_ACTIONS.find(a=>a.id===mp[1])?.label||'';ctx.font=5.5*sc+'px JetBrains Mono';ctx.fillStyle='#AAA';ctx.fillText(an.slice(0,8),bx,by+br+7*sc)}}
}
function rr(c,x,y,w,h,r){c.beginPath();c.moveTo(x+r,y);c.lineTo(x+w-r,y);c.quadraticCurveTo(x+w,y,x+w,y+r);c.lineTo(x+w,y+h-r);c.quadraticCurveTo(x+w,y+h,x+w-r,y+h);c.lineTo(x+r,y+h);c.quadraticCurveTo(x,y+h,x,y+h-r);c.lineTo(x,y+r);c.quadraticCurveTo(x,y,x+r,y);c.closePath()}

/* ═══════ GAMEPAD POLL ═══════ */
function gpPoll(){
  const gps=navigator.getGamepads?.();const gp=gps?.[0]||gps?.[1]||gps?.[2]||gps?.[3];
  if(!gp){if(gpOn){gpOn=false;gpNm='';_gp=null;gpBadge()}requestAnimationFrame(gpPoll);return}
  _gp=gp; // store globally
  if(!gpOn){gpOn=true;gpNm=gp.id||'Gamepad';const had=gpLoad(gpNm);if(!had){gpDefaults();gpSave(gpNm);gpBadge();gpOpenModal()}else gpBadge()}
  const btn=i=>gp.buttons[i]?.pressed,was=i=>gpPrev[i];
  if(gpMapping){
    for(let i=0;i<gp.buttons.length;i++){if(btn(i)&&!was(i)){
      if(gpRT){Object.keys(gpMap).forEach(k=>{if(gpMap[k]===gpRT)delete gpMap[k]});gpMap[i]=gpRT;gpRT=null;gpMapping=false;gpSave(gpNm);gpBadge();const w=$('#mapper-wizard');if(w)w.style.display='none'}
      else{const aid=GP_ACTIONS[gpWI]?.id;if(aid){Object.keys(gpMap).forEach(k=>{if(gpMap[k]===aid)delete gpMap[k]});gpMap[i]=aid}gpWI++;if(gpWI>=GP_ACTIONS.length){gpMapping=false;gpSave(gpNm);gpBadge();const w=$('#mapper-wizard');if(w)w.style.display='none'}else{const a=$('#wiz-action');if(a)a.textContent=GP_ACTIONS[gpWI]?.label||'';const p=$('#wiz-progress');if(p)p.textContent=(gpWI+1)+' / '+GP_ACTIONS.length}}
      break}}
  } else {for(const[bi,aid]of Object.entries(gpMap)){const i=parseInt(bi);if(btn(i)&&!was(i)){const a=GP_ACTIONS.find(x=>x.id===aid);if(a)a.fn()}}}
  gpPrev=Array.from({length:20},(_,i)=>btn(i));
  // Refresh mapper if open
  if($('#gp-modal')?.style.display!=='none')gpRenderMapper();
  // Send axes for base control
  if(gp&&gp.axes&&gp.axes.length>=2){
    const a=[gp.axes[0]||0,gp.axes[1]||0,gp.axes.length>2?gp.axes[2]:0];
    if(a.some(v=>Math.abs(v)>0.05))post('/joystick',{axes:a});
  }
  // Send axes with key mapping for base control
  if(gp&&gp.axes&&gp.axes.length>=2){
    const hasMovement=gp.axes.slice(0,3).some(v=>Math.abs(v)>0.1);
    if(hasMovement){
      post('/joystick',{
        axes:Array.from(gp.axes),
        axis_map:axisMap,
        deadzone:0.15
      });
    }
  }
  requestAnimationFrame(gpPoll);
}

/* ═══════ WIRING ═══════ */
function wire(){const on=(id,fn)=>{const e=$(id);if(e)e.onclick=fn};
  on('#btn-rec',A.startRec);on('#btn-stop',A.stopRec);on('#btn-sav',A.save);on('#btn-dis',()=>{if(confirm('Discard?'))A.discard()});on('#btn-redo',A.rerecord);on('#btn-recon',A.reconnect);
  on('#btn-apl',async()=>{const r=await post('/settings',cs());flash($('#btn-apl'),r?.ok?'OK':'err')});on('#btn-ini',A.init);
  on('#btn-tl-on',()=>post('/start_teleop'));on('#btn-tl-off',()=>post('/stop_teleop'));
  on('#btn-sd',async()=>{await post('/set_episode_count',{count:+($('#ep_done')?.value||0)});flash($('#btn-sd'),'✓')});
  on('#btn-st',async()=>{await post('/settings',{target_episodes:+($('#ep_tgt')?.value||50)});flash($('#btn-st'),'✓')});
  on('#btn-sn',async()=>{await post('/set_next_episode',{next:+($('#ep_nxt')?.value||1)});flash($('#btn-sn'),'✓')});
  on('#btn-ver',A.verify);on('#btn-lc',copyLog);on('#btn-le',exportLog)}


function axisRemap(idx){
  get('/joystick/config').then(r=>{
    const cfg=r.config||{};const am=(cfg.axes||{})[idx]||{};
    const neg=prompt('Key for NEGATIVE (left/up) on Axis '+(idx+1)+':', am.neg||'');
    if(neg===null)return;
    const pos=prompt('Key for POSITIVE (right/down) on Axis '+(idx+1)+':', am.pos||'');
    if(pos===null)return;
    const label=prompt('Label (optional):', am.label||'');
    const axes=cfg.axes||{};
    axes[idx]={neg:neg.toLowerCase(),pos:pos.toLowerCase(),label:label||''};
    post('/joystick/config',{axes:axes});
  });
}

/* ═══════ BOOT ═══════ */
wire();poll();gpPoll();gpBadge();pollTelem();
setTimeout(()=>{if(typeof Chart!=='undefined')try{initChart()}catch(e){console.error(e)};initArm()},300);

function drawJoystickCanvas2(axes,buttons){
  const c=$('#mapper-canvas');if(!c)return;const ctx=c.getContext('2d'),dpr=window.devicePixelRatio||1;
  const W=c.width=c.clientWidth*dpr,H=c.height=c.clientHeight*dpr;
  ctx.fillStyle='#F0EDE8';ctx.fillRect(0,0,W,H);
  if(!axes||axes.length<2){ctx.font='13px JetBrains Mono';ctx.fillStyle='#AAA';ctx.textAlign='center';ctx.fillText('No joystick',W/2,H/2);return}
  const sc=W/260;
  ctx.fillStyle='#E0DBD4';ctx.strokeStyle='#C8C0B5';ctx.lineWidth=1.5;rr(ctx,W*.12,H*.03,W*.76,H*.94,10*sc);ctx.fill();ctx.stroke();
  const sx=W/2,sy=H*.22,sr=40*sc;ctx.fillStyle='#D5CEC6';ctx.beginPath();ctx.arc(sx,sy,sr,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#B8B0A5';ctx.lineWidth=1;ctx.stroke();
  ctx.strokeStyle='#C8C0BB';ctx.lineWidth=.5;ctx.beginPath();ctx.moveTo(sx-sr,sy);ctx.lineTo(sx+sr,sy);ctx.stroke();ctx.beginPath();ctx.moveTo(sx,sy-sr);ctx.lineTo(sx,sy+sr);ctx.stroke();
  const ax0=axes[0]||0,ay0=axes[1]||0;
  ctx.save();ctx.shadowColor='rgba(61,52,139,.4)';ctx.shadowBlur=8;ctx.fillStyle='#3D348B';ctx.beginPath();ctx.arc(sx+ax0*sr*.75,sy+ay0*sr*.75,9*sc,0,Math.PI*2);ctx.fill();ctx.restore();
  ctx.font=8*sc+'px JetBrains Mono';ctx.fillStyle='#888';ctx.textAlign='center';ctx.fillText('X:'+ax0.toFixed(2)+' Y:'+ay0.toFixed(2),sx,sy+sr+14*sc);
  if(axes.length>2){const tw=axes[2]||0,ty=H*.42,tw2=W*.55,th=10*sc;ctx.fillStyle='#D5CEC6';rr(ctx,W/2-tw2/2,ty,tw2,th,5);ctx.fill();
    const fw=Math.abs(tw)*tw2/2;ctx.fillStyle=tw>=0?'#3D348B':'#A06D1B';if(tw>=0)ctx.fillRect(W/2,ty,fw,th);else ctx.fillRect(W/2-fw,ty,fw,th);
    ctx.fillText('Twist: '+tw.toFixed(2),W/2,ty+th+12*sc)}
  const by0=H*.56,br=11*sc,cols=4,gap2=20*sc,totalW=cols*br*2+(cols-1)*gap2,bx0=W/2-totalW/2+br;
  for(let i=0;i<16;i++){const row=Math.floor(i/cols),col=i%cols,bx=bx0+col*(br*2+gap2),by=by0+row*(br*2+gap2),pr=!!(buttons&(1<<i));
    ctx.save();if(pr){ctx.shadowColor='rgba(61,52,139,.5)';ctx.shadowBlur=8}ctx.fillStyle=pr?'#3D348B':'#D8D2CA';ctx.beginPath();ctx.arc(bx,by,br,0,Math.PI*2);ctx.fill();ctx.restore();
    ctx.font=(pr?'bold ':'')+8*sc+'px JetBrains Mono';ctx.fillStyle=pr?'#fff':'#888';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(''+(i+1),bx,by)}
}
