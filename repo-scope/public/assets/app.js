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
