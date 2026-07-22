'use strict';

let chart       = null;
let sessionId   = null;

function initChart() {
  const ctx = document.getElementById('timeline-chart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels:   [],
      datasets: [
        {
          label:           'Attention %',
          data:            [],
          borderColor:     '#00d4ff',
          backgroundColor: 'rgba(0,212,255,0.07)',
          borderWidth:     2,
          pointRadius:     2,
          pointHoverRadius:4,
          fill:            true,
          tension:         0.4,
        },
        {
          label:       'Alert threshold (60%)',
          data:        [],
          borderColor: '#ef4444',
          borderWidth: 1,
          borderDash:  [5, 5],
          pointRadius: 0,
          fill:        false,
        },
      ],
    },
    options: {
      responsive:          true,
      maintainAspectRatio: false,
      animation:           { duration: 250 },
      interaction:         { mode: 'index', intersect: false },
      scales: {
        x: {
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#7777a0', font: { size: 10 }, maxTicksLimit: 8 },
        },
        y: {
          min:   0,
          max:   100,
          grid:  { color: 'rgba(255,255,255,0.04)' },
          ticks: {
            color: '#7777a0',
            font:  { size: 10 },
            callback: v => v + '%',
          },
        },
      },
      plugins: {
        legend: {
          labels: { color: '#7777a0', font: { size: 11 }, boxWidth: 12, padding: 14 },
        },
        tooltip: {
          backgroundColor: 'rgba(13,13,26,0.9)',
          borderColor:     '#1c1c32',
          borderWidth:     1,
          titleColor:      '#ededf8',
          bodyColor:       '#7777a0',
        },
      },
    },
  });
}

function updateDashboard(d) {

  document.getElementById('fps-label').textContent = `${d.fps} fps`;
  const dot = document.getElementById('mqtt-dot');
  dot.classList.toggle('on', !!d.mqtt_connected);

  const attn    = d.class_attention ?? 0;
  const hasData = d.total_students > 0;
  const gEl     = document.getElementById('gauge-value');

  gEl.textContent = hasData ? attn + '%' : '--';
  gEl.className   = 'gauge-value ' + (
    !hasData          ? 'idle'   :
    attn >= 70        ? 'high'   :
    attn >= 45        ? 'medium' : 'low'
  );

  const fillColor = attn >= 70 ? '#10b981' : attn >= 45 ? '#f59e0b' : '#ef4444';
  const fill      = document.getElementById('gauge-fill');
  fill.style.width      = attn + '%';
  fill.style.background = fillColor;

  document.getElementById('cnt-att').textContent = d.attentive_count  ?? 0;
  document.getElementById('cnt-dis').textContent = d.distracted_count ?? 0;
  document.getElementById('cnt-slp').textContent = d.sleeping_count   ?? 0;
  document.getElementById('cnt-phn').textContent = d.phone_count      ?? 0;
  document.getElementById('cnt-total').textContent =
    d.total_students > 0 ? `${d.total_students} student(s) detected` : 'No students detected';


  const list = document.getElementById('students-list');
  list.innerHTML = '';

  if (!d.students || d.students.length === 0) {
    list.innerHTML = '<div class="empty-msg">Waiting for detections…</div>';
  } else {
    const colorMap = {
      attentive:  '#10b981',
      distracted: '#f59e0b',
      sleeping:   '#ef4444',
      phone:      '#f97316',
    };

    d.students.forEach(s => {
      const key   = (s.state || '').toLowerCase();
      const color = colorMap[key] || '#888';
      const row   = document.createElement('div');
      row.className = 'student-row';
      row.innerHTML = `
        <span class="s-id">S${s.id}</span>
        <span class="s-dot" style="background:${color}"></span>
        <span class="s-state">${s.state}</span>
        <div class="s-bar">
          <div class="s-fill" style="width:${s.score}%;background:${color}"></div>
        </div>
        <span class="s-pct" style="color:${color}">${s.score}%</span>
      `;
      list.appendChild(row);
    });
  }


  if (chart && d.timeline && d.timeline.length > 0) {
    chart.data.labels             = d.timeline.map(p => p.time);
    chart.data.datasets[0].data   = d.timeline.map(p => p.attention);
    chart.data.datasets[1].data   = d.timeline.map(() => 60);
    chart.update('none');
  }


  const alertList = document.getElementById('alert-list');
  alertList.innerHTML = '';

  if (d.alerts && d.alerts.length > 0) {
    d.alerts.forEach(a => {
      const el    = document.createElement('div');
      el.className = `alert-item ${a.level || 'warning'}`;
      el.innerHTML = `
        <span class="a-time">${a.time}</span>
        <span class="a-msg">${a.message}</span>
      `;
      alertList.appendChild(el);
    });
  } else {
    alertList.innerHTML = '<div class="empty-msg">No alerts — class is on track ✓</div>';
  }


  const badge = document.getElementById('session-badge');
  if (d.session_active) {
    badge.textContent = '● Recording';
    badge.classList.add('active');
  } else if (!badge.classList.contains('ended')) {
    badge.textContent = 'No active session';
    badge.classList.remove('active');
  }
}

function connectSSE() {
  const src = new EventSource('/stream');

  src.onmessage = e => {
    try { updateDashboard(JSON.parse(e.data)); }
    catch (err) { console.warn('SSE parse error', err); }
  };

  src.onerror = () => {
    src.close();
    console.warn('[SSE] Reconnecting in 3s…');
    setTimeout(connectSSE, 3000);
  };
}

async function startSession() {
  const name = document.getElementById('session-name').value.trim()
               || `Session — ${new Date().toLocaleString()}`;

  const res  = await fetch('/api/start_session', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ name }),
  });
  const data = await res.json();

  if (data.status === 'ok') {
    sessionId = data.session_id;

    const badge = document.getElementById('session-badge');
    badge.textContent = `● ${data.name}`;
    badge.classList.add('active');
    badge.classList.remove('ended');

    document.getElementById('btn-report').style.display = 'none';


    chart.data.labels = [];
    chart.data.datasets.forEach(ds => ds.data = []);
    chart.update();

    console.log(`[Session] Started: id=${sessionId} name="${data.name}"`);
  }
}

async function endSession() {
  if (!confirm('End this session and save the report?')) return;

  const res  = await fetch('/api/end_session', { method: 'POST' });
  const data = await res.json();

  if (data.status === 'ok') {
    sessionId = data.session_id;

    const badge = document.getElementById('session-badge');
    badge.textContent = 'Session saved';
    badge.classList.remove('active');
    badge.classList.add('ended');

    const btn    = document.getElementById('btn-report');
    btn.style.display = 'inline-block';
    btn.onclick  = () => window.open(`/report/${sessionId}`, '_blank');

    console.log(`[Session] Ended: id=${sessionId}`);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initChart();
  connectSSE();
  document.getElementById('btn-start').addEventListener('click', startSession);
  document.getElementById('btn-end').addEventListener('click', endSession);
});
