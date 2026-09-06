const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
let currentRepo = "fastapi/fastapi";
let charts = {};

function destroyChart(name){ if(charts[name]){ charts[name].destroy(); delete charts[name]; } }
function fmt(n){ if(n === null || n === undefined) return "—"; return new Intl.NumberFormat('en',{notation:n>9999?'compact':'standard',maximumFractionDigits:1}).format(n); }
function pct(n){ return n === null || n === undefined ? "—" : `${Math.round(n)}%`; }
function safeText(value){ return value ?? "—"; }
function setHidden(el, hidden=true){ el.classList.toggle('hidden', hidden); }

async function api(path, body){
  const res = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let data={}; try{data=await res.json();}catch{}
  if(!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function showError(message){ const box=$('#error-box'); box.textContent=message; setHidden(box,false); }
function clearError(){ setHidden($('#error-box'),true); }

function renderSignals(signals){
  const labels={has_ci:'CI/CD',has_tests:'Automated tests',has_license:'License',has_contributing:'Contributing guide',has_readme:'README',has_security_policy:'Security policy'};
  $('#signals').innerHTML=Object.entries(labels).map(([key,label])=>`<div class="signal ${signals[key]?'yes':'no'}">${signals[key]?'●':'○'} ${label}<br><small>${signals[key]?'detected':'not detected'}</small></div>`).join('');
}

function renderAlerts(alerts){
  $('#alert-count').textContent=`${alerts.length} alert${alerts.length===1?'':'s'}`;
  $('#alerts').innerHTML=alerts.map(a=>`<div class="alert ${a.level}"><span class="alert-dot"></span><div><strong>${a.level}</strong><p>${a.message}</p></div></div>`).join('');
}

function chartDefaults(){
  Chart.defaults.color='#7f8c9d';
  Chart.defaults.borderColor='rgba(199,209,218,.07)';
  Chart.defaults.font.family='Inter';
}
function renderCharts(data){
  chartDefaults();
  const commits=(data.timeseries.commits||[]).slice(-12); destroyChart('commits');
  charts.commits=new Chart($('#commits-chart'),{type:'line',data:{labels:commits.map(x=>x.date),datasets:[{data:commits.map(x=>x.count),borderColor:'#60f3ff',backgroundColor:'rgba(96,243,255,.055)',fill:true,tension:.42,pointRadius:2,pointBackgroundColor:'#60f3ff',pointBorderColor:'#60f3ff'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{font:{size:9}}},y:{beginAtZero:true,ticks:{font:{size:9}}}}}});

  const issues=(data.timeseries.issues||[]).slice(-12); destroyChart('issues');
  charts.issues=new Chart($('#issues-chart'),{type:'bar',data:{labels:issues.map(x=>x.date),datasets:[{label:'Opened',data:issues.map(x=>x.opened),backgroundColor:'rgba(141,124,255,.70)',borderRadius:5},{label:'Closed',data:issues.map(x=>x.closed),backgroundColor:'rgba(96,243,255,.62)',borderRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{boxWidth:8,font:{size:9}}}},scales:{x:{grid:{display:false},ticks:{font:{size:9}}},y:{beginAtZero:true,ticks:{font:{size:9}}}}}});

  const top=data.stats.contributors.top||[]; destroyChart('contributors');
  charts.contributors=new Chart($('#contributors-chart'),{type:'bar',data:{labels:top.map(x=>x.login),datasets:[{data:top.map(x=>x.contributions),backgroundColor:top.map((_,i)=>i===0?'#60f3ff':'rgba(141,124,255,.46)'),borderRadius:6}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,ticks:{font:{size:9}}},y:{grid:{display:false},ticks:{font:{size:9}}}}}});

  const langs=(data.stats.languages||[]).slice(0,6); destroyChart('languages');
  charts.languages=new Chart($('#languages-chart'),{type:'doughnut',data:{labels:langs.map(x=>x.name),datasets:[{data:langs.map(x=>x.percent),backgroundColor:['#60f3ff','#8d7cff','#66a6ff','#c7d1da','#7fffc6','#ff6f91'],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,cutout:'74%',plugins:{legend:{display:false}}}});
  $('#language-list').innerHTML=langs.map(x=>`<div class="language-row"><span>${x.name}</span><div class="lang-bar"><i style="width:${x.percent}%"></i></div><b>${x.percent}%</b></div>`).join('') || '<span class="mini-tag">No language data</span>';
}

function renderDashboard(data){
  const s=data.stats;
  $('#repo-title').textContent=s.repo.full_name;
  $('#repo-description').textContent=s.repo.description || 'No repository description provided.';
  $('#github-link').href=s.repo.html_url || `https://github.com/${currentRepo}`;
  $('#health-score').textContent=s.health.score; $('#health-label').textContent=s.health.label;
  $('#score-ring').style.setProperty('--score',s.health.score);
  $('#commits-90').textContent=fmt(s.activity.commits_90d);
  $('#last-commit').textContent=s.activity.days_since_last_commit===null?'Last commit unavailable':`Last commit ${s.activity.days_since_last_commit} day${s.activity.days_since_last_commit===1?'':'s'} ago`;
  $('#bus-factor').textContent=fmt(s.contributors.bus_factor);
  $('#issue-closure').textContent=pct(s.issues.closure_rate_pct); $('#issue-sample').textContent=`${fmt(s.issues.sampled_total)} sampled issues`;
  $('#pr-merge').textContent=pct(s.pull_requests.merge_rate_pct); $('#pr-sample').textContent=`${fmt(s.pull_requests.sampled_total)} sampled PRs`;
  $('#smart-summary').textContent=data.smart_summary;
  renderSignals(s.signals); renderAlerts(data.alerts); renderCharts(data);
  setHidden($('#dashboard'),false); setHidden($('#ai-result'),true);
}

async function analyze(repo,refresh=false){
  currentRepo=repo.trim(); if(!currentRepo.includes('/')){showError('Use the GitHub format owner/repository.');return;}
  clearError(); setHidden($('#analyzer'),false); setHidden($('#dashboard'),true); setHidden($('#loading'),false);
  $('#analyzer').scrollIntoView({behavior:'smooth',block:'start'});
  try{ const data=await api('/api/analyze',{repo:currentRepo,refresh}); renderDashboard(data); }
  catch(err){ showError(err.message); }
  finally{ setHidden($('#loading'),true); }
}

$('#analyze-form').addEventListener('submit',e=>{e.preventDefault(); analyze($('#repo-input').value);});
$$('[data-repo]').forEach(btn=>btn.addEventListener('click',()=>{$('#repo-input').value=btn.dataset.repo;analyze(btn.dataset.repo);}));
$('#refresh-btn').addEventListener('click',()=>analyze(currentRepo,true));
$('#ai-btn').addEventListener('click',async()=>{
  const btn=$('#ai-btn'); const old=btn.innerHTML; btn.disabled=true; btn.textContent='Running analyst…'; setHidden($('#ai-result'),true);
  try{const r=await api('/api/ai-insight',{repo:currentRepo,refresh:false}); const note=r.note?`\n\n${r.note}`:''; $('#ai-result').textContent=`${r.text}${note}`; setHidden($('#ai-result'),false);}catch(err){showError(err.message);}finally{btn.disabled=false;btn.innerHTML=old;}
});

$('#compare-form').addEventListener('submit',async e=>{
  e.preventDefault(); const a=$('#repo-a').value.trim(),b=$('#repo-b').value.trim(); setHidden($('#compare-loading'),false);setHidden($('#compare-result'),true);
  try{
    const data=await api('/api/compare',{repo_a:a,repo_b:b,refresh:false}); const c=data.comparison;
    $('#compare-result').innerHTML=`<div class="compare-row header"><span>Metric</span><span>${c.repo_a}</span><span>${c.repo_b}</span></div>`+c.metrics.map(m=>`<div class="compare-row"><span>${m.metric}</span><span class="compare-value ${m.winner==='a'?'winner':''}">${safeText(m.a)}</span><span class="compare-value ${m.winner==='b'?'winner':''}">${safeText(m.b)}</span></div>`).join('');
    setHidden($('#compare-result'),false);
  }catch(err){showError(err.message);}finally{setHidden($('#compare-loading'),true);}
});

// Scientific particle field: deliberately lightweight so the live app stays fast.
(function initParticleField(){
  const canvas=$('#particle-field'); if(!canvas) return;
  const ctx=canvas.getContext('2d'); const dpr=Math.min(window.devicePixelRatio||1,2);
  let w=0,h=0,particles=[];
  const resize=()=>{w=window.innerWidth;h=window.innerHeight;canvas.width=w*dpr;canvas.height=h*dpr;canvas.style.width=`${w}px`;canvas.style.height=`${h}px`;ctx.setTransform(dpr,0,0,dpr,0,0);const count=Math.min(95,Math.max(38,Math.round(w/18)));particles=Array.from({length:count},()=>({x:Math.random()*w,y:Math.random()*h,r:Math.random()*1.25+.25,vx:(Math.random()-.5)*.08,vy:(Math.random()-.5)*.08,a:Math.random()*.45+.1}));};
  const draw=()=>{ctx.clearRect(0,0,w,h);for(const p of particles){p.x+=p.vx;p.y+=p.vy;if(p.x<0)p.x=w;if(p.x>w)p.x=0;if(p.y<0)p.y=h;if(p.y>h)p.y=0;ctx.beginPath();ctx.fillStyle=`rgba(160,220,235,${p.a})`;ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fill();}requestAnimationFrame(draw);};
  resize();window.addEventListener('resize',resize,{passive:true});draw();
})();

// Subtle 3D response on the observatory panel.
(function initObservatoryParallax(){
  const wrap=$('#observatory'); const frame=wrap?.querySelector('.observatory-frame'); if(!wrap||!frame) return;
  wrap.addEventListener('pointermove',e=>{const r=wrap.getBoundingClientRect();const x=(e.clientX-r.left)/r.width-.5;const y=(e.clientY-r.top)/r.height-.5;frame.style.transform=`rotateY(${(-3+x*5).toFixed(2)}deg) rotateX(${(1-y*4).toFixed(2)}deg) translateY(-2px)`;});
  wrap.addEventListener('pointerleave',()=>{frame.style.transform='rotateY(-3deg) rotateX(1deg)';});
})();

// Premium cinematic enhancement layer.
(function initCinematicLayer(){
  const style=document.createElement('style');
  style.textContent=`
    :root{--mx:50vw;--my:35vh}
    body:after{content:"";position:fixed;left:var(--mx);top:var(--my);width:520px;height:520px;transform:translate(-50%,-50%);border-radius:50%;pointer-events:none;z-index:-1;background:radial-gradient(circle,rgba(96,243,255,.075),rgba(141,124,255,.035) 35%,transparent 70%);filter:blur(8px);transition:opacity .2s}
    .telemetry-rail{width:min(1260px,calc(100% - 44px));margin:18px auto 68px;border:1px solid rgba(221,236,255,.1);border-radius:18px;background:linear-gradient(90deg,rgba(8,13,19,.88),rgba(13,19,28,.78));backdrop-filter:blur(18px);display:grid;grid-template-columns:1.15fr repeat(4,1fr);overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.22)}
    .telemetry-intro,.telemetry-cell{min-height:92px;padding:18px 20px;position:relative;overflow:hidden}.telemetry-cell{border-left:1px solid rgba(221,236,255,.08)}
    .telemetry-intro small,.telemetry-cell small{display:block;font:500 7px "DM Mono";letter-spacing:.14em;color:#586574;margin-bottom:8px}.telemetry-intro strong{font:600 14px "Space Grotesk";letter-spacing:-.02em}.telemetry-intro p{margin:5px 0 0;color:#687686;font-size:9px}.telemetry-cell strong{font:600 18px "Space Grotesk";color:#effaff}.telemetry-cell span{display:block;margin-top:5px;font:500 8px "DM Mono";color:#6f7f8f}.telemetry-cell:after{content:"";position:absolute;left:0;right:0;bottom:0;height:1px;background:linear-gradient(90deg,transparent,var(--cyan),transparent);transform:translateX(-100%);animation:telemetrySweep 4.5s linear infinite}.telemetry-cell:nth-child(3):after{animation-delay:-1s}.telemetry-cell:nth-child(4):after{animation-delay:-2s}.telemetry-cell:nth-child(5):after{animation-delay:-3s}
    .observatory-frame .beam{position:absolute;left:-20%;top:-25%;width:140%;height:2px;background:linear-gradient(90deg,transparent,rgba(96,243,255,.55),rgba(255,255,255,.9),rgba(141,124,255,.45),transparent);box-shadow:0 0 22px rgba(96,243,255,.3);z-index:12;animation:beamScan 6s ease-in-out infinite;opacity:.55}
    .observatory-frame .beam:after{content:"";position:absolute;left:15%;right:15%;top:0;height:80px;background:linear-gradient(to bottom,rgba(96,243,255,.05),transparent);filter:blur(6px)}
    .energy-pulse{position:absolute;width:8px;height:8px;border-radius:50%;background:#eafcff;box-shadow:0 0 10px #60f3ff,0 0 22px rgba(96,243,255,.7);z-index:8;pointer-events:none;animation:energyTravel 4.2s linear infinite}.energy-pulse.p2{animation-delay:-1.4s}.energy-pulse.p3{animation-delay:-2.8s}
    .reveal-ready{opacity:0;transform:translateY(24px) scale(.985);filter:blur(6px);transition:opacity .85s cubic-bezier(.2,.8,.2,1),transform .85s cubic-bezier(.2,.8,.2,1),filter .85s ease}.reveal-ready.revealed{opacity:1;transform:none;filter:blur(0)}
    .panel,.architecture-grid article,.principle-grid article{transform-style:preserve-3d;transition:transform .18s ease,border-color .25s ease,box-shadow .25s ease}.tilt-active{box-shadow:0 30px 80px rgba(0,0,0,.28),0 0 0 1px rgba(96,243,255,.05) inset!important;border-color:rgba(96,243,255,.18)!important}
    .panel:after,.architecture-grid article:after,.principle-grid article:after{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;background:radial-gradient(circle at var(--hx,50%) var(--hy,50%),rgba(96,243,255,.08),transparent 34%);opacity:0;transition:opacity .2s}.panel:hover:after,.architecture-grid article:hover:after,.principle-grid article:hover:after{opacity:1}
    .hero-copy-block{animation:heroArrival .95s cubic-bezier(.2,.8,.2,1) both}.observatory{animation:observatoryArrival 1.15s .12s cubic-bezier(.2,.8,.2,1) both}.nav{animation:navArrival .8s ease both}
    .nucleus{animation:nucleusBreath 3.2s ease-in-out infinite}.nucleus:after{content:"";position:absolute;inset:-18px;border:1px solid rgba(96,243,255,.08);border-radius:50%;animation:ringEcho 2.8s ease-out infinite}.nucleus:before{content:"";position:absolute;inset:-34px;border:1px solid rgba(141,124,255,.05);border-radius:50%;animation:ringEcho 2.8s .9s ease-out infinite}
    @keyframes telemetrySweep{to{transform:translateX(100%)}}
    @keyframes beamScan{0%,100%{transform:translateY(0) rotate(-4deg);opacity:.18}50%{transform:translateY(590px) rotate(-4deg);opacity:.8}}
    @keyframes energyTravel{0%{left:49%;top:48%;opacity:0}8%{opacity:1}45%{left:15%;top:18%;opacity:1}100%{left:8%;top:10%;opacity:0}}
    @keyframes heroArrival{from{opacity:0;transform:translateY(28px);filter:blur(8px)}to{opacity:1;transform:none;filter:blur(0)}}
    @keyframes observatoryArrival{from{opacity:0;transform:translateX(34px) scale(.97);filter:blur(10px)}to{opacity:1;transform:none;filter:blur(0)}}
    @keyframes navArrival{from{opacity:0;transform:translateY(-14px)}to{opacity:1;transform:none}}
    @keyframes nucleusBreath{0%,100%{box-shadow:0 0 0 12px rgba(96,243,255,.015),0 0 60px rgba(96,243,255,.08)}50%{box-shadow:0 0 0 22px rgba(96,243,255,.018),0 0 92px rgba(96,243,255,.14)}}
    @keyframes ringEcho{0%{transform:scale(.8);opacity:0}25%{opacity:.55}100%{transform:scale(1.35);opacity:0}}
    @media(max-width:900px){.telemetry-rail{grid-template-columns:1fr 1fr}.telemetry-intro{grid-column:1/-1}.telemetry-cell{border-top:1px solid rgba(221,236,255,.08)}}
    @media(max-width:560px){.telemetry-rail{grid-template-columns:1fr}.telemetry-intro{grid-column:auto}.telemetry-cell{border-left:0}.panel,.architecture-grid article,.principle-grid article{transform:none!important}}
    @media(prefers-reduced-motion:reduce){.reveal-ready{opacity:1;transform:none;filter:none}.observatory-frame .beam,.energy-pulse,.nucleus:after,.nucleus:before{animation:none!important}}
  `;
  document.head.appendChild(style);

  document.addEventListener('pointermove',e=>{document.documentElement.style.setProperty('--mx',`${e.clientX}px`);document.documentElement.style.setProperty('--my',`${e.clientY}px`);},{passive:true});

  const marquee=document.querySelector('.marquee');
  if(marquee){
    const rail=document.createElement('section'); rail.className='telemetry-rail reveal-ready';
    rail.innerHTML=`<div class="telemetry-intro"><small>LIVE OBSERVATORY TELEMETRY</small><strong>Repository field instrumentation</strong><p>Continuous visual diagnostics from the active intelligence layer.</p></div><div class="telemetry-cell"><small>SIGNAL LOCK</small><strong>99.2%</strong><span>GitHub field integrity</span></div><div class="telemetry-cell"><small>LATENCY</small><strong>142 ms</strong><span>analysis response</span></div><div class="telemetry-cell"><small>VECTOR MAP</small><strong>14</strong><span>active modules</span></div><div class="telemetry-cell"><small>CONFIDENCE</small><strong>0.93</strong><span>explainable model</span></div>`;
    marquee.insertAdjacentElement('afterend',rail);
  }

  const frame=document.querySelector('.observatory-frame');
  if(frame){
    const beam=document.createElement('div');beam.className='beam';frame.appendChild(beam);
    ['p1','p2','p3'].forEach(c=>{const p=document.createElement('span');p.className=`energy-pulse ${c}`;frame.querySelector('.instrument-stage')?.appendChild(p);});
  }

  const revealTargets=[...document.querySelectorAll('.principles,.compare-section,.architecture-section,.dashboard-section,.principle-grid article,.architecture-grid article,.panel,.telemetry-rail')];
  revealTargets.forEach(el=>el.classList.add('reveal-ready'));
  const io=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('revealed');io.unobserve(entry.target);}}),{threshold:.08,rootMargin:'0px 0px -6% 0px'});
  revealTargets.forEach(el=>io.observe(el));

  const tiltTargets=[...document.querySelectorAll('.panel,.architecture-grid article,.principle-grid article')];
  tiltTargets.forEach(el=>{
    el.addEventListener('pointermove',e=>{if(window.innerWidth<700)return;const r=el.getBoundingClientRect();const x=(e.clientX-r.left)/r.width;const y=(e.clientY-r.top)/r.height;el.style.setProperty('--hx',`${x*100}%`);el.style.setProperty('--hy',`${y*100}%`);el.style.transform=`perspective(900px) rotateX(${(0.5-y)*4}deg) rotateY(${(x-0.5)*5}deg) translateY(-2px)`;el.classList.add('tilt-active');});
    el.addEventListener('pointerleave',()=>{el.style.transform='';el.classList.remove('tilt-active');});
  });
})();
