const $ = (id) => document.getElementById(id);
const walk = $('walk');
let scenario = 'normal';
const sample = {
  normal: {first: 8 * 60 + 42, second: 8 * 60 + 49, age: 32},
  delay: {first: 8 * 60 + 47, second: 8 * 60 + 49, age: 48},
  stale: {first: 8 * 60 + 42, second: 8 * 60 + 49, age: 214}
};
function clock(minutes) { return `${String(Math.floor(minutes / 60)).padStart(2,'0')}:${String(minutes % 60).padStart(2,'0')}`; }
function render() {
  const {first, second, age} = sample[scenario];
  const needed = Number(walk.value), gap = second - first;
  const stale = age > 90;
  const kind = stale ? 'stale' : gap < needed ? 'missed' : gap < needed + 2 ? 'tight' : 'comfortable';
  const labels = {comfortable:['Comfortable','You have room to make this connection.','↗'],tight:['Tight connection','A small delay could change the outcome.','↗'],missed:['Likely missed','The predicted gap is shorter than your walk.','×'],stale:['Data is stale','There is no reliable recommendation right now.','!']};
  $('status').textContent = labels[kind][0]; $('summary').textContent = labels[kind][1]; $('statusIcon').textContent = labels[kind][2];
  $('gap').innerHTML = stale ? '—' : `${gap}<span>min</span>`;
  $('firstTime').textContent = clock(first); $('secondTime').textContent = clock(second);
  $('freshness').textContent = `${age} sec old`; $('freshnessNote').textContent = stale ? 'Beyond the 90 second freshness limit' : 'Within the 90 second freshness limit';
  $('buffer').textContent = stale ? '—' : `${gap-needed} min`; $('walkLabel').textContent = `${needed} min`;
  $('walkText').textContent = `${needed} min walk`;
  $('walkTrack').style.width = `${Math.min(100, 100 * needed / Math.max(gap,1))}%`;
  document.querySelector('.hero-card').classList.toggle('stale', stale);
}
walk.addEventListener('input', render);
document.querySelectorAll('[data-scenario]').forEach(button => button.addEventListener('click', () => {
  scenario = button.dataset.scenario;
  document.querySelectorAll('[data-scenario]').forEach(b => b.classList.toggle('selected', b === button));
  if (!$('apiToggle').checked) render();
}));
$('apiToggle').addEventListener('change', e => {
  $('apiFields').hidden = !e.target.checked;
  if (!e.target.checked) { $('summary').textContent = 'You have room to make this connection.'; render(); }
});
$('refresh').addEventListener('click', async () => {
  const params = new URLSearchParams({stop:$('stopId').value,from:$('fromId').value,to:$('toId').value,walk:walk.value});
  try {
    const response = await fetch(`/api/transfer?${params}`);
    if (!response.ok) throw new Error((await response.json()).error || `HTTP ${response.status}`);
    const data = await response.json();
    const a = data.assessment;
    $('status').textContent = a.status === 'unknown' ? 'No prediction' : a.status.charAt(0).toUpperCase() + a.status.slice(1);
    $('summary').textContent = a.reason;
    $('gap').innerHTML = a.gap_minutes === null ? '—' : `${a.gap_minutes}<span>min</span>`;
    $('firstTime').textContent = data.from ? new Date(data.from.arrival*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '—';
    $('secondTime').textContent = data.to ? new Date(data.to.arrival*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '—';
    $('freshness').textContent = a.age_seconds === undefined ? 'No recent feed' : `${a.age_seconds} sec old`;
    $('buffer').textContent = a.gap_minutes === null ? '—' : `${(a.gap_minutes-Number(walk.value)).toFixed(1)} min`;
    $('freshnessNote').textContent = 'Local GTFS-Realtime feed';
    $('statusIcon').textContent = a.status === 'missed' ? '×' : a.status === 'stale' ? '!' : '↗';
  } catch (error) {
    $('status').textContent = 'Feed unavailable'; $('summary').textContent = `${error.message}. Start the local server and ingester to use a feed.`;
    $('gap').textContent = '—'; $('freshness').textContent = 'No connection'; $('buffer').textContent = '—';
  }
});
render();
