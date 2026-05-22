/* KCC Recorder — Final Clean App.js */
const POLL=500;
let LS=null,RC=[],CH=null,LV=-1,allLogs=[];
let armState=[0,-45,-30,20,0,0,0,0,0];
let chartBuf=[];
const CHART_WIN=150;
let baseSpeed=1.0;

const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const post=async(p,b)=>{try{const r=await fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):'{}'});return await r.json()}catch{return{}}};
const get=async p=>{try{return(await fetch(p)).json()}catch{return{}}};
const badge=(k,t,c='')=>{const e=$(`.bd[data-key="${k}"]`);if(e){e.textContent=t;e.className='bd'+(c?' '+c:'')}};
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const flash=(b,t)=>{if(!b)return;const o=b.textContent;b.textContent=t;setTimeout(()=>b.textContent=o,1e3)};

/* ═══════ CONTROLS POPUP ═══════ */
function toggleControls(){const m=$('#ctrl-modal');if(!m)return;m.style.display=m.style.display==='flex'?'none':'flex'}

/* ═══════ CAMERAS ═══════ */
function renderCams(c,st){
  if(!(c.length===RC.length&&c.every((x,i)=>x===RC[i]))){
    const r=$('#cam-row');if(!r)return;r.innerHTML='';
    c.forEach(n=>{const d=document.createElement('div');d.className='cm';
      d.innerHTML='<img src="/camera/'+n+'.mjpg"/><span class="cl">observation.images.'+n+'</span><span class="cs" data-cs="'+n+'">live</span>';
      r.appendChild(d)});RC=c.slice();}
  $$('[data-cs]').forEach(e=>{const r=st==='recording',v=st==='review';
    e.textContent=r?'rec':v?'preview':'live';e.className='cs '+(r?'recording':v?'review':'live')});}

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
  const rb=$('#btn-rec');
  if(rb){
    if(R){rb.textContent='■ STOP';rb.className='bm brec recording';rb.disabled=false}
    else{rb.innerHTML='● REC <span class="kw">Space</span>';rb.className='bm brec';rb.disabled=!(I||T)||!s.dataset_initialized||E}
  }
  h('#rv',!V);dis('#btn-ini',R||V);h('#btn-recon',!E);dis('#btn-tl-on',!(I&&!E));dis('#btn-tl-off',!T);
  if(s.episodes_done>LV&&s.dataset_initialized&&s.state==='idle'){LV=s.episodes_done;fetchStats()}
  const rm=$('#rm');if(rm)rm.textContent=(s.current_episode_seconds||0).toFixed(1)+'s · '+(s.episodes_done||0)+'/'+(s.target_episodes||50);
  if(s.log_tail){allLogs=s.log_tail;const l=$('#log');if(l){l.innerHTML=s.log_tail.slice(-6).map(x=>'<div class="line">'+esc(x)+'</div>').join('');l.scrollTop=l.scrollHeight}}}

/* ═══════ INSPECTOR ═══════ */
async function fetchStats(){const s=await get('/dataset_stats');if(!s||!s.ok)return;
  const sv=(id,v,c)=>{const e=$(id);if(e){e.textContent=v||'—';if(c)e.className='iv '+c}};
  sv('#i-ep',s.total_episodes,s.total_episodes>0?'ok':'');sv('#i-fr',s.total_frames);
  sv('#i-dur',s.last_ep_duration?s.last_ep_duration.toFixed(1)+'s':'—');sv('#i-arm',s.arm_range);
  sv('#i-wh',s.wheel_range,s.wheels_still?'ok':'wn');
  // Update entanglement card
  const ec=$('#ent-card'),ev=$('#i-ent'),er=$('#ent-rec'),ef=$('#ent-fill'),em=$('#ent-marker');
  if(s.entanglement!=null&&ec){
    const E=s.entanglement;
    ev.textContent='E = '+E.toFixed(3);
    ef.style.width=(E*100)+'%';
    em.style.left=(E*100)+'%';
    ec.className='ent-card'+(E<0.3?' decompose':E>0.5?' e2e':' borderline');
    ef.style.background=E<0.3?'#2EA85A':E>0.5?'#E05A47':'#D4953A';
    er.textContent=E<0.2?'✓ SAFE TO DECOMPOSE — 2-4x cost savings':E<0.3?'✓ LIKELY DECOMPOSABLE — test first':E<0.5?'⚠ BORDERLINE — run both strategies':'✗ DO NOT DECOMPOSE — collect E2E';
  } else if(ev){ev.textContent='—';if(er)er.textContent='Record 10 episodes to compute'}
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
  const ts=$('#telem-status');if(ts)ts.textContent=hasData?'live':'waiting for data...'}

