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
  Chart.defaults.color='#9f90a3';
  Chart.defaults.borderColor='rgba(255,246,223,.08)';
  Chart.defaults.font.family='Manrope';
}
function renderCharts(data){
  chartDefaults();
  const commits=(data.timeseries.commits||[]).slice(-12); destroyChart('commits');
  charts.commits=new Chart($('#commits-chart'),{type:'line',data:{labels:commits.map(x=>x.date),datasets:[{data:commits.map(x=>x.count),borderColor:'#d9ff62',backgroundColor:'rgba(217,255,98,.065)',fill:true,tension:.4,pointRadius:2,pointBackgroundColor:'#d9ff62'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{font:{size:9}}},y:{beginAtZero:true,ticks:{font:{size:9}}}}}});

  const issues=(data.timeseries.issues||[]).slice(-12); destroyChart('issues');
  charts.issues=new Chart($('#issues-chart'),{type:'bar',data:{labels:issues.map(x=>x.date),datasets:[{label:'Opened',data:issues.map(x=>x.opened),backgroundColor:'rgba(245,138,214,.74)',borderRadius:5},{label:'Closed',data:issues.map(x=>x.closed),backgroundColor:'rgba(217,255,98,.7)',borderRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{boxWidth:8,font:{size:9}}}},scales:{x:{grid:{display:false},ticks:{font:{size:9}}},y:{beginAtZero:true,ticks:{font:{size:9}}}}}});

  const top=data.stats.contributors.top||[]; destroyChart('contributors');
  charts.contributors=new Chart($('#contributors-chart'),{type:'bar',data:{labels:top.map(x=>x.login),datasets:[{data:top.map(x=>x.contributions),backgroundColor:top.map((_,i)=>i===0?'#d9ff62':'rgba(245,138,214,.5)'),borderRadius:6}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,ticks:{font:{size:9}}},y:{grid:{display:false},ticks:{font:{size:9}}}}}});

  const langs=(data.stats.languages||[]).slice(0,6); destroyChart('languages');
  charts.languages=new Chart($('#languages-chart'),{type:'doughnut',data:{labels:langs.map(x=>x.name),datasets:[{data:langs.map(x=>x.percent),backgroundColor:['#d9ff62','#f58ad6','#ff7a72','#fff2d4','#a379bb','#9cb95e'],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,cutout:'72%',plugins:{legend:{display:false}}}});
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
