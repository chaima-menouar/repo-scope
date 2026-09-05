const $ = (sel) => document.querySelector(sel);
let activeReviewer = '';
let currentCandidate = null;
let selectedLabel = null;

function setHidden(el, hidden = true){ el.classList.toggle('hidden', hidden); }
function escapeHtml(value){ return String(value ?? '').replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch])); }
function showMessage(message, type='info'){
  const box = $('#review-message');
  box.textContent = message;
  box.dataset.type = type;
  setHidden(box, false);
}
function clearMessage(){ setHidden($('#review-message'), true); }

async function getJson(url){
  const res = await fetch(url);
  let data = {}; try { data = await res.json(); } catch {}
  if(!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}
async function postJson(url, body={}){
  const res = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  let data = {}; try { data = await res.json(); } catch {}
  if(!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function metric(value, fallback='—'){
  return value === null || value === undefined || value === '' ? fallback : value;
}
function pct(value){
  if(value === null || value === undefined) return '—';
  const n = Number(value);
  if(Number.isNaN(n)) return String(value);
  return `${Math.round(n * (n <= 1 ? 100 : 1))}%`;
}

function renderStatus(data){
  $('#stat-queue').textContent = metric(data.queue_repositories);
  $('#stat-decisions').textContent = metric(data.raw_decisions);
  $('#stat-adjudicated').textContent = metric(data.adjudicated_repositories);

  const readiness = data.readiness || {};
  $('#stat-readiness').textContent = readiness.eligible ? 'Eligible' : 'Blocked';
  const reasons = readiness.blocking_reasons || [];
  $('#stat-readiness-note').textContent = reasons[0] || 'manual promotion gate';
  $('#readiness-copy').textContent = reasons.length ? reasons.join(' · ') : 'Automated evidence is eligible; manual approval is still required.';

  $('#write-mode').textContent = data.write_enabled
    ? 'Local review writes are enabled.'
    : 'Read-only mode. Set REPOSCOPE_HUMAN_REVIEW_WRITE_ENABLED=true before starting the server to save decisions.';

  const agreement = data.agreement || {};
  $('#agreement-reviewers').textContent = metric(agreement.reviewer_count ?? data.reviewer_count);
  $('#agreement-shared').textContent = metric(agreement.repositories_with_multiple_reviewers ?? agreement.shared_repositories);
  $('#agreement-rate').textContent = agreement.raw_agreement === undefined ? '—' : pct(agreement.raw_agreement);
  $('#agreement-kappa').textContent = metric(agreement.cohens_kappa ?? agreement.mean_pairwise_kappa);

  const adjudication = data.adjudication || {};
  $('#adjudication-status').textContent = metric(adjudication.status, data.adjudicated_repositories ? 'partial' : 'no decisions');
  $('#adjudication-disagreements').textContent = metric(adjudication.disagreement_repositories, 0);
  $('#adjudication-insufficient').textContent = metric(adjudication.insufficient_reviewer_repositories, 0);
}

async function loadStatus(){
  try { renderStatus(await getJson('/api/human-validation/status')); }
  catch(err){ showMessage(err.message, 'error'); }
}

function renderCandidate(candidate, mode){
  currentCandidate = candidate;
  selectedLabel = null;
  document.querySelectorAll('[data-label]').forEach(btn => btn.classList.remove('selected'));
  $('#submit-review').disabled = true;
  $('#review-notes').value = '';
  $('#assignment-mode').textContent = mode === 'assigned' ? 'Assigned review' : 'Open queue';

  if(!candidate){
    $('#candidate-title').textContent = 'No pending repositories';
    $('#candidate-empty').textContent = 'This reviewer has no visible pending candidates.';
    setHidden($('#candidate-empty'), false);
    setHidden($('#candidate-card'), true);
    return;
  }

  $('#candidate-title').textContent = candidate.repo;
  $('#candidate-github').href = `https://github.com/${encodeURI(candidate.repo)}`;
  $('#candidate-snapshot').textContent = candidate.snapshot_at_utc ? `Snapshot ${candidate.snapshot_at_utc}` : '';
  const fields = [
    ['Language', candidate.language],
    ['Stars', candidate.stars],
    ['Size KB', candidate.size_kb],
    ['Last pushed', candidate.catalog_pushed_at],
    ['Archived', candidate.archived],
    ['Release age (days)', candidate.latest_release_age_days],
    ['Latest release', candidate.latest_release_at],
  ];
  $('#candidate-evidence').innerHTML = fields.map(([label,value]) => `<div><span>${escapeHtml(label)}</span><b>${escapeHtml(metric(value))}</b></div>`).join('');
  setHidden($('#candidate-empty'), true);
  setHidden($('#candidate-card'), false);
}

async function loadCandidate(){
  clearMessage();
  const reviewer = $('#reviewer-id').value.trim();
  if(!reviewer){ showMessage('Enter a reviewer ID first.', 'error'); return; }
  activeReviewer = reviewer;
  try {
    const data = await getJson(`/api/human-validation/candidates?reviewer=${encodeURIComponent(reviewer)}&limit=1`);
    renderCandidate(data.candidates[0] || null, data.assignment_mode);
  } catch(err){
    renderCandidate(null, 'open_queue');
    showMessage(err.message, 'error');
  }
}

function updateSubmitState(){
  $('#submit-review').disabled = !(currentCandidate && selectedLabel && $('#review-notes').value.trim().length >= 8);
}

document.querySelectorAll('[data-label]').forEach(btn => btn.addEventListener('click', () => {
  selectedLabel = btn.dataset.label;
  document.querySelectorAll('[data-label]').forEach(x => x.classList.toggle('selected', x === btn));
  updateSubmitState();
}));
$('#review-notes').addEventListener('input', updateSubmitState);
$('#load-review').addEventListener('click', loadCandidate);
$('#reviewer-id').addEventListener('keydown', e => { if(e.key === 'Enter') loadCandidate(); });
$('#skip-review').addEventListener('click', async () => { await loadCandidate(); });

$('#submit-review').addEventListener('click', async () => {
  if(!currentCandidate || !selectedLabel) return;
  const btn = $('#submit-review');
  btn.disabled = true;
  try {
    await postJson('/api/human-validation/review', {
      repo: currentCandidate.repo,
      reviewer: activeReviewer,
      human_label: selectedLabel,
      review_notes: $('#review-notes').value.trim(),
    });
    showMessage(`Saved ${selectedLabel} review for ${currentCandidate.repo}.`, 'success');
    await loadStatus();
    await loadCandidate();
  } catch(err){
    showMessage(err.message, 'error');
    updateSubmitState();
  }
});

$('#refresh-validation').addEventListener('click', async () => {
  const btn = $('#refresh-validation');
  const old = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Refreshing…';
  try {
    const data = await postJson('/api/human-validation/refresh');
    renderStatus(data.validation);
    showMessage('Validation artifacts refreshed successfully.', 'success');
  } catch(err){ showMessage(err.message, 'error'); }
  finally { btn.disabled = false; btn.textContent = old; }
});

loadStatus();