/* ═══════ TELEMETRY ═══════ */
async function pollTelem(){const r=await get('/telemetry');if(r&&r.ok&&r.state){armState=r.state;feedChart(r.state)}setTimeout(pollTelem,100)}

/* ═══════ SPEED CONTROL ═══════ */
async function speedUp(){const r=await post('/speed',{delta:0.1});if(r.speed){baseSpeed=r.speed;$('#speed-badge').textContent=baseSpeed.toFixed(1)+'x'}}
async function speedDown(){const r=await post('/speed',{delta:-0.1});if(r.speed){baseSpeed=r.speed;$('#speed-badge').textContent=baseSpeed.toFixed(1)+'x'}}

/* ═══════ LOG ═══════ */
function copyLog(){navigator.clipboard?.writeText(allLogs.join('\n')).then(()=>flash($('#btn-lc'),'✓'))}
function exportLog(){const b=new Blob([allLogs.join('\n')],{type:'text/plain'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='kcc_log.txt';a.click()}

/* ═══════ ACTIONS ═══════ */
const cs=()=>({hf_org:$('#hf_org')?.value?.trim()||'',hf_repo_name:$('#hf_repo')?.value?.trim()||'',task_description:$('#hf_task')?.value||'',target_episodes:parseInt($('#ep_tgt')?.value||50,10)});
const A={
  startRec(){post('/start_recording')},stopRec(){post('/stop_recording')},
  toggleRec(){if(LS?.state==='recording')post('/stop_recording');else post('/start_recording')},save(){post('/save')},discard(){post('/discard')},
  toggleTeleop(){if(LS?.state==='teleop')post('/stop_teleop');else post('/start_teleop')},
  verify(){fetchStats()},
  epUp(){post('/set_episode_count',{count:+(document.getElementById('ep_done')?.value||0)+1})},
  epDown(){post('/set_episode_count',{count:Math.max(0,+(document.getElementById('ep_done')?.value||0)-1)})},
  reconnect(){post('/reconnect')},
  init(){post('/settings',cs()).then(()=>post('/init_dataset',cs()).then(r=>{if(r&&!r.ok)alert(r.error||'init failed');else fetchStats()}))}
};

/* ═══════ KEYBOARD ═══════ */
document.onkeydown=e=>{if(e.target.tagName==='INPUT')return;
  if(e.key==='Escape'){e.preventDefault();const m=$('#ctrl-modal');if(m&&m.style.display==='flex'){toggleControls();return}A.discard();return}
  const map={
    ' ':A.toggleRec,'F2':A.toggleRec,
    'Enter':A.save,'F3':A.save,
    'F4':A.discard,
    't':A.toggleTeleop,'T':A.toggleTeleop,'F7':A.toggleTeleop,
    'v':A.verify,'V':A.verify,
    'i':A.init,'I':A.init,
    'c':A.reconnect,'C':A.reconnect,
    'r':speedUp,'R':speedUp,
    'f':speedDown,'F':speedDown,
    'F8':A.epDown,'F9':A.epUp
  };
  if(map[e.key]){e.preventDefault();map[e.key]()}};

/* ═══════ WIRING ═══════ */
function wire(){const on=(id,fn)=>{const e=$(id);if(e)e.onclick=fn};
  on('#btn-rec',A.toggleRec);on('#btn-sav',A.save);on('#btn-dis',()=>{if(confirm('Discard?'))A.discard()});
  on('#btn-recon',A.reconnect);on('#btn-apl',async()=>{const r=await post('/settings',cs());flash($('#btn-apl'),r?.ok?'OK':'err')});on('#btn-ini',A.init);
  on('#btn-tl-on',()=>post('/start_teleop'));on('#btn-tl-off',()=>post('/stop_teleop'));
  on('#btn-sd',async()=>{await post('/set_episode_count',{count:+($('#ep_done')?.value||0)});flash($('#btn-sd'),'✓')});
  on('#btn-st',async()=>{await post('/settings',{target_episodes:+($('#ep_tgt')?.value||50)});flash($('#btn-st'),'✓')});
  on('#btn-sn',async()=>{await post('/set_next_episode',{next:+($('#ep_nxt')?.value||1)});flash($('#btn-sn'),'✓')});
  on('#btn-ver',A.verify);on('#btn-lc',copyLog);on('#btn-le',exportLog)}

/* ═══════ BOOT ═══════ */
wire();poll();setInterval(()=>{if(LS?.dataset_initialized)fetchStats()},5000);pollTelem();
setTimeout(()=>{if(typeof Chart!=='undefined')try{initChart()}catch(e){console.error(e)};initArm()},300);
