# E-Waste Value Appraiser — complete source bundle

Generated 2026-11-12. Every source file in the repo, in one document.
Vendored Leaflet (148 KB, third-party) and binary icons are excluded —
they are already in the git repo.

**Prefer the git repo over pasting this.** It is ~125 KB of code, which
will consume a large share of a new chat's context. Push the repo and let
the agent read it instead; paste `HANDOFF.md` as the brief.

The HTML alone will not run — it needs the Python backend for the
valuation engine and for calling Gemini without exposing the API key.

---

## Contents

1. `static/index.html`
2. `static/app.js`
3. `static/styles.css`
4. `static/sw.js`
5. `static/manifest.json`
6. `server.py`
7. `engine/knowledge.py`
8. `engine/vision.py`
9. `engine/appraisal.py`
10. `engine/overrides.py`
11. `engine/store.py`
12. `requirements.txt`
13. `runtime.txt`
14. `Procfile`
15. `render.yaml`
16. `PHONE_URL.txt`

---


## `static/index.html`

````html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,maximum-scale=1">
<meta name="theme-color" content="#0B0F0C">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="/manifest.json">
<title>E-Waste Value Appraiser</title>
<link rel="stylesheet" href="/vendor/leaflet.css">
<link rel="stylesheet" href="/styles.css">
</head>
<body>

<!-- ============================================================ HOME -->
<section class="screen active" id="screen-home">
  <header class="topbar">
    <div>
      <h1 class="brand">E-Waste <span>Value Appraiser</span></h1>
      <p class="tagline">Point. Shoot. Know what it is worth.</p>
    </div>
    <div class="engbadge" id="engine-badge">heuristic</div>
  </header>

  <div class="statstrip" id="statstrip">
    <div class="stat"><b id="st-scans">0</b><span>scans</span></div>
    <div class="stat"><b id="st-kg">0</b><span>kg</span></div>
    <div class="stat"><b id="st-val">0</b><span>value</span></div>
    <div class="stat tappable" id="st-co2-box"><b id="st-co2">0</b><span>CO2 kg ?</span></div>
  </div>

  <div class="bigcards">
    <button class="bigcard scan" id="go-scan">
      <svg viewBox="0 0 24 24" class="ico"><path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2"/><rect x="8" y="8" width="8" height="8" rx="2"/></svg>
      <b>SCAN</b><span>Identify &amp; appraise</span>
    </button>
    <button class="bigcard map" id="go-map">
      <svg viewBox="0 0 24 24" class="ico"><path d="M12 21s7-6 7-11a7 7 0 1 0-14 0c0 5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>
      <b>MAP</b><span>Drop pin &amp; find recyclers</span>
    </button>
  </div>

  <div class="quickcats" id="quickcats"></div>

  <h3 class="sechead">Recent scans</h3>
  <div id="recent" class="recent"></div>
</section>

<!-- ============================================================ SCAN -->
<section class="screen" id="screen-scan">
  <header class="topbar simple">
    <button class="back" data-back>&larr;</button>
    <h2>Scan an item</h2>
    <span></span>
  </header>

  <div class="camwrap">
    <video id="video" playsinline autoplay muted></video>
    <canvas id="canvas" hidden></canvas>
    <img id="preview" hidden alt="captured">
    <div class="reticle"><div class="corner tl"></div><div class="corner tr"></div>
      <div class="corner bl"></div><div class="corner br"></div>
      <p class="hint">Centre the item &mdash; or upload a photo</p>
    </div>
  </div>

  <div class="scanmodes">
    <button class="chip active" data-hint="electronic">Auto detect</button>
    <button class="chip" data-hint="e">Force e-waste</button>
    <button class="chip" data-hint="w">Force general</button>
  </div>

  <div class="scanactions">
    <button class="ghost" id="btn-upload">Upload</button>
    <button class="shutter" id="btn-capture" aria-label="Capture"></button>
    <button class="ghost" id="btn-switch">Flip</button>
  </div>
  <input type="file" id="file" accept="image/*" hidden>

  <div id="scanmsg" class="scanmsg"></div>
</section>

<!-- ========================================================== RESULT -->
<section class="screen" id="screen-result">
  <header class="topbar simple">
    <button class="back" data-back>&larr;</button>
    <h2>Appraisal</h2>
    <button class="ghost sm" id="btn-rescan">Rescan</button>
  </header>
  <div id="result-body" class="resultbody"></div>
</section>

<!-- ============================================================= MAP -->
<section class="screen" id="screen-map">
  <header class="topbar simple">
    <button class="back" data-back>&larr;</button>
    <h2>Waste map</h2>
    <button class="ghost sm" id="btn-locate">Locate</button>
  </header>
  <div id="map"></div>
  <div class="mapfilters" id="mapfilters">
    <button class="chip active" data-layer="recyclers">Recyclers</button>
    <button class="chip active" data-layer="reports">Reports</button>
    <button class="chip active" data-layer="listings">Listings</button>
    <button class="chip" data-layer="heat">Heatmap</button>
  </div>
  <button class="fab" id="btn-droppin">+</button>
</section>

<!-- ========================================================= SETTINGS -->
<section class="screen" id="screen-settings">
  <header class="topbar simple"><span></span><h2>Settings</h2><span></span></header>
  <div class="settings">
    <h3 class="sechead">Analysis engine</h3>
    <p class="note" id="engine-note"></p>

    <h3 class="sechead">Recovery cost (Rs per kg of feed)</h3>
    <div id="ed-costs"></div>

    <h3 class="sechead">Processing route cost (Rs per kg)</h3>
    <p class="note">Charged per item type &mdash; refining a PCB costs far more per kg
      than shredding a steel appliance.</p>
    <div id="ed-proc"></div>

    <h3 class="sechead">Metals &mdash; price, recovery %, CO2 factor</h3>
    <p class="note">Price shows Rs/g for precious metals, Rs/kg otherwise.
      CO2 factor = kg of CO2 avoided per kg of that metal recycled.</p>
    <div id="ed-metals"></div>

    <h3 class="sechead">Devices &mdash; weight (g) &amp; mineral yield</h3>
    <select id="dev-pick" class="pickrow"></select>
    <div id="ed-dev"></div>

    <h3 class="sechead">General waste &mdash; weight (g) &amp; rate (Rs/kg)</h3>
    <div id="ed-items"></div>

    <h3 class="sechead">Data</h3>
    <button class="ghost" id="btn-clear">Clear scan history</button>
    <button class="ghost warnbtn" id="btn-reset">Reset all numbers to defaults</button>

    <h3 class="sechead">About</h3>
    <p class="note">Metal prices captured <b id="price-date">-</b> from published Indian
      market rates. Recovery yields are published PCB / device assay ranges.
      All figures are <b>estimates, not a guaranteed payout</b>.</p>
  </div>
</section>

<!-- ======================================================= TAB BAR -->
<nav class="tabbar">
  <button class="tab active" data-screen="screen-home">
    <svg viewBox="0 0 24 24"><path d="M3 11l9-8 9 8M5 10v10h14V10"/></svg><span>Home</span></button>
  <button class="tab" data-screen="screen-scan">
    <svg viewBox="0 0 24 24"><path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/></svg><span>Scan</span></button>
  <button class="tab" data-screen="screen-map">
    <svg viewBox="0 0 24 24"><path d="M12 21s7-6 7-11a7 7 0 1 0-14 0c0 5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></svg><span>Map</span></button>
  <button class="tab" data-screen="screen-settings">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/></svg><span>Settings</span></button>
</nav>

<!-- ==================================================== PIN MODAL -->
<div class="modal" id="modal-pin" hidden>
  <div class="sheet">
    <h3>Drop a pin</h3>
    <p class="note" id="pin-address">Locating…</p>
    <div class="segmented">
      <button class="seg active" data-mode="report">Report dumping</button>
      <button class="seg" data-mode="listing">List my e-waste</button>
    </div>
    <div id="pin-fields"></div>
    <div class="sheetbtns">
      <button class="ghost" data-close>Cancel</button>
      <button class="primary" id="btn-publish">Publish</button>
    </div>
  </div>
</div>

<div class="toast" id="toast" hidden></div>

<script src="/vendor/leaflet.js"></script>
<script src="/app.js"></script>
</body>
</html>

````


## `static/app.js`

````javascript
/* E-Waste Value Appraiser - PWA client */
'use strict';

const S = {
  screen: 'screen-home',
  result: null,          // last /api/analyze payload
  appraisal: null,
  key: null,
  catalog: [],
  costs: null,
  prices: {},            // metal overrides
  hint: 'auto',
  stream: null,
  facing: 'environment',
  map: null, layers: {}, pending: null, pinMode: 'report',
  home: { lat: 13.0827, lng: 80.2707 },
};

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const fmt = n => (Math.round(n * 100) / 100).toLocaleString('en-IN');
const rs = n => '₹' + fmt(n);

function esc(s) {
  return String(s).replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}

function toast(msg, ms = 2600) {
  const t = $('#toast'); t.textContent = msg; t.hidden = false;
  clearTimeout(t._t); t._t = setTimeout(() => (t.hidden = true), ms);
}

/* ------------------------------------------------------------ navigation */
function show(id) {
  $$('.screen').forEach(s => s.classList.toggle('active', s.id === id));
  $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.screen === id));
  S.screen = id;
  window.scrollTo(0, 0);
  if (id === 'screen-map') setTimeout(initMap, 30);
  if (id === 'screen-home') loadHome();
  if (id === 'screen-settings') loadSettings();
  if (id === 'screen-scan') startCamera();
  if (id !== 'screen-scan') stopCamera();
}
$$('.tab').forEach(t => t.onclick = () => show(t.dataset.screen));
$$('[data-back]').forEach(b => b.onclick = () => show('screen-home'));
$('#go-scan').onclick = () => show('screen-scan');
$('#go-map').onclick = () => show('screen-map');
$('#btn-rescan').onclick = () => show('screen-scan');

/* --------------------------------------------------------------- camera */
async function startCamera() {
  const v = $('#video');
  $('#preview').hidden = true; v.hidden = false;
  try {
    stopCamera();
    S.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: S.facing }, audio: false });
    v.srcObject = S.stream; await v.play().catch(() => {});
  } catch (e) {
    $('#scanmsg').textContent = 'Camera unavailable — use Upload instead.';
  }
}
function stopCamera() {
  if (S.stream) { S.stream.getTracks().forEach(t => t.stop()); S.stream = null; }
}
$('#btn-switch').onclick = () => {
  S.facing = S.facing === 'environment' ? 'user' : 'environment'; startCamera();
};
$('#btn-upload').onclick = () => $('#file').click();
$('#file').onchange = e => { if (e.target.files[0]) send(e.target.files[0]); };
$('#btn-capture').onclick = () => {
  const v = $('#video'), c = $('#canvas');
  if (!v.videoWidth) return toast('Camera not ready — use Upload');
  c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext('2d').drawImage(v, 0, 0);
  c.toBlob(b => { if (b) send(new File([b], 'scan.jpg', { type: 'image/jpeg' })); },
    'image/jpeg', 0.85);
};
$$('.scanmodes .chip').forEach(c => c.onclick = () => {
  $$('.scanmodes .chip').forEach(x => x.classList.remove('active'));
  c.classList.add('active'); S.hint = c.dataset.hint;
});

/* --------------------------------------------------------------- analyse */
async function send(file) {
  const msg = $('#scanmsg');
  msg.textContent = 'Analysing…';
  const fd = new FormData();
  fd.append('file', file); fd.append('record', '1');
  try {
    const r = await fetch('/api/analyze', { method: 'POST', body: fd });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const data = await r.json();
    S.result = data;
    S.key = data.guess ? data.guess.key : null;
    S.appraisal = data.appraisal || null;
    renderResult(); show('screen-result');
    msg.textContent = '';
  } catch (e) {
    msg.textContent = 'Analysis failed: ' + e.message;
  }
}

/* ---------------------------------------------------------------- result */
async function reAppraise(key, qty = 1, weightG = null, rate = null,
                          aiLabel = null, record = false) {
  // remember the model's wording so it survives weight/quantity tweaks
  if (aiLabel) { S.aiLabel = aiLabel; S.aiLabelKey = key; }
  const label = aiLabel || (S.aiLabelKey === key ? S.aiLabel : null);
  const body = { key, quantity: qty, confidence: S.result?.verdict?.confidence ?? 0,
                 engine: S.result?.verdict?.engine ?? 'manual',
                 costs: S.costs, prices: S.prices, record: record || !!aiLabel };
  if (label) body.ai_label = label;
  if (weightG !== null && weightG !== undefined && weightG !== '') body.weight_g = weightG;
  if (rate !== null && rate !== undefined && rate !== '') body.rate = rate;
  const r = await fetch('/api/appraise', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body) });
  S.appraisal = await r.json(); S.key = key;
  renderResult();
}

function renderResult() {
  const res = S.result, ap = S.appraisal;
  if (!res || !ap) return;
  const v = res.verdict;
  const isE = ap.is_electronic === true;      // drives the E-WASTE / OTHER banner
  const mineralView = ap.kind !== 'waste';    // copper cable is general waste but
                                              // is still valued by mineral recovery
  // v.confidence is P(electronic); flip it when the verdict is the general stream
  const streamPct = Math.round((isE ? (v.confidence ?? 0) : 1 - (v.confidence ?? 0)) * 100);
  const matchPct = Math.round((res.guess?.score ?? 0) * 100);
  const conf = streamPct;

  let h = '';
  /* ---- verdict banner ---- */
  h += `<div class="verdict ${isE ? 'ewaste' : (v.stream === 'unknown' ? 'unknown' : 'other')}">
    <div class="vtag">${isE ? 'Electronic waste' : 'Non-electronic waste'}</div>
    <div class="vname">${ap.display_label || ap.label}</div>
    <div class="vsub">${v.message}</div>
    <div class="confbar ${isE ? 'p' : ''}"><i style="width:${streamPct}%"></i></div>
    <div class="vsub">${isE ? 'E-waste' : 'General waste'} confidence ${streamPct}%
      &middot; best match ${matchPct}% &middot; engine ${v.engine}</div>
  </div>`;

  /* what the vision model actually reported, so a wrong guess is visible and
     easy to correct rather than being hidden behind a confident number */
  /* if the model was configured but failed, say so - a silent fallback to the
     colour heuristic looks like a confident answer when it is only a guess */
  if (res.ai_error) {
    h += `<div class="tip" style="background:#2A2410;border-color:#6B5A1F;color:#FDE68A">
      <b>AI unavailable for this scan</b> &mdash; fell back to the offline estimate,
      which only matches colour and texture. Check your connection and rescan for a
      proper identification.<br><span class="mut" style="font-size:11px">${
        String(res.ai_error).slice(0, 110)}</span></div>`;
  }

  const av = res.ai_view;
  if (av && (av.description || av.materials)) {
    h += `<div class="card aiview"><h4>What the AI saw</h4>
      <div class="aidesc">${av.description || av.label || '-'}</div>
      ${av.materials ? `<div class="rowline"><span class="mut">Materials seen</span>
        <span>${av.materials}</span></div>` : ''}
      ${av.matched ? '' : `<p class="note" style="margin-top:8px">No exact catalogue
        match for this &mdash; choose the closest item below.</p>`}
    </div>`;
  }

  if (ap.hazardous) h += `<div class="warn"><b>Safety first.</b> ${ap.note ||
    'Do not open, puncture or burn this. Hand it to an authorised collector.'}</div>`;

  /* ---- confirm / correct ---- */
  const cands = res.candidates || [];
  if (cands.length) {
    const hasAI = cands.some(c => c.source === 'ai');
    h += `<div class="card"><h4>Confirm what it is</h4>
      <p class="note" style="margin:-4px 0 10px">Tap an option to value it${
        hasAI ? ' — the &#9889; one is what the AI identified' : ''}.</p>
      <div class="cands">`;
    cands.forEach(c => h += `<button class="cand ${c.key === ap.key ? 'on' : ''}${
        c.source === 'ai' ? ' ai' : ''}"
      data-key="${esc(c.key)}" data-ai="${c.source === 'ai' ? esc(c.display || '') : ''}"
      ${c.source === 'ai' ? 'title="AI identification"' : ''}>
      ${c.source === 'ai' ? '&#9889; ' : ''}${esc(c.display || c.label)}
      · ${Math.round((c.score || 0) * 100)}%</button>`);
    h += `</div><div class="rowline"><span class="mut">Not in the list?</span></div>
      <select id="pick" style="width:100%;background:#0B0F0C;border:1px solid #26332B;
      border-radius:11px;padding:11px;color:#E8F0EA;margin-top:6px">
      <option value="">Choose the exact item…</option>
      ${S.catalog.map(i => `<option value="${i.key}" ${i.key === ap.key ? 'selected' : ''}>
        ${i.is_electronic ? '⚡ ' : ''}${i.label}</option>`).join('')}
      </select></div>`;
  }

  /* ---- minerals (e-waste + metal scrap streams) ---- */
  if (mineralView) {
    h += `<div class="card"><h4>What it is made of — recoverable minerals</h4>
      <table class="mini"><tr><th>Mineral</th><th>Yield</th><th>Recov.</th>
      <th>Recovered</th><th style="text-align:right">Value</th></tr>`;
    ap.minerals.forEach(m => {
      h += `<tr><td>${m.symbol} · ${m.name}${m.precious ? ' <b class="gold">★</b>' : ''}</td>
        <td>${m.yield_display} ${m.yield_unit}</td>
        <td>${Math.round(m.recovery * 100)}%</td>
        <td>${m.in_feed} ${m.in_feed_unit}</td>
        <td class="num">${rs(m.value)}</td></tr>`;
    });
    h += `</table><p class="note" style="margin-top:9px">Yields are published assay
      ranges; recovery is the share actually extracted by the refining route.
      ★ = precious metal.</p></div>`;

    h += `<div class="card"><h4>Component breakdown</h4>`;
    ap.components.forEach(c => h += `<div class="rowline"><span>${c.name}
      <small class="mut">· ${c.carries}</small></span><span>${c.share}%</span></div>`);
    h += `</div>`;

    /* cost & profit */
    h += `<div class="card"><h4>Cost &amp; profit</h4>
      <div class="rowline"><span>Gross metal value</span><span>${rs(ap.gross)}</span></div>`;
    Object.entries(ap.costs || {}).forEach(([k, val]) =>
      h += `<div class="rowline"><span class="mut">− ${k}</span>
        <span class="red">${rs(val)}</span></div>`);
    // some streams (CRT glass, for one) genuinely cost more to process than they return
    const neg = ap.net < 0;
    h += `<div class="rowline"><span><b>${neg ? 'Net cost to recycle' : 'Net profit'}</b></span>
      <span class="${neg ? 'red' : 'green'}"><b>${rs(ap.net)}</b></span></div>
      <div class="rowline"><span class="mut">Margin</span><span>${ap.margin}%</span></div>
      <div class="rowline"><span class="mut">Feed weight</span><span>${ap.total_kg} kg
        (${ap.quantity} × ${ap.unit_weight_g} g)</span></div>
      <div class="rowline"><span class="mut">Per tonne</span>
        <span class="${neg ? 'red' : 'gold'}">${rs(ap.per_tonne_net)}</span></div>
      <div class="rowline"><span class="mut">CO₂ avoided</span>
        <span>${ap.co2_saved_kg} kg</span></div></div>`;

    /* disposal guidance for non-electronic streams that are still mineral-valued
       (copper cable is general waste, not e-waste) */
    if (!isE && ap.bin) {
      const BIN = { wet: 'WET / biodegradable', dry: 'DRY',
        recyclable: 'RECYCLABLE / dry', hazardous: 'HAZARDOUS' };
      h += `<div class="card"><h4>Disposal</h4>
        <div class="rowline"><span>Bin</span><span><b>${BIN[ap.bin] || ap.bin}</b></span></div>
        <div class="rowline"><span>Decomposition</span><span>${ap.decomposition || '-'}</span></div>
        <p class="note" style="margin-top:9px">${ap.note || ''}</p></div>`;
    }

    /* weight + quantity - both editable, because the catalogue weight is only a
       typical figure and the user knows what their item actually weighs */
    h += `<div class="card"><h4>Weight &amp; quantity</h4>
      <div class="wgrid">
        <label>Weight per unit
          <input id="in-w" type="number" min="0" step="1" value="${ap.unit_weight_g}">
          <span>g</span></label>
        <label>Quantity
          <input id="in-q" type="number" min="1" step="1" value="${ap.quantity}">
          <span>units</span></label>
      </div>
      <div class="rowline"><span>Total feed weight</span>
        <span id="out-kg">${ap.total_kg} kg</span></div>
      <div class="scale">
        ${[1, 10, 100, 1000].map(n => `<button data-qty="${n}"
          class="${ap.quantity == n ? 'on' : ''}">${n}×</button>`).join('')}
        <button data-tonne="1">1 tonne</button></div>
      <p class="note" style="margin-top:9px">Catalogue default for this item is
      ${(S.catalog.find(c => c.key === ap.key) || {}).avg_weight_g ?? ap.unit_weight_g} g
      &mdash; change it to your actual weight.
      Pricing as on ${ap.price_date}.</p></div>`;
  } else {
    /* ---- general waste ---- */
    h += `<div class="card"><h4>Disposal</h4>
      <div class="rowline"><span>Bin</span><span><b>${
        { wet: 'WET / biodegradable', dry: 'DRY', recyclable: 'RECYCLABLE / dry',
          hazardous: 'HAZARDOUS' }[ap.bin] || ap.bin}</b></span></div>
      <div class="rowline"><span>Decomposition</span><span>${ap.decomposition}</span></div>
      <ul class="adv" style="margin-top:10px">${ap.advice.map(a => `<li>${a}</li>`).join('')}</ul>
      </div>`;

    h += `<div class="card"><h4>Material composition</h4>`;
    ap.materials.forEach(m => h += `<div class="rowline"><span>${m.name}
      <small class="mut">· becomes ${m.becomes}</small></span>
      <span>${m.share}%</span></div>`);
    h += `</div>`;

    h += `<div class="card"><h4>Scrap value</h4>
      <div class="rowline"><span>Weight</span><span>${ap.total_kg} kg</span></div>
      <div class="rowline"><span>Rate</span><span>${rs(ap.rate)} / kg</span></div>
      <div class="rowline"><span><b>Value</b></span>
        <span class="green"><b>${rs(ap.gross)}</b></span></div>
      <div class="rowline"><span class="mut">CO₂ avoided</span>
        <span>${ap.co2_saved_kg} kg</span></div></div>`;

    /* weight editor - free numeric entry, quick presets underneath */
    h += `<div class="card"><h4>Weight</h4>
      <div class="wgrid">
        <label>Weight
          <input id="in-w" type="number" min="0" step="1" value="${Math.round(ap.total_kg * 1000)}">
          <span>g</span></label>
        <label>Scrap rate
          <input id="in-rate" type="number" min="0" step="0.5" value="${ap.rate}">
          <span>Rs/kg</span></label>
      </div>
      <div class="scale">
        ${[10, 100, 500, 1000].map(g => `<button data-w="${g}">${g} g</button>`).join('')}
      </div></div>`;
  }

  h += `<div class="actions">
    <button class="ghost" id="btn-pin">Drop pin on map</button>
    <button class="primary" id="btn-find">Find a recycler</button></div>
    <p class="note" style="margin-top:12px">Estimate only — not a guaranteed payout.
    Dealers typically realise 60–70% of gross metal value.</p>`;

  const body = $('#result-body'); body.innerHTML = h;

  body.querySelectorAll('.cand').forEach(b =>
    b.onclick = () => reAppraise(b.dataset.key, 1, null, null,
                                 b.dataset.ai || null));
  const pick = $('#pick');
  if (pick) pick.onchange = () => pick.value && reAppraise(pick.value, 1, null, null, null, true);
  const keep = () => (S.aiLabelKey === ap.key ? S.aiLabel : null);
  body.querySelectorAll('[data-qty]').forEach(b =>
    b.onclick = () => reAppraise(ap.key, +b.dataset.qty, null, null, keep()));
  body.querySelectorAll('[data-tonne]').forEach(b =>
    b.onclick = () => reAppraise(ap.key, 1000 / (ap.unit_weight_g / 1000),
                                 null, null, keep()));
  body.querySelectorAll('[data-w]').forEach(b =>
    b.onclick = () => reAppraise(ap.key, 1, +b.dataset.w, null, keep()));

  // direct weight / quantity / rate entry
  const inW = $('#in-w'), inQ = $('#in-q'), inR = $('#in-rate');
  const applyNumeric = () => {
    const w = inW ? +inW.value : null;
    const q = inQ ? +inQ.value : null;
    const r = inR ? +inR.value : null;
    const keep = S.aiLabelKey === ap.key ? S.aiLabel : null;
    if (inR) return reAppraise(ap.key, 1, w, r, keep);      // general waste
    return reAppraise(ap.key, (q && q > 0 ? q : 1), w, null, keep);  // e-waste / metal
  };
  [inW, inQ, inR].forEach(el => { if (el) el.onchange = applyNumeric; });

  $('#btn-pin').onclick = () => {
    S.pending = { lat: S.home.lat, lng: S.home.lng, item_key: ap.key, label: ap.label };
    openPin(S.home.lat, S.home.lng);
  };
  $('#btn-find').onclick = () => { show('screen-map'); setTimeout(() => {
    if (S.map) { S.map.setView([S.home.lat, S.home.lng], 13); }
  }, 400); };
}

/* ------------------------------------------------------------------- map */
function icon(color) {
  return L.divIcon({ className: '', html: `<div class="pin-icon" style="width:18px;height:18px;
    background:${color}"></div>`, iconSize: [18, 18], iconAnchor: [9, 9] });
}
async function initMap() {
  if (S.map) { S.map.invalidateSize(); return; }
  S.map = L.map('map', { zoomControl: false }).setView([S.home.lat, S.home.lng], 12);
  // Same-origin tiles: the server proxies a real tile provider with a browser
  // UA and rejects the placeholder stubs these services hand to datacenters.
  L.tileLayer('/tiles/{z}/{x}/{y}.png', {
    maxZoom: 17,
    attribution: '&copy; OpenStreetMap contributors | style &copy; OpenTopoMap'
  }).addTo(S.map);
  L.control.zoom({ position: 'bottomright' }).addTo(S.map);
  S.layers.recyclers = L.layerGroup().addTo(S.map);
  S.layers.reports = L.layerGroup().addTo(S.map);
  S.layers.listings = L.layerGroup().addTo(S.map);
  S.layers.heat = L.layerGroup();
  S.map.on('contextmenu', e => { S.pending = { lat: e.latlng.lat, lng: e.latlng.lng };
    openPin(e.latlng.lat, e.latlng.lng); });
  loadMap();
  // Leaflet measures the container once; if the screen was still laying out the
  // map ends up 0px tall and renders blank. Re-measure once things settle.
  [60, 250, 600].forEach(d => setTimeout(() => {
    if (S.map && document.getElementById('screen-map').classList.contains('active')) {
      S.map.invalidateSize();
    }
  }, d));
  if (navigator.geolocation) navigator.geolocation.getCurrentPosition(p => {
    S.home = { lat: p.coords.latitude, lng: p.coords.longitude };
    S.map.setView([S.home.lat, S.home.lng], 13); loadMap();
  }, () => {}, { timeout: 7000 });
}
async function loadMap() {
  const d = await (await fetch(`/api/map?lat=${S.home.lat}&lng=${S.home.lng}&radius=30`)).json();
  S.layers.recyclers.clearLayers(); S.layers.reports.clearLayers();
  S.layers.listings.clearLayers(); S.layers.heat.clearLayers();
  (d.recyclers || []).forEach(r => L.marker([r.lat, r.lng], { icon: icon('#22C55E') })
    .addTo(S.layers.recyclers).bindPopup(
      `<b>${r.name}</b><br>${r.type} · ${r.distance_km} km<br>
       <span style="color:#8FA396">${r.accepts}</span><br>
       <a href="tel:${r.phone}" style="color:#4ADE80">${r.phone}</a>`));
  (d.reports || []).forEach(r => L.marker([r.lat, r.lng], { icon: icon('#EF4444') })
    .addTo(S.layers.reports).bindPopup(
      `<b>${r.category}</b> · ${r.severity}<br>${r.note || ''}<br>
       <span style="color:#8FA396">${r.address || ''}</span><br>👍 ${r.upvotes}`));
  (d.listings || []).forEach(l => L.marker([l.lat, l.lng], { icon: icon('#38BDF8') })
    .addTo(S.layers.listings).bindPopup(
      `<b>${l.label}</b> ×${l.qty}<br>Asking ${rs(l.asking)}<br>
       <span style="color:#8FA396">${l.address || ''}</span>`));
  (d.reports || []).forEach(r => L.circle([r.lat, r.lng], {
    radius: 260, color: '#EF4444', weight: 1, fillColor: '#EF4444', fillOpacity: .16 })
    .addTo(S.layers.heat));
}
$('#btn-locate').onclick = () => {
  if (navigator.geolocation) navigator.geolocation.getCurrentPosition(p => {
    S.home = { lat: p.coords.latitude, lng: p.coords.longitude };
    S.map.setView([S.home.lat, S.home.lng], 14); loadMap(); toast('Located');
  }, () => toast('Location unavailable'));
};
$$('#mapfilters .chip').forEach(c => c.onclick = () => {
  c.classList.toggle('active');
  const on = c.classList.contains('active'), layer = S.layers[c.dataset.layer];
  if (!layer || !S.map) return;
  on ? S.map.addLayer(layer) : S.map.removeLayer(layer);
});
$('#btn-droppin').onclick = () => {
  const c = S.map ? S.map.getCenter() : S.home;
  S.pending = { lat: c.lat, lng: c.lng }; openPin(c.lat, c.lng);
};

/* ------------------------------------------------------------ pin modal */
async function openPin(lat, lng) {
  $('#modal-pin').hidden = false;
  $('#pin-address').textContent = 'Locating…';
  const addr = await (await fetch('/api/map')).json();   // warm-up
  try {
    const g = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`);
    const j = await g.json();
    $('#pin-address').textContent = (j.display_name || '').slice(0, 150) ||
      `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  } catch { $('#pin-address').textContent = `${lat.toFixed(4)}, ${lng.toFixed(4)}`; }
  renderPinFields();
}
function renderPinFields() {
  const mode = S.pinMode;
  const opts = S.catalog.map(i =>
    `<option value="${i.key}" ${S.pending.item_key === i.key ? 'selected' : ''}>${i.label}</option>`).join('');
  $('#pin-fields').innerHTML = mode === 'report'
    ? `<label>Category</label><select id="f-cat">
        <option value="e-waste">Electronic waste</option>
        <option value="plastic">Plastic</option>
        <option value="organic">Organic / wet</option>
        <option value="hazardous">Hazardous</option></select>
       <label>Severity</label><select id="f-sev">
        <option value="low">Low</option><option value="medium" selected>Medium</option>
        <option value="high">High</option></select>
       <label>Note</label><textarea id="f-note" rows="2" placeholder="What is dumped here?"></textarea>`
    : `<label>Item</label><select id="f-item">${opts}</select>
       <label>Quantity</label><input id="f-qty" type="number" value="1" min="1">
       <label>Asking price (₹) — blank = auto</label><input id="f-ask" type="number" placeholder="auto">`;
}
$$('.seg').forEach(s => s.onclick = () => {
  $$('.seg').forEach(x => x.classList.remove('active'));
  s.classList.add('active'); S.pinMode = s.dataset.mode; renderPinFields();
});
$$('[data-close]').forEach(b => b.onclick = () => ($('#modal-pin').hidden = true));
$('#btn-publish').onclick = async () => {
  const p = S.pending; if (!p) return;
  if (S.pinMode === 'report') {
    await fetch('/api/report', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat: p.lat, lng: p.lng, category: $('#f-cat').value,
        severity: $('#f-sev').value, note: $('#f-note').value }) });
    toast('Dumping reported. Thank you.');
  } else {
    const r = await (await fetch('/api/listing', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat: p.lat, lng: p.lng, item_key: $('#f-item').value,
        qty: +$('#f-qty').value || 1, asking: $('#f-ask').value || null }) })).json();
    toast(`Listed • suggested price ${rs(r.suggested_price || 0)}`);
  }
  $('#modal-pin').hidden = true; loadMap();
};

/* ----------------------------------------------------------------- home */
async function loadHome() {
  const [cat, hist] = await Promise.all([
    fetch('/api/catalog').then(r => r.json()),
    fetch('/api/history?limit=20').then(r => r.json())]);
  S.catalog = cat.items; S.costs = cat.costs;
  $('#price-date').textContent = cat.price_date;
  const h = hist.history || [];
  const st = await fetch('/api/stats').then(r => r.json());
  $('#st-scans').textContent = st.scans;
  $('#st-kg').textContent = st.kg.toFixed(1);
  $('#st-val').textContent = '₹' + fmt(st.value);
  $('#st-co2').textContent = st.co2.toFixed(1);

  const quick = ['motherboard', 'smartphone', 'liion_battery', 'laptop',
    'pet_bottle', 'alu_can', 'cardboard', 'fruit_peel'];
  $('#quickcats').innerHTML = quick.map(k => {
    const it = S.catalog.find(c => c.key === k);
    return it ? `<button class="chip" data-q="${k}">${it.is_electronic ? '⚡ ' : ''}${it.label}</button>` : '';
  }).join('');
  $$('#quickcats [data-q]').forEach(b => b.onclick = () => {
    S.result = { verdict: { confidence: 1, message: 'Selected manually.',
      engine: 'manual', stream: 'manual' }, candidates: [] };
    reAppraise(b.dataset.q, 1, null, null, null, true); show('screen-result');
  });

  $('#recent').innerHTML = h.length
    ? h.slice(0, 10).map(r => `<div class="rcard"><b>${r.label}</b>
        <span>${r.is_electronic ? '⚡ e-waste' : 'general'}</span>
        <div class="v">${rs(r.value || 0)}</div></div>`).join('')
    : '<p class="empty">No scans yet — tap SCAN to appraise your first item.</p>';
}

/* ------------------------------------------------------------ CO2 note */
/* CO2 "avoided" = the emissions you do NOT cause by recovering metal from
   scrap instead of mining and refining virgin ore. It is a saving, not a
   release: recycling aluminium avoids ~9 kg CO2 per kg, copper ~3.5,
   gold ~16. Each metal carries its own factor and all of them are editable
   in Settings -> Metals. */
$('#st-co2-box').onclick = () => {
  const top = Object.entries(S.settings?.metals || {})
    .map(([k, m]) => [m.symbol, m.impact, m.name])
    .sort((a, b) => b[1] - a[1]).slice(0, 5)
    .map(([sym, imp, name]) => `${sym} ${imp}/kg`).join('  ·  ');
  toast('CO2 avoided = emissions saved by recovering metal from scrap instead of '
      + 'mining virgin ore. It is a saving, not a release. Factors: ' + top, 7000);
};

/* ------------------------------------------------------------- settings */
/* Every number in the app is editable and persists to overrides.json. */

async function setOverride(body) {
  await fetch('/api/settings', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  toast('Saved');
}

function numRow(labelText, value, step, unit, onSet) {
  const lab = document.createElement('label');
  const t = document.createElement('span'); t.className = 'nl'; t.textContent = labelText;
  const i = document.createElement('input');
  i.type = 'number'; i.step = step; i.value = value;
  const u = document.createElement('span'); u.className = 'unit'; u.textContent = unit || '';
  lab.append(t, i, u);
  i.onchange = () => {
    const v = parseFloat(i.value);
    if (Number.isFinite(v)) onSet(v); else { i.value = value; toast('Enter a number'); }
  };
  return lab;
}

async function loadSettings() {
  const d = await fetch('/api/settings').then(r => r.json());
  S.settings = d;
  $('#price-date').textContent = d.price_date;

  // ---- recovery cost -------------------------------------------------
  const ec = $('#ed-costs'); ec.innerHTML = '';
  Object.entries(d.costs).forEach(([k, v]) => ec.appendChild(
    numRow(k, v, 1, 'Rs/kg', val => setOverride({ costs: { [k]: val } }))));

  // ---- processing route cost -----------------------------------------
  const ep = $('#ed-proc'); ep.innerHTML = '';
  Object.entries(d.devices).forEach(([k, dev]) => ep.appendChild(
    numRow(dev.label, d.processing[k] ?? d.default_processing, 1, 'Rs/kg',
      val => setOverride({ processing: { [k]: val } }))));

  // ---- metals --------------------------------------------------------
  const em = $('#ed-metals'); em.innerHTML = '';
  Object.entries(d.metals).forEach(([k, m]) => {
    const wrap = document.createElement('div'); wrap.className = 'grp';
    const h = document.createElement('h5');
    h.textContent = `${m.symbol} · ${m.name}`; wrap.appendChild(h);
    const perG = m.precious;                       // precious metals shown as Rs/g
    wrap.appendChild(numRow('Price', perG ? m.price / 1000 : m.price,
      perG ? 1 : 0.01, perG ? 'Rs/g' : 'Rs/kg',
      val => setOverride({ metals: { [k]: { price: perG ? val * 1000 : val } } })));
    wrap.appendChild(numRow('Recovery', Math.round(m.recovery * 100), 1, '%',
      val => setOverride({ metals: { [k]: { recovery: Math.min(Math.max(val / 100, 0), 1) } } })));
    wrap.appendChild(numRow('CO2 factor', m.impact, 0.1, 'kg/kg',
      val => setOverride({ impact: { [k]: val } })));
    em.appendChild(wrap);
  });

  // ---- devices: weight + per-metal yield ------------------------------
  const pick = $('#dev-pick');
  const keys = Object.keys(d.devices);
  if (!pick.options.length) {
    keys.forEach(k => {
      const o = document.createElement('option'); o.value = k;
      o.textContent = d.devices[k].label; pick.appendChild(o);
    });
  }
  const renderDev = () => {
    const k = pick.value; const dev = d.devices[k]; if (!dev) return;
    const box = $('#ed-dev'); box.innerHTML = '';
    box.appendChild(numRow(dev.label + ' weight', dev.weight_g, 1, 'g',
      val => setOverride({ devices: { [k]: { weight_g: val } } })));
    Object.entries(dev.yields).forEach(([metal, qty]) => {
      const mm = d.metals[metal] || { symbol: metal, name: metal, precious: false };
      box.appendChild(numRow(`${mm.symbol} yield`,
        mm.precious ? qty * 1000 : qty, mm.precious ? 0.01 : 0.1,
        mm.precious ? 'g/t' : 'kg/t',
        val => setOverride({ devices: { [k]: { yields: { [metal]: mm.precious ? val / 1000 : val } } } })));
    });
  };
  pick.onchange = renderDev; renderDev();

  // ---- general waste --------------------------------------------------
  const ei = $('#ed-items'); ei.innerHTML = '';
  Object.entries(d.items).forEach(([k, it]) => ei.appendChild(
    numRow(`${it.label} — rate`, it.rate, 0.5, 'Rs/kg',
      val => setOverride({ items: { [k]: { rate: val } } }))));
  Object.entries(d.items).forEach(([k, it]) => ei.appendChild(
    numRow(`${it.label} — weight`, it.weight_g, 1, 'g',
      val => setOverride({ items: { [k]: { weight_g: val } } }))));
}

$('#btn-clear').onclick = async () => {
  if (!confirm('Delete every saved scan? This cannot be undone.')) return;
  const r = await (await fetch('/api/history', { method: 'DELETE' })).json();
  toast(`Cleared ${r.removed} scans`); loadHome();
};
$('#btn-reset').onclick = async () => {
  if (!confirm('Reset every edited number back to the shipped defaults?')) return;
  await fetch('/api/settings/reset', { method: 'POST' });
  toast('All numbers reset to defaults'); loadSettings();
};

/* ------------------------------------------------------------- settings */
/* ----------------------------------------------------------------- boot */
(async function boot() {
  const h = await fetch('/api/health').then(r => r.json()).catch(() => null);
  if (h) {
    $('#engine-badge').textContent = h.ai;
    $('#engine-badge').classList.toggle('ai', h.ai !== 'heuristic');
    $('#engine-note').innerHTML = h.ai === 'heuristic'
      ? 'Running the <b>built-in heuristic engine</b> — image features (colour, edges, ' +
        'metallic tone) are matched against the material catalogue. No API key needed, ' +
        'works fully offline. Set <code>AI_PROVIDER</code> and <code>AI_API_KEY</code> ' +
        'on the server to switch to a real vision model.'
      : `Running <b>${h.ai} vision AI</b> — model <code>${h.model || 'auto'}</code>, ` +
        `key ${h.key_loaded ? 'loaded' : 'MISSING'}. Identification is done by the model; ` +
        `valuation still uses the same deterministic engine, so every number stays yours to edit.`;
  }
  loadHome();
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
})();

````


## `static/styles.css`

````css
:root{
  --bg:#0B0F0C; --surface:#141A16; --surface2:#1B241E; --line:#26332B;
  --ink:#E8F0EA; --muted:#8FA396; --accent:#22C55E; --purple:#A855F7;
  --gold:#F5B301; --red:#EF4444; --blue:#38BDF8; --amber:#F59E0B; --copper:#C2703F;
  --safe-b:env(safe-area-inset-bottom,0px);
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0;height:100%}
body{
  background:#050706; color:var(--ink);
  font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  overflow-x:hidden;
}
@media(min-width:520px){
  body{display:flex;justify-content:center;background:#050706}
  .screen,.tabbar{max-width:430px;width:430px;box-shadow:0 0 60px rgba(0,0,0,.6)}
  .tabbar{left:50%;transform:translateX(-50%)}
}
button{font:inherit;color:inherit;cursor:pointer;border:0;background:none}
h1,h2,h3{margin:0}
b{font-weight:700}

/* ------------------------------------------------------------- screens */
.screen{
  display:none; min-height:100vh; min-height:100dvh; background:var(--bg);
  padding:0 0 calc(84px + var(--safe-b));
}
.screen.active{display:block}

.topbar{display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:calc(18px + env(safe-area-inset-top,0px)) 18px 14px}
.topbar.simple{position:sticky;top:0;z-index:20;background:var(--bg);
  border-bottom:1px solid var(--line);padding-bottom:12px}
.topbar h2{font-size:18px}
.brand{font-size:23px;letter-spacing:.2px;line-height:1.1}
.brand span{color:var(--accent)}
.tagline{margin:4px 0 0;font-size:13px;color:var(--muted)}
.engbadge{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);
  border:1px solid var(--line);border-radius:999px;padding:5px 9px;white-space:nowrap}
.engbadge.ai{color:#4ADE80;border-color:#1E3A34;background:#0F1F19}
.back{font-size:22px;padding:4px 10px;color:var(--muted)}

/* --------------------------------------------------------------- stats */
.statstrip{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:0 18px 14px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:14px;
  padding:10px 6px;text-align:center}
.stat b{display:block;font-size:17px;color:var(--accent)}
.stat span{font-size:10.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px}

/* ----------------------------------------------------------- big cards */
.bigcards{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:0 18px}
.bigcard{aspect-ratio:1/1;min-height:150px;border-radius:22px;display:flex;
  flex-direction:column;align-items:center;justify-content:center;gap:6px;
  border:1.5px solid var(--line);background:var(--surface);transition:transform .12s}
.bigcard:active{transform:scale(.97)}
.bigcard b{font-size:19px;letter-spacing:1.2px}
.bigcard span{font-size:11.5px;color:var(--muted);text-align:center;padding:0 8px}
.bigcard.scan{border-color:#1E5E3B;background:linear-gradient(160deg,#132A1D,#0F1A14)}
.bigcard.map{border-color:#22405E;background:linear-gradient(160deg,#12202E,#0F161C)}
.ico{width:42px;height:42px;fill:none;stroke:currentColor;stroke-width:1.6;
  stroke-linecap:round;stroke-linejoin:round}
.bigcard.scan .ico{stroke:var(--accent)}
.bigcard.map .ico{stroke:var(--blue)}

/* --------------------------------------------------------------- chips */
.quickcats{display:flex;gap:7px;overflow-x:auto;padding:14px 18px 4px;
  scrollbar-width:none}
.quickcats::-webkit-scrollbar{display:none}
.chip{flex:0 0 auto;border:1px solid var(--line);background:var(--surface);
  border-radius:999px;padding:7px 13px;font-size:12.5px;color:var(--muted)}
.chip.active{background:var(--accent);color:#04140A;border-color:var(--accent);font-weight:600}

.sechead{font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:1.4px;
  padding:18px 18px 8px}
.recent{display:flex;gap:10px;overflow-x:auto;padding:0 18px;scrollbar-width:none}
.recent::-webkit-scrollbar{display:none}
.rcard{flex:0 0 140px;background:var(--surface);border:1px solid var(--line);
  border-radius:14px;padding:11px}
.rcard b{display:block;font-size:13px;margin-bottom:3px;line-height:1.25}
.rcard span{font-size:11px;color:var(--muted)}
.rcard .v{color:var(--accent);font-weight:700;font-size:14px}
.empty{color:var(--muted);font-size:13px;padding:6px 18px}

/* --------------------------------------------------------------- camera */
.camwrap{position:relative;background:#000;aspect-ratio:3/4;max-height:58vh;
  overflow:hidden;margin:0 14px;border-radius:20px;border:1px solid var(--line)}
#video,#preview{width:100%;height:100%;object-fit:cover;display:block}
.reticle{position:absolute;inset:14%;pointer-events:none;
  display:flex;align-items:center;justify-content:center}
.corner{position:absolute;width:32px;height:32px;border:3px solid var(--accent);opacity:.9}
.corner.tl{top:0;left:0;border-right:0;border-bottom:0;border-radius:10px 0 0 0}
.corner.tr{top:0;right:0;border-left:0;border-bottom:0;border-radius:0 10px 0 0}
.corner.bl{bottom:0;left:0;border-right:0;border-top:0;border-radius:0 0 0 10px}
.corner.br{bottom:0;right:0;border-left:0;border-top:0;border-radius:0 0 10px 0}
.hint{position:absolute;bottom:-34px;left:0;right:0;text-align:center;font-size:12.5px;
  color:var(--muted)}

.scanmodes{display:flex;gap:8px;justify-content:center;padding:44px 18px 10px}
.scanactions{display:flex;align-items:center;justify-content:center;gap:26px;padding:8px 18px}
.shutter{width:74px;height:74px;border-radius:50%;background:var(--accent);
  border:5px solid #0B0F0C;box-shadow:0 0 0 3px var(--accent)}
.shutter:active{transform:scale(.93)}
.ghost{background:var(--surface);border:1px solid var(--line);border-radius:12px;
  padding:11px 16px;font-size:14px;color:var(--ink)}
.ghost.sm{padding:7px 12px;font-size:12.5px}
.scanmsg{text-align:center;color:var(--muted);font-size:13px;padding:10px 18px;min-height:22px}

/* -------------------------------------------------------------- result */
.resultbody{padding:14px 16px 20px}
.verdict{border-radius:20px;padding:18px;text-align:center;border:1.5px solid}
.verdict.ewaste{background:linear-gradient(160deg,#241536,#150E20);border-color:var(--purple)}
.verdict.other{background:linear-gradient(160deg,#12291D,#0E1A14);border-color:var(--accent)}
.verdict.unknown{background:var(--surface);border-color:var(--line)}
.vtag{display:inline-block;font-size:11px;letter-spacing:2px;color:var(--muted);
  text-transform:uppercase;margin-bottom:8px}
.vname{font-size:27px;font-weight:800;letter-spacing:.4px}
.verdict.ewaste .vname{color:#D8B4FE}
.verdict.other .vname{color:#86EFAC}
.vsub{font-size:13px;color:var(--muted);margin-top:8px;line-height:1.5}
.confbar{height:6px;border-radius:3px;background:#22301F;margin-top:14px;overflow:hidden}
.confbar i{display:block;height:100%;background:var(--accent)}
.confbar.p i{background:var(--purple)}

.cands{display:flex;flex-wrap:wrap;gap:7px;margin-top:14px}
.cand{border:1px solid var(--line);background:var(--surface);border-radius:999px;
  padding:7px 12px;font-size:12.5px}
.cand.on{background:var(--accent);color:#04140A;font-weight:700;border-color:var(--accent)}
/* the AI's own identification - must be impossible to miss next to the guesses */
.cand.ai{border-color:#A855F7;background:rgba(168,85,247,.14);color:#E9D5FF;font-weight:600}
.cand.ai.on{background:#A855F7;color:#12021C;border-color:#A855F7;font-weight:700}

.card{background:var(--surface);border:1px solid var(--line);border-radius:18px;
  padding:14px;margin-top:12px}
.card h4{margin:0 0 10px;font-size:13px;letter-spacing:1.2px;color:var(--muted);
  text-transform:uppercase}
.rowline{display:flex;justify-content:space-between;gap:10px;padding:7px 0;
  border-top:1px solid var(--line);font-size:14px}
.rowline:first-of-type{border-top:0}
.rowline span:last-child{font-weight:600;text-align:right}
.mut{color:var(--muted)}
.gold{color:var(--gold)} .green{color:var(--accent)} .red{color:var(--red)}
.blue{color:var(--blue)} .purple{color:#D8B4FE}

table.mini{width:100%;border-collapse:collapse;font-size:13px}
table.mini th{text-align:left;color:var(--muted);font-weight:600;font-size:11px;
  text-transform:uppercase;letter-spacing:.6px;padding:6px 4px;border-bottom:1px solid var(--line)}
table.mini td{padding:7px 4px;border-bottom:1px solid #1C2620}
table.mini td.num{text-align:right;font-variant-numeric:tabular-nums}
table.mini tr:last-child td{border-bottom:0}

.bigval{font-size:33px;font-weight:800;color:var(--accent);letter-spacing:.5px}
.bigval small{font-size:14px;color:var(--muted);font-weight:500}
.scale{display:flex;gap:6px;margin-top:12px;flex-wrap:wrap}
.scale button{flex:1;min-width:52px;border:1px solid var(--line);background:var(--surface2);
  border-radius:10px;padding:8px 4px;font-size:12.5px;color:var(--muted)}
.scale button.on{background:var(--purple);color:#fff;border-color:var(--purple);font-weight:700}

.warn{background:#2A1414;border:1px solid #6B1F1F;color:#FCA5A5;border-radius:14px;
  padding:12px;font-size:13.5px;margin-top:12px;line-height:1.5}
.tip{background:#0F1F19;border:1px solid #1E3A34;color:#86EFAC;border-radius:14px;
  padding:12px;font-size:13.5px;margin-top:12px;line-height:1.5}
ul.adv{margin:0;padding-left:18px;font-size:14px;line-height:1.65}
.note{font-size:12.5px;color:var(--muted);line-height:1.6}
.pill{display:inline-block;background:var(--surface2);border:1px solid var(--line);
  border-radius:999px;padding:4px 10px;font-size:11.5px;color:var(--muted);margin:3px 4px 0 0}

.actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}
.primary{background:var(--accent);color:#04140A;border-radius:14px;padding:14px;
  font-weight:700;font-size:14.5px}
.primary:active{opacity:.85}

/* -------------------------------------------------------------- map */
#map{height:calc(100dvh - 190px);min-height:420px;margin:12px 14px;border-radius:18px;
  border:1px solid var(--line);
  /* grid shows through wherever tiles are transparent (open water / offline) */
  background-color:#0E1512;
  background-image:linear-gradient(rgba(34,197,94,.055) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(34,197,94,.055) 1px,transparent 1px);
  background-size:44px 44px;overflow:hidden}
/* basemap is light topographic imagery - invert it into the app's dark theme */
.leaflet-tile-pane .leaflet-tile{
  filter:invert(1) hue-rotate(180deg) brightness(.78) contrast(1.12) saturate(.55)}
.mapfilters{display:flex;gap:7px;overflow-x:auto;padding:0 14px;scrollbar-width:none}
.mapfilters::-webkit-scrollbar{display:none}
.fab{position:fixed;right:calc(50% - 215px + 16px);bottom:calc(96px + var(--safe-b));
  width:56px;height:56px;border-radius:50%;background:var(--accent);color:#04140A;
  font-size:30px;font-weight:700;box-shadow:0 8px 22px rgba(0,0,0,.5);z-index:5}
@media(max-width:519px){.fab{right:16px}}
.leaflet-container{background:#0E1512;font:inherit}
.leaflet-popup-content-wrapper{background:#141A16;color:#E8F0EA;border-radius:14px}
.leaflet-popup-tip{background:#141A16}
.leaflet-popup-content{margin:12px 14px;font-size:13px}
.leaflet-bar a{background:#141A16;color:#E8F0EA;border-color:#26332B}
.pin-icon{border-radius:50%;border:2px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.5)}

/* ------------------------------------------------------------- modal */
.modal{position:fixed;inset:0;background:rgba(0,0,0,.66);z-index:60;display:flex;
  align-items:flex-end;justify-content:center}
.modal[hidden]{display:none}
.sheet{width:100%;max-width:430px;background:var(--surface);border-radius:24px 24px 0 0;
  padding:18px 18px calc(20px + var(--safe-b));border-top:1px solid var(--line)}
.sheet h3{margin-bottom:6px}
.segmented{display:flex;gap:6px;background:var(--surface2);border-radius:12px;
  padding:4px;margin:12px 0}
.seg{flex:1;padding:9px;border-radius:9px;font-size:13px;color:var(--muted)}
.seg.active{background:var(--accent);color:#04140A;font-weight:700}
.sheet label{display:block;font-size:12.5px;color:var(--muted);margin:10px 0 4px}
.sheet input,.sheet select,.sheet textarea{width:100%;background:var(--bg);
  border:1px solid var(--line);border-radius:11px;padding:11px;color:var(--ink);font:inherit}
.sheetbtns{display:flex;gap:10px;margin-top:16px}
.sheetbtns .primary,.sheetbtns .ghost{flex:1}

/* ----------------------------------------------------------- settings */
.settings{padding:4px 18px}
.settings label{display:flex;justify-content:space-between;align-items:center;gap:12px;
  background:var(--surface);border:1px solid var(--line);border-radius:12px;
  padding:11px 13px;margin-bottom:8px;font-size:14px}
.settings input{width:110px;background:var(--bg);border:1px solid var(--line);
  border-radius:9px;padding:8px;color:var(--ink);text-align:right}
.settings .grp{border:1px solid var(--line);border-radius:14px;padding:8px 12px 4px;
  margin-bottom:10px;background:var(--surface)}
.settings .grp h5{margin:0 0 6px;font-size:13px;color:var(--ink)}
.settings label{display:flex;align-items:center;gap:10px;background:var(--surface);
  border:1px solid var(--line);border-radius:12px;padding:9px 12px;margin-bottom:7px;
  font-size:13.5px}
.settings label .nl{flex:1;color:var(--ink)}
.settings label input{width:104px;background:var(--bg);border:1px solid var(--line);
  border-radius:9px;padding:7px 8px;color:var(--ink);text-align:right;font-size:13.5px}
.settings label .unit{width:46px;color:var(--muted);font-size:11.5px;text-align:right}
.settings .grp label{background:var(--surface2);border-color:transparent}
.pickrow{width:100%;background:var(--surface);border:1px solid var(--line);
  border-radius:12px;padding:11px;color:var(--ink);margin-bottom:10px;font-size:14px}
.warnbtn{border-color:#6B1F1F;color:#FCA5A5}
.stat.tappable{cursor:pointer}
.wgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px}
.wgrid label{display:flex;align-items:center;gap:8px;background:var(--surface2);
  border:1px solid var(--line);border-radius:12px;padding:9px 10px;font-size:12px;
  color:var(--muted)}
.wgrid input{width:100%;background:var(--bg);border:1px solid var(--line);
  border-radius:9px;padding:8px;color:var(--ink);font-size:14px;text-align:right}
.wgrid span{font-size:11.5px;color:var(--muted);white-space:nowrap}

/* ------------------------------------------------------------- tabbar */
.tabbar{position:fixed;bottom:0;left:0;right:0;display:grid;grid-template-columns:repeat(4,1fr);
  background:var(--surface);border-top:1px solid var(--line);
  padding-bottom:var(--safe-b);z-index:40}
.tab{display:flex;flex-direction:column;align-items:center;gap:3px;padding:9px 0;
  color:var(--muted);font-size:10.5px}
.tab svg{width:23px;height:23px;fill:none;stroke:currentColor;stroke-width:1.7;
  stroke-linecap:round;stroke-linejoin:round}
.tab.active{color:var(--accent)}

.toast{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(96px + var(--safe-b));
  background:#0F1F19;border:1px solid #1E3A34;color:#86EFAC;padding:12px 18px;
  border-radius:14px;font-size:13.5px;z-index:80;max-width:88vw;text-align:center}
.toast[hidden]{display:none}


/* --- AI observation card --- */
.aiview{border-color:#2A3F55;background:linear-gradient(160deg,#12202E,#0F161C)}
.aidesc{font-size:15px;color:#BAE6FD;line-height:1.45;font-weight:600;margin-bottom:6px}

````


## `static/sw.js`

````javascript
/* Offline shell.
   App code is served NETWORK-FIRST: a cache-first worker pinned an old app.js
   on the phone and silently blocked every later fix from reaching it.
   Icons and vendored libs never change, so those stay cache-first. */
const C = 'ewaste-v2';
const ASSETS = ['/', '/styles.css', '/app.js', '/manifest.json',
                '/icon-192.png', '/icon-512.png',
                '/vendor/leaflet.js', '/vendor/leaflet.css'];

// anything that ships logic or markup must always come from the network first
const FRESH = /\/(app\.js|styles\.css|index\.html)?$/;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(C).then(c => c.addAll(ASSETS)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== C).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

function put(req, resp) {
  const copy = resp.clone();
  caches.open(C).then(k => k.put(req, copy)).catch(() => {});
  return resp;
}

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  if (u.origin !== self.location.origin) return;
  if (u.pathname.startsWith('/api/')) return;   // never cache live data

  if (FRESH.test(u.pathname)) {
    e.respondWith(
      fetch(e.request).then(r => put(e.request, r))
        .catch(() => caches.match(e.request).then(r => r || caches.match('/')))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).then(resp => put(e.request, resp))
      .catch(() => caches.match('/')))
  );
});

self.addEventListener('message', e => { if (e.data === 'skip') self.skipWaiting(); });

````


## `static/manifest.json`

````json
{
  "name": "E-Waste Value Appraiser",
  "short_name": "E-Waste AI",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0B0F0C",
  "theme_color": "#0B0F0C",
  "orientation": "portrait",
  "icons": [
    {"src":"/icon-192.png","sizes":"192x192","type":"image/png","purpose":"any"},
    {"src":"/icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}
  ]
}

````


## `server.py`

````python
"""E-Waste Value Appraiser - FastAPI backend + PWA host."""
import os
import io
import json
import time

from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

from engine import knowledge as K, vision as V, appraisal as A, store as S
from engine.appraisal import IMPACT
from engine import overrides as OV

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")

app = FastAPI(title="E-Waste Value Appraiser", version="1.0")
S.init()

MAX_BYTES = 8 * 1024 * 1024


# ------------------------------------------------------------------ helpers
def _read(upload: UploadFile) -> bytes:
    data = upload.file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image too large (max 8 MB)")
    if not data:
        raise HTTPException(400, "Empty upload")
    # reject non-images up front so a stray PDF/HEIC never reaches the engine
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
    except Exception:                                            # noqa: BLE001
        raise HTTPException(400, "That file is not a readable image (use JPEG or PNG).")
    return data


def _reverse_geocode(lat, lng):
    try:
        import requests
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "jsonv2", "lat": lat, "lon": lng, "zoom": 17},
            headers={"User-Agent": "EWASTE-Value-Appraiser/1.0 (hackathon demo)"},
            timeout=6)
        if r.ok:
            return r.json().get("display_name", "")[:160]
    except Exception:                                            # noqa: BLE001
        pass
    return f"{lat:.4f}, {lng:.4f}"


# --------------------------------------------------------------- catalogue
@app.get("/api/health")
def health():
    return dict(ok=True, ai=V.AI_PROVIDER or "heuristic",
                model=V.current_model() if V.AI_PROVIDER else "",
                key_loaded=bool(V.AI_KEY),
                price_date=K.PRICE_DATE,
                devices=len(K.DEVICES), items=len(K.ITEMS))


@app.get("/api/catalog")
def catalog():
    return dict(items=K.catalog(), costs=K.DEFAULT_COSTS, price_date=K.PRICE_DATE)


@app.get("/api/prices")
def prices():
    return dict(price_date=K.PRICE_DATE, costs=K.DEFAULT_COSTS,
                metals={k: dict(name=v["name"], symbol=v["symbol"],
                                price_inr_per_kg=v["price_inr_per_kg"],
                                recovery=v["recovery"], precious=v["precious"],
                                source=v["source"])
                        for k, v in K.METALS.items()})


# ----------------------------------------------------------------- analyse
@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), record: int = 1):
    data = _read(file)
    t0 = time.time()
    try:
        result = V.analyze(data)
    except HTTPException:
        raise
    except Exception as exc:                                      # noqa: BLE001
        raise HTTPException(400, f"Could not analyse that image: {exc}")

    # auto-appraise the top guess so the result sheet is populated immediately
    cands = result["candidates"]
    if cands:
        top = cands[0]
        item = K.get(top["key"])
        # dispatch on the table the key lives in, not on `kind`: copper cable is
        # general waste but is valued through the mineral-recovery engine
        if top["key"] in K.DEVICES:
            ap = A.electronic_appraisal(top["key"], quantity=1)
        else:
            ap = A.waste_appraisal(top["key"], item["avg_weight_g"])
        # carry the model's own wording onto the first price screen, otherwise
        # the heading shows the generic catalogue name instead of what it saw
        ai_name = (top.get("display") or "").strip()
        if ai_name:
            ap["display_label"] = ai_name[:80]
        result["appraisal"] = ap
        result["guess"] = dict(key=top["key"], label=item["label"], score=top["score"],
                               why=top["why"], kind=item["kind"])
        if record:
            S.add_scan(top["key"], ap.get("display_label") or ap["label"], ap["is_electronic"],
                       result["verdict"]["confidence"], result["verdict"].get("engine"),
                       ap["total_kg"] * 1000, ap.get("gross", 0), ap.get("net", 0),
                       ap["kind"], ap.get("co2_saved_kg", 0.0), ap.get("quantity", 1.0))
    result["elapsed_ms"] = int((time.time() - t0) * 1000)
    return JSONResponse(result)


@app.post("/api/appraise")
async def appraise(payload: dict):
    key = payload.get("key")
    if key not in K.DEVICES and key not in K.ITEMS:
        raise HTTPException(404, f"Unknown item '{key}'")
    ap = A.appraise(key,
                    weight_g=payload.get("weight_g"),
                    quantity=payload.get("quantity", 1),
                    costs=payload.get("costs"),
                    prices=payload.get("prices"),
                    rate=payload.get("rate"))
    # let the caller keep the model's own wording on screen (e.g. "Banana peel")
    # even when the maths runs off a generic profile
    if payload.get("ai_label"):
        ap["display_label"] = str(payload["ai_label"])[:80]
    if payload.get("record"):
        S.add_scan(key, ap["label"], ap["is_electronic"],
                   payload.get("confidence", 0.0), payload.get("engine", "manual"),
                   ap["total_kg"] * 1000, ap.get("gross", 0), ap.get("net", 0),
                   ap["kind"], ap.get("co2_saved_kg", 0.0), ap.get("quantity", 1.0))
    return JSONResponse(ap)


@app.get("/api/history")
def history(limit: int = 30):
    return dict(history=S.history(limit))


# ---------------------------------------------------------------- settings
@app.get("/api/settings")
def get_settings():
    """Everything numeric, with its current effective value."""
    ov = OV.all_overrides()
    # report EFFECTIVE values (defaults already layered with saved overrides) so
    # the settings screen shows what the engine will actually use
    return dict(
        overrides=ov,
        costs=OV.costs(dict(K.DEFAULT_COSTS)),
        processing={k: OV.processing(k, K.PROCESSING.get(k, K.DEFAULT_PROCESSING))
                    for k in K.DEVICES},
        default_processing=K.DEFAULT_PROCESSING,
        metals={k: dict(name=v["name"], symbol=v["symbol"],
                        price=OV.metal_price(k, v["price_inr_per_kg"]),
                        recovery=OV.metal_recovery(k, v["recovery"]),
                        precious=v["precious"],
                        impact=OV.impact(k, IMPACT.get(k, 0.0)),
                        unit=("Rs/g" if v["precious"] else "Rs/kg"))
                for k, v in K.METALS.items()},
        devices={k: dict(label=v["label"],
                         weight_g=OV.device_weight(k, v["avg_weight_g"]),
                         yields=OV.device_yields(k, dict(v["yields"])),
                         is_electronic=v.get("is_electronic", True))
                 for k, v in K.DEVICES.items()},
        items={k: dict(label=v["label"],
                       weight_g=OV.item_weight(k, v["avg_weight_g"]),
                       rate=OV.item_rate(k, v["rate_inr_per_kg"]), bin=v["bin"])
               for k, v in K.ITEMS.items()},
        price_date=K.PRICE_DATE)


@app.post("/api/settings")
async def save_settings(payload: dict):
    return dict(ok=True, overrides=OV.save(payload))


@app.post("/api/settings/reset")
def reset_settings():
    return dict(ok=True, overrides=OV.reset())


# ----------------------------------------------------------------- history
@app.delete("/api/history")
def delete_history():
    return dict(ok=True, removed=S.clear_history())


@app.get("/api/stats")
def stats():
    return S.stats()


# --------------------------------------------------------------------- map
@app.get("/api/map")
def map_data(lat: float = 13.0827, lng: float = 80.2707, radius: float = 30):
    return dict(reports=S.reports(), listings=S.listings(),
                recyclers=S.nearby(lat, lng, radius))


@app.post("/api/report")
async def report(payload: dict):
    try:
        lat = float(payload["lat"]); lng = float(payload["lng"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(400, "lat/lng required")
    rid = S.add_report(lat, lng, _reverse_geocode(lat, lng),
                       payload.get("category", "e-waste"), payload.get("note", ""),
                       payload.get("severity", "medium"))
    return dict(id=rid, ok=True)


@app.post("/api/report/{rid}/upvote")
def upvote(rid: int):
    S.upvote_report(rid)
    return dict(ok=True)


@app.post("/api/listing")
async def listing(payload: dict):
    try:
        lat = float(payload["lat"]); lng = float(payload["lng"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(400, "lat/lng required")
    key = payload.get("item_key", "smartphone")
    item = K.get(key) or K.get("smartphone")
    qty = float(payload.get("qty", 1))
    ap = A.appraise(key, quantity=qty)
    fair = ap.get("net") or ap.get("gross", 0)
    asking = payload.get("asking")
    lid = S.add_listing(lat, lng, _reverse_geocode(lat, lng), key, item["label"],
                        qty, float(asking) if asking else fair,
                        payload.get("note", ""))
    return dict(id=lid, ok=True, suggested_price=round(fair, 2))


# ------------------------------------------------------------------- tiles
# OpenStreetMap serves a REAL tile to browser User-Agents but a 103-byte blank
# 1-bit placeholder to anything else. Fetching tiles server-side with a browser
# UA and caching them means the browser never depends on that policy, and the
# map renders over a plain same-origin URL.
TILE_CACHE = os.path.join(BASE, "tilecache")
os.makedirs(TILE_CACHE, exist_ok=True)
TILE_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
TILE_MAX_FILES = 4000
TILE_SUBDOMAINS = ("a", "b", "c")
# OpenTopoMap serves real tiles to this host; plain OSM hands back a uniform
# placeholder. OSM is kept as a fallback if OpenTopoMap is ever unavailable.
TILE_PROVIDERS = (
    "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
)
_BLANK = {}


def _is_real_tile(data):
    """True when the bytes are map imagery, not a provider stub/placeholder."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        try:
            px = im.get_flattened_data()
        except AttributeError:                    # older Pillow
            px = list(im.getdata())
        return len(set(px)) >= 60
    except Exception:                                            # noqa: BLE001
        return False


def _empty_tile():
    """Transparent 256x256 for genuinely empty areas (open water)."""
    if "empty" not in _BLANK:
        import io as _io
        from PIL import Image as _Image
        im = _Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        buf = _io.BytesIO()
        im.save(buf, "PNG")
        _BLANK["empty"] = buf.getvalue()
    return _BLANK["empty"]


def _blank_tile():
    """Dark 256x256 placeholder so a failed tile looks intentional, not broken."""
    if "png" not in _BLANK:
        import io as _io
        from PIL import Image as _Image
        im = _Image.new("RGB", (256, 256), (14, 21, 18))
        buf = _io.BytesIO()
        im.save(buf, "PNG")
        _BLANK["png"] = buf.getvalue()
    return _BLANK["png"]


@app.get("/tiles/{z}/{x}/{y}.png")
def tiles(z: int, x: int, y: int):
    if not (0 <= z <= 19):
        raise HTTPException(400, "bad zoom")
    n = 1 << z
    if not (0 <= x < n and 0 <= y < n):
        raise HTTPException(400, "bad tile coordinate")
    fp = os.path.join(TILE_CACHE, f"{z}_{x}_{y}.png")
    if os.path.isfile(fp):
        return FileResponse(fp, media_type="image/png",
                            headers={"Cache-Control": "public, max-age=604800"})
    sub = TILE_SUBDOMAINS[(z + x + y) % len(TILE_SUBDOMAINS)]
    for tpl in TILE_PROVIDERS:
        try:
            import requests
            r = requests.get(
                tpl.format(s=sub, z=z, x=x, y=y),
                headers={"User-Agent": TILE_UA,
                         "Referer": "https://www.openstreetmap.org/"},
                timeout=10)
            if r.status_code != 200:
                continue
            data = r.content
            # Tile servers hand datacenter IPs a uniform placeholder. Real map
            # imagery has 250+ distinct colours; the OSM stub has 23.
            if not _is_real_tile(data):
                # genuinely empty tile (open water) - transparent so the grid
                # underneath shows through instead of a jarring grey square
                if len(data) < 1500:
                    return Response(_empty_tile(), media_type="image/png",
                                    headers={"Cache-Control": "public, max-age=604800"})
                continue                      # a stub - try the next provider
            try:
                if len(os.listdir(TILE_CACHE)) < TILE_MAX_FILES:
                    with open(fp, "wb") as fh:
                        fh.write(data)
            except OSError:
                pass
            return Response(data, media_type="image/png",
                            headers={"Cache-Control": "public, max-age=604800"})
        except Exception:                                        # noqa: BLE001
            continue
    return Response(_empty_tile(), media_type="image/png",
                    headers={"Cache-Control": "no-store"})


# ------------------------------------------------------------------ static
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")


@app.get("/manifest.json")
def manifest():
    return FileResponse(os.path.join(STATIC, "manifest.json"),
                        media_type="application/manifest+json")

````


## `engine/knowledge.py`

````python
"""Materials, device and pricing knowledge base for E-Waste Value Appraiser.

All metal prices are Indian market rates captured on 2026-11-07 with the source
recorded. Recovery yields are per tonne of feed and come from published
e-waste / PCB assay literature (UNEP StEP class data); they are stored as
kilograms per tonne so every metal uses one unit.
"""

PRICE_DATE = "2026-11-07"

# ----------------------------------------------------------------- metals
# price_inr_per_kg  | recovery = typical hydrometallurgical / smelting yield
METALS = {
    "gold": dict(name="Gold", symbol="Au", price_inr_per_kg=14_200 * 1000, recovery=0.95,
                 precious=True, source="livemint.com/gold-prices"),
    "silver": dict(name="Silver", symbol="Ag", price_inr_per_kg=184 * 1000, recovery=0.90,
                   precious=True, source="livemint.com/silver-prices"),
    "palladium": dict(name="Palladium", symbol="Pd", price_inr_per_kg=2_950 * 1000, recovery=0.90,
                      precious=True, source="goldbroker.com/charts/palladium-price/inr"),
    "copper": dict(name="Copper", symbol="Cu", price_inr_per_kg=1_350.0, recovery=0.90,
                   precious=False, source="upstox.com/mcx-copper-price"),
    "aluminium": dict(name="Aluminium", symbol="Al", price_inr_per_kg=263.0, recovery=0.90,
                      precious=False, source="metalscost.com"),
    "cobalt": dict(name="Cobalt", symbol="Co", price_inr_per_kg=3_410.0, recovery=0.80,
                   precious=False, source="metalscost.com"),
    "nickel": dict(name="Nickel", symbol="Ni", price_inr_per_kg=1_366.0, recovery=0.85,
                   precious=False, source="metalscost.com"),
    "lithium": dict(name="Lithium", symbol="Li", price_inr_per_kg=1_168.0, recovery=0.65,
                    precious=False, source="metalscost.com"),
    "neodymium": dict(name="Neodymium", symbol="Nd", price_inr_per_kg=11_805.0, recovery=0.70,
                      precious=False, source="metalscost.com"),
    "tin": dict(name="Tin", symbol="Sn", price_inr_per_kg=3_959.0, recovery=0.70,
                precious=False, source="metalscost.com"),
    "lead": dict(name="Lead", symbol="Pb", price_inr_per_kg=160.8, recovery=0.90,
                 precious=False, source="metalscost.com"),
    "zinc": dict(name="Zinc", symbol="Zn", price_inr_per_kg=319.0, recovery=0.80,
                 precious=False, source="metalscost.com"),
    "iron": dict(name="Iron / steel", symbol="Fe", price_inr_per_kg=30.0, recovery=0.95,
                 precious=False, source="Indian scrap market (indicative)"),
}

# default cost model, INR per kg of feed (India defaults, user editable)
DEFAULT_COSTS = dict(collection=25.0, transport=8.0, processing=120.0)

# Processing cost per kg depends on the recovery ROUTE, not just the weight.
# Refining a PCB for precious metals is far costlier per kg than shredding a
# steel appliance for scrap. Indicative Indian-market figures (Rs/kg).
DEFAULT_PROCESSING = 120.0
GENERIC_KEYS = ("ewaste_generic", "waste_generic")

PROCESSING = {
    # precious-metal refining (acid / thermal routes)
    "motherboard": 120.0, "smartphone": 120.0, "laptop": 120.0, "ram": 120.0,
    "cpu": 120.0, "hdd": 120.0, "adapter": 120.0, "remote": 120.0,
    # hydrometallurgical battery recovery
    "liion_battery": 60.0,
    # leaded glass - specialist handling, inherently a net cost
    "crt": 45.0,
    # shredding + ferrous / non-ferrous separation
    "tv_led": 18.0, "appliance": 18.0,
    # stripping / baling
    "copper_wire": 15.0,
}

# ------------------------------------------------------- e-waste profiles
# yields: kg of metal per tonne (1000 kg) of that device
# components: (name, share % of device mass, what it carries)
DEVICES = {
    "motherboard": dict(
        label="Desktop motherboard / PCB", is_electronic=True, avg_weight_g=600,
        yields=dict(gold=0.25, silver=1.0, palladium=0.10, copper=200, aluminium=20,
                    iron=30, tin=10, lead=5, zinc=5),
        components=[("Fibreglass substrate", 55, "Copper tracks, resin"),
                    ("CPU socket / VRM", 8, "Gold, copper"),
                    ("Capacitors", 8, "Aluminium, tantalum"),
                    ("Connectors & slots", 12, "Gold fingers, copper, tin"),
                    ("Solder", 5, "Tin, lead"),
                    ("Chipset / ICs", 12, "Gold, silver, palladium")],
        note="Highest-grade fraction in consumer e-waste."),
    "smartphone": dict(
        label="Smartphone", is_electronic=True, avg_weight_g=180,
        yields=dict(gold=0.30, silver=1.0, palladium=0.10, copper=130, aluminium=40,
                    iron=30, lithium=14, cobalt=28, nickel=10, neodymium=0.3),
        components=[("Main PCB", 25, "Gold, silver, palladium, copper"),
                    ("Li-ion battery", 25, "Lithium, cobalt, nickel, graphite"),
                    ("Display assembly", 20, "Glass, indium, rare earths"),
                    ("Casing", 20, "Aluminium or plastic"),
                    ("Camera & sensors", 5, "Copper, gold, rare earths"),
                    ("Vibration motor / speaker", 5, "Neodymium, copper")],
        note="Per-kg gold content rivals high-grade ore."),
    "laptop": dict(
        label="Laptop / notebook", is_electronic=True, avg_weight_g=2200,
        yields=dict(gold=0.20, silver=0.80, palladium=0.08, copper=150, aluminium=100,
                    iron=200, lithium=10, cobalt=20, nickel=8, neodymium=0.2),
        components=[("Motherboard", 12, "Gold, silver, palladium, copper"),
                    ("Battery pack", 20, "Lithium, cobalt, nickel"),
                    ("Display", 18, "Glass, indium"),
                    ("Storage drive", 8, "Aluminium, neodymium magnet, copper"),
                    ("Casing", 22, "Aluminium / magnesium / plastic"),
                    ("Keyboard & chassis", 12, "Plastic, steel"),
                    ("Cooling / heatsink", 8, "Copper, aluminium")],
        note="Mixed fraction; battery is the value driver."),
    "liion_battery": dict(
        label="Lithium-ion battery", is_electronic=True, avg_weight_g=45,
        yields=dict(lithium=20, cobalt=150, nickel=80, copper=70, aluminium=50, iron=100),
        components=[("Cathode", 30, "Lithium, cobalt, nickel"),
                    ("Anode", 15, "Graphite, copper foil"),
                    ("Current collectors", 12, "Copper, aluminium foil"),
                    ("Electrolyte", 15, "Lithium salts"),
                    ("Casing & safety", 28, "Steel, aluminium, plastics")],
        hazardous=True,
        note="Fire risk if punctured. Never charge a swollen cell."),
    "copper_wire": dict(
        label="Copper cable / wire", is_electronic=False, avg_weight_g=100,
        yields=dict(copper=600),
        components=[("Copper conductor", 60, "Copper"),
                    ("Insulation", 40, "PVC / rubber")],
        note="Stripping the insulation roughly doubles the price.",
        bin="recyclable",
        decomposition="Copper does not degrade; insulation persists 500+ years"),
    "ram": dict(
        label="RAM module / memory stick", is_electronic=True, avg_weight_g=25,
        yields=dict(gold=0.30, silver=0.50, copper=150, tin=20),
        components=[("PCB substrate", 65, "Copper tracks"),
                    ("Gold edge connector", 8, "Gold"),
                    ("Memory ICs", 20, "Gold, silver"),
                    ("Solder & passives", 7, "Tin, copper")],
        note="Edge connectors carry visible gold plating."),
    "cpu": dict(
        label="CPU / processor", is_electronic=True, avg_weight_g=12,
        yields=dict(gold=0.50, silver=1.5, palladium=0.20, copper=100),
        components=[("Silicon die", 10, "Gold, silver, palladium"),
                    ("Package / substrate", 40, "Gold bond wires, copper"),
                    ("Pins / pads", 25, "Gold plating"),
                    ("Heat spreader", 25, "Copper, nickel")],
        note="Richest single component by weight."),
    "hdd": dict(
        label="Hard disk drive", is_electronic=True, avg_weight_g=450,
        yields=dict(aluminium=300, iron=200, copper=20, neodymium=20, silver=0.05,
                    gold=0.10),
        components=[("Aluminium chassis", 45, "Aluminium"),
                    ("Platters", 12, "Aluminium, cobalt alloy"),
                    ("Voice coil magnet", 5, "Neodymium, praseodymium"),
                    ("PCB", 6, "Gold, silver, copper"),
                    ("Motor & steel", 32, "Iron, copper")],
        note="The magnet is one of the best neodymium sources in e-waste."),
    "tv_led": dict(
        label="LED / LCD television", is_electronic=True, avg_weight_g=12000,
        yields=dict(iron=100, copper=20, aluminium=10, silver=0.02, gold=0.01, tin=2),
        components=[("Panel / glass", 45, "Glass, indium, liquid crystal"),
                    ("Steel & stand", 25, "Iron"),
                    ("Driver PCBs", 8, "Copper, gold, silver"),
                    ("Plastic housing", 18, "ABS / PS"),
                    ("Cabling", 4, "Copper")],
        note="Low metal value per kg; handle the panel carefully."),
    "appliance": dict(
        label="Large appliance (washer / fridge)", is_electronic=True, avg_weight_g=60000,
        yields=dict(iron=600, copper=30, aluminium=20),
        components=[("Steel body", 60, "Iron"),
                    ("Motor / compressor", 15, "Copper, iron"),
                    ("Wiring", 5, "Copper"),
                    ("Plastics", 20, "PP / ABS")],
        note="Value is almost entirely bulk steel."),
    "crt": dict(
        label="CRT monitor / old TV", is_electronic=True, avg_weight_g=20000,
        yields=dict(iron=50, copper=20, lead=20, aluminium=10),
        components=[("Leaded glass funnel", 45, "Lead, glass"),
                    ("Copper yoke & wiring", 10, "Copper"),
                    ("Steel frame", 25, "Iron"),
                    ("Electronics", 10, "Copper, tin, gold trace"),
                    ("Plastics", 10, "ABS")],
        hazardous=True,
        note="Contains leaded glass. Do not break the tube."),
    "adapter": dict(
        label="Power adapter / charger", is_electronic=True, avg_weight_g=120,
        yields=dict(copper=200, iron=50, gold=0.05, aluminium=20),
        components=[("Transformer winding", 35, "Copper"),
                    ("PCB", 20, "Copper, gold, tin"),
                    ("Plastic shell", 35, "ABS / PC"),
                    ("Cable", 10, "Copper")],
        note="Copper winding is the main value."),
    # Fallback profile: used when the vision model names something that is not in
    # the catalogue. Deliberately conservative - a mixed small-electronics assay.
    # Hidden from the model's catalogue list so it never short-circuits a specific ID.
    "ewaste_generic": dict(
        label="Mixed electronic item", is_electronic=True, avg_weight_g=250,
        yields=dict(gold=0.15, silver=0.6, palladium=0.05, copper=90,
                    aluminium=50, iron=90, tin=8, nickel=3),
        components=[("Circuit board", 30, "Gold, silver, palladium, copper"),
                    ("Wiring & motors", 25, "Copper, iron"),
                    ("Casing", 30, "Plastic or aluminium"),
                    ("Other", 15, "Mixed")],
        note="Generic mixed-electronics estimate - pick a specific item if you can."),
    "remote": dict(
        label="TV remote control", is_electronic=True, avg_weight_g=90,
        yields=dict(iron=30, copper=20, zinc=10),
        components=[("Plastic shell", 55, "ABS"),
                    ("PCB", 15, "Copper, tin, silver"),
                    ("Contacts & springs", 20, "Iron, copper"),
                    ("Battery contacts", 10, "Zinc, nickel")],
        note="Low value; recycle rather than bin."),
}

# ------------------------------------------------------------ general waste
# bin: wet | dry | recyclable | hazardous
ITEMS = {
    # Fallback profile for non-electronic items the catalogue does not cover.
    "waste_generic": dict(
        label="Other general waste", is_electronic=False, avg_weight_g=100,
        bin="dry", decomposition="Varies by material", rate_inr_per_kg=8.0,
        materials=[("Mixed material", 100, True, "Depends on composition")]),
    "pet_bottle": dict(
        label="PET water bottle", is_electronic=False, avg_weight_g=25,
        bin="recyclable", decomposition="~450 years", rate_inr_per_kg=25.0,
        materials=[("PET plastic", 92, True, "Polyester fibre / new flakes"),
                   ("HDPE cap", 5, True, "New caps / crates"),
                   ("Label & adhesive", 3, False, "Residue")]),
    "hdpe_bottle": dict(
        label="HDPE bottle (milk / detergent)", is_electronic=False, avg_weight_g=40,
        bin="recyclable", decomposition="~100+ years", rate_inr_per_kg=40.0,
        materials=[("HDPE plastic", 100, True, "Pipes, crates, new bottles")]),
    "alu_can": dict(
        label="Aluminium drink can", is_electronic=False, avg_weight_g=15,
        bin="recyclable", decomposition="~200 years", rate_inr_per_kg=150.0,
        materials=[("Aluminium", 100, True, "New cans - 95% less energy")]),
    "tin_can": dict(
        label="Steel / tin food can", is_electronic=False, avg_weight_g=50,
        bin="recyclable", decomposition="~50 years", rate_inr_per_kg=25.0,
        materials=[("Steel", 96, True, "New steel"),
                   ("Tin coating", 2, True, "Recovered tin"),
                   ("Label", 2, False, "Residue")]),
    "cardboard": dict(
        label="Cardboard box", is_electronic=False, avg_weight_g=200,
        bin="recyclable", decomposition="~2 months", rate_inr_per_kg=12.0,
        materials=[("Paper fibre", 94, True, "New cartons"),
                   ("Adhesive / tape", 6, False, "Residue")]),
    "newspaper": dict(
        label="Newspaper / paper", is_electronic=False, avg_weight_g=150,
        bin="recyclable", decomposition="~6 weeks", rate_inr_per_kg=15.0,
        materials=[("Paper fibre", 100, True, "Recycled paper")]),
    "glass_bottle": dict(
        label="Glass bottle", is_electronic=False, avg_weight_g=300,
        bin="recyclable", decomposition="~1 million years", rate_inr_per_kg=5.0,
        materials=[("Soda-lime glass", 100, True, "New glass containers")]),
    "fruit_peel": dict(
        label="Fruit / vegetable peel", is_electronic=False, avg_weight_g=120,
        bin="wet", decomposition="2-5 weeks", rate_inr_per_kg=0.0,
        materials=[("Organic matter", 100, True, "Compost / biogas")]),
    "food_scraps": dict(
        label="Cooked food waste", is_electronic=False, avg_weight_g=150,
        bin="wet", decomposition="1-2 weeks", rate_inr_per_kg=0.0,
        materials=[("Organic matter", 100, True, "Compost / biogas")]),
    "garden_waste": dict(
        label="Leaves / garden waste", is_electronic=False, avg_weight_g=300,
        bin="wet", decomposition="~6 months", rate_inr_per_kg=0.0,
        materials=[("Organic matter", 100, True, "Compost / mulch")]),
    "plastic_bag": dict(
        label="Plastic carry bag (LDPE)", is_electronic=False, avg_weight_g=8,
        bin="dry", decomposition="~500+ years", rate_inr_per_kg=20.0,
        materials=[("LDPE film", 100, True, "Carry bags, bin liners")]),
    "multilayer_pouch": dict(
        label="Multilayer snack / milk pouch", is_electronic=False, avg_weight_g=6,
        bin="dry", decomposition="~500+ years", rate_inr_per_kg=10.0,
        materials=[("PET film", 30, False, "Hard to separate"),
                   ("Polyethylene", 55, False, "Hard to separate"),
                   ("Aluminium foil", 15, True, "Recoverable after delamination")],
        note="Multi-layer laminate - most kerbside programs reject it."),
    "tetrapak": dict(
        label="Tetra Pak carton", is_electronic=False, avg_weight_g=25,
        bin="dry", decomposition="~100 years", rate_inr_per_kg=8.0,
        materials=[("Paper fibre", 70, True, "Recycled board"),
                   ("Polyethylene", 25, True, "Plastic pellets"),
                   ("Aluminium foil", 5, True, "Aluminium")]),
    "thermocol": dict(
        label="Thermocol / EPS foam", is_electronic=False, avg_weight_g=10,
        bin="dry", decomposition="~500+ years", rate_inr_per_kg=15.0,
        materials=[("Expanded polystyrene", 100, True, "Compacted EPS blocks")]),
    "paper_cup": dict(
        label="Paper cup (laminated)", is_electronic=False, avg_weight_g=10,
        bin="dry", decomposition="~100 years", rate_inr_per_kg=8.0,
        materials=[("Paper fibre", 88, True, "Recycled board"),
                   ("PE lining", 12, False, "Residue")]),
    "brass": dict(
        label="Brass fitting / tap", is_electronic=False, avg_weight_g=80,
        bin="recyclable", decomposition="Does not degrade", rate_inr_per_kg=450.0,
        materials=[("Copper", 60, True, "New brass"),
                   ("Zinc", 38, True, "New brass"),
                   ("Other", 2, False, "Residue")]),
    "tyre": dict(
        label="Rubber tyre", is_electronic=False, avg_weight_g=9000,
        bin="dry", decomposition="~2000 years", rate_inr_per_kg=10.0,
        materials=[("Rubber", 70, True, "Crumb rubber"),
                   ("Steel belt", 20, True, "Scrap steel"),
                   ("Textile", 10, False, "Residue")]),
    "paint_tin": dict(
        label="Paint / chemical tin", is_electronic=False, avg_weight_g=500,
        bin="hazardous", decomposition="Does not degrade", rate_inr_per_kg=0.0,
        materials=[("Steel", 60, True, "Recycled steel if cleaned"),
                   ("Paint residue", 40, False, "Hazardous waste")],
        hazardous=True,
        note="Do not puncture or burn. Hand to an authorised collector."),
    "cfl_tubelight": dict(
        label="CFL / tube light", is_electronic=False, avg_weight_g=120,
        bin="hazardous", decomposition="Does not degrade", rate_inr_per_kg=0.0,
        materials=[("Glass", 70, False, "Mercury contaminated"),
                   ("Mercury vapour", 1, False, "Hazardous"),
                   ("Metal & phosphor", 29, True, "Recoverable")],
        hazardous=True,
        note="Contains mercury. Never break it indoors."),
    "medical_waste": dict(
        label="Medical waste / syringe", is_electronic=False, avg_weight_g=15,
        bin="hazardous", decomposition="Does not degrade", rate_inr_per_kg=0.0,
        materials=[("Plastic", 70, False, "Infectious waste"),
                   ("Steel needle", 20, False, "Sharps"),
                   ("Biological", 10, False, "Infectious waste")],
        hazardous=True,
        note="Biohazard. Use a sharps box and authorised disposal only."),
}


def catalog():
    """Flat, searchable catalog of everything the app knows."""
    out = []
    for key, d in DEVICES.items():
        out.append(dict(key=key, label=d["label"],
                        kind=("e-waste" if d.get("is_electronic", True) else "metal"),
                        is_electronic=d["is_electronic"], avg_weight_g=d["avg_weight_g"],
                        hazardous=d.get("hazardous", False)))
    for key, d in ITEMS.items():
        out.append(dict(key=key, label=d["label"], kind="waste",
                        is_electronic=False, avg_weight_g=d["avg_weight_g"],
                        hazardous=d.get("hazardous", False)))
    return sorted(out, key=lambda x: (not x["is_electronic"], x["label"]))


def get(key):
    if key in DEVICES:
        d = dict(DEVICES[key]); d["key"] = key
        d["kind"] = "e-waste" if d.get("is_electronic", True) else "metal"
        return d
    if key in ITEMS:
        d = dict(ITEMS[key]); d["kind"] = "waste"; d["key"] = key; return d
    return None

````


## `engine/vision.py`

````python
"""Image analysis and classification.

Two modes:
  * heuristic  - feature extraction from the pixels (works with no API key)
  * ai         - Gemini / OpenAI vision when an API key is configured

Both return the same shape so the app behaves identically.
"""
import io
import os
import json
import base64

import numpy as np
from PIL import Image

from . import knowledge as K

AI_PROVIDER = os.environ.get("AI_PROVIDER", "").lower()   # "gemini" | "openai"
AI_KEY = os.environ.get("AI_API_KEY", "")
# Prefer a file over an env var so the secret never shows up in `ps` output.
_KEY_FILE = os.environ.get("AI_API_KEY_FILE",
                           os.path.join(os.path.dirname(os.path.dirname(
                               os.path.abspath(__file__))), ".aikey"))
if not AI_KEY:
    try:
        with open(_KEY_FILE) as _fh:
            AI_KEY = _fh.read().strip()
    except OSError:
        pass

# Models get retired (gemini-2.0-flash is gone as of 2026). Try an alias that
# tracks the current release first, then concrete fallbacks, then allow override.
# Ordered by measured latency on a real image request (2026-11):
#   gemini-flash-lite-latest  0.9s  correct
#   gemini-3.5-flash-lite     1.2s  correct
#   gemini-3.5-flash          2.8s  correct
#   gemini-3.6-flash          3.2s  correct
# Retired / unreliable, kept out of the chain on purpose:
#   gemini-2.0-flash, gemini-2.5-flash  -> 404 no longer available
#   gemini-3.7-flash, gemini-3.8-flash  -> 503 high demand
#   gemini-flash-latest                 -> hangs (>90s)
GEMINI_MODELS = [
    m for m in [os.environ.get("GEMINI_MODEL", ""),
                "gemini-flash-lite-latest", "gemini-3.5-flash-lite",
                "gemini-3.5-flash", "gemini-3.6-flash"] if m
]
_working_model = None


def current_model():
    """Which model the AI path actually settled on (empty until one succeeds)."""
    return _working_model or (GEMINI_MODELS[0] if GEMINI_MODELS else "")


# ------------------------------------------------------------ feature math
def _hsv_stats(img):
    hsv = np.asarray(img.convert("HSV"), dtype=np.float32)
    h = hsv[..., 0] * 360.0 / 255.0
    s = hsv[..., 1] / 255.0
    v = hsv[..., 2] / 255.0
    return h, s, v


def _mask_frac(mask):
    return float(mask.mean()) if mask.size else 0.0


def _edge_density(gray):
    gx = np.abs(np.diff(gray, axis=1)).mean() if gray.shape[1] > 1 else 0.0
    gy = np.abs(np.diff(gray, axis=0)).mean() if gray.shape[0] > 1 else 0.0
    return float((gx + gy) / 2.0 / 255.0)


def extract_features(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((320, 320))
    rgb = np.asarray(img, dtype=np.float32) / 255.0
    gray = np.asarray(img.convert("L"), dtype=np.float32) / 255.0
    h, s, v = _hsv_stats(img)

    def band(lo, hi, smin=0.0, smax=1.0, vmin=0.0, vmax=1.0):
        m = (h >= lo) & (h <= hi) & (s >= smin) & (s <= smax) & (v >= vmin) & (v <= vmax)
        return float(m.mean())

    f = dict(
        width=img.width, height=img.height,
        brightness=float(gray.mean()),
        contrast=float(gray.std()),
        saturation=float(s.mean()),
        edge=_edge_density(gray),
        # bands tuned against measured samples:
        #   PCB solder mask  hue 141, sat .78, val .35
        #   leaf green       hue 113, sat .62, val .51
        #   copper           hue  25, sat .84, val .72
        #   cardboard        hue  31, sat .60, val .69
        pcb_green=band(128, 178, 0.40, 1.0, 0.10, 0.62),
        copper=band(4, 36, 0.68, 1.0, 0.25, 1.0),
        gold_tan=band(36, 62, 0.30, 1.0, 0.25, 0.95),
        metal_gray=float(((s < 0.16) & (v > 0.22) & (v < 0.88)).mean()),
        white_pale=float(((v > 0.86) & (s < 0.14)).mean()),
        brown_organic=band(12, 52, 0.18, 0.68, 0.18, 0.88),
        yellow_fruit=band(45, 70, 0.35, 1.0, 0.45, 1.0),
        green_plant=band(58, 128, 0.22, 1.0, 0.12, 0.95),
        blue_cool=band(180, 250, 0.15, 1.0, 0.20, 1.0),
        dark=float((v < 0.25).mean()),
    )
    f["aspect"] = round(img.width / max(img.height, 1), 3)
    return f


# ------------------------------------------------------------- heuristic
def classify_heuristic(features):
    """Return ordered candidate list. Each: key, kind, is_electronic, score, why."""
    c = []

    def add(key, kind, is_el, score, why):
        if score > 0.02:
            c.append(dict(key=key, kind=kind, is_electronic=is_el,
                          score=round(min(score, 0.97), 3), why=why))

    f = features
    pcb, gray, edge = f["pcb_green"], f["metal_gray"], f["edge"]
    cu, tan = f["copper"], f["gold_tan"]
    brown, yel, plant = f["brown_organic"], f["yellow_fruit"], f["green_plant"]
    pale, dark, bright = f["white_pale"], f["dark"], f["brightness"]
    blue, sat, aspect = f["blue_cool"], f["saturation"], f["aspect"]
    detail = f["contrast"]          # robust proxy: 0.03 flat, 0.11 dense PCB

    # ---- electronic signals -------------------------------------------
    # calibrated on measured samples (see extract_features band comments)
    if pcb > 0.10:
        add("motherboard", "e-waste", True, 0.60 + pcb * 0.9 + detail * 1.5,
            f"Circuit-board green over {pcb*100:.0f}% of the frame with dense surface detail")
    elif pcb > 0.03:
        add("motherboard", "e-waste", True, 0.40 + pcb * 3.0,
            f"Some circuit-board green detected ({pcb*100:.0f}%)")

    if pcb > 0.05 and aspect < 0.70:
        add("ram", "e-waste", True, 0.34 + pcb * 1.8,
            "Narrow green board - consistent with a memory module")

    # dark body + glowing panel = screen device; aspect separates the two
    if dark > 0.35 and blue > 0.12:
        if aspect < 0.85:
            add("smartphone", "e-waste", True, 0.48 + dark * 0.5 + blue * 0.6,
                "Dark portrait slab with a lit display - a phone")
        else:
            add("laptop", "e-waste", True, 0.46 + dark * 0.5 + blue * 0.5,
                "Dark body with a wide lit display panel")
    elif dark > 0.30 and gray > 0.15:
        add("appliance", "e-waste", True, 0.30 + gray * 0.9 + dark * 0.4,
            "Large dark metallic body")

    # Dark + desaturated is ambiguous between a powered-off device and insulated
    # cable. Bias toward e-waste: misrouting a phone to general waste is worse
    # than the reverse, and the user can always correct from the candidate list.
    if dark > 0.55 and sat < 0.30 and blue < 0.12:
        if aspect >= 1.0:
            add("laptop", "e-waste", True, 0.38 + dark * 0.15,
                "Dark uniform body with no lit panel - a powered-off device")
        else:
            add("smartphone", "e-waste", True, 0.38 + dark * 0.15,
                "Dark portrait slab, screen off")
    # cable only when the form is genuinely elongated - a coil has no colour signal
    if dark > 0.72 and sat < 0.20 and blue < 0.10 and aspect >= 1.5:
        add("copper_wire", "waste", False, 0.34 + dark * 0.3,
            "Long dark insulated form - cable or wire")

    if cu > 0.20:
        add("copper_wire", "waste", False, 0.46 + cu * 1.2,
            f"Strong copper tone ({cu*100:.0f}% of pixels)")
    if tan > 0.15 and detail > 0.05:
        add("cpu", "e-waste", True, 0.34 + tan * 1.4,
            "Gold-plated contacts and chip package tones")
    if tan > 0.12 and cu > 0.08:
        add("brass", "waste", False, 0.30 + tan * 1.2, "Brass / copper alloy colour")

    if gray > 0.25 and bright > 0.45 and detail < 0.10:
        add("alu_can", "waste", False, 0.34 + gray * 0.9,
            "Smooth bright metal - aluminium or steel")

    # ---- non-electronic signals ---------------------------------------
    if yel > 0.22 and sat > 0.35:
        add("fruit_peel", "waste", False, 0.45 + yel * 1.1,
            "Dominant fruit-yellow tone, little structural detail")
    if plant > 0.25 and plant > pcb * 2:
        add("garden_waste", "waste", False, 0.44 + plant * 1.0,
            "Leaf-green plant matter")
    # cardboard is lighter (brightness ~.52) than cooked food (~.37) at similar hue
    if brown > 0.30 and sat < 0.68 and bright > 0.42:
        add("cardboard", "waste", False, 0.44 + brown * 0.8,
            "Brown fibrous surface - cardboard or paper")
    if brown > 0.25 and bright <= 0.45 and plant < 0.10:
        add("food_scraps", "waste", False, 0.30 + brown * 0.5, "Mixed organic tones")
    if pale > 0.40 and sat < 0.25:
        add("newspaper", "waste", False, 0.34 + pale * 0.6, "Light, low-saturation sheet")
    if pale > 0.55 and bright > 0.80:
        add("thermocol", "waste", False, 0.30 + pale * 0.5, "Very bright, textureless")
    if blue > 0.20 and bright > 0.45:
        add("pet_bottle", "waste", False, 0.28 + blue * 0.8,
            "Clear / blue-tinted plastic")
    if blue > 0.15 and pale > 0.20:
        add("glass_bottle", "waste", False, 0.24 + blue * 0.7,
            "Glassy transparent surface")

    c.sort(key=lambda x: -x["score"])
    return c[:4]


def verdict_from_candidates(cands):
    """Turn ranked candidates into an e-waste / non-e-waste verdict."""
    if not cands:
        return dict(is_electronic=None, confidence=0.0, stream="unknown",
                    message="Couldn't recognise this. Pick the item manually or retake with better light.")
    top = cands[0]
    el = sum(c["score"] for c in cands if c["is_electronic"])
    non = sum(c["score"] for c in cands if not c["is_electronic"])
    total = el + non or 1.0
    conf = float(el / total)
    gap = top["score"] - (cands[1]["score"] if len(cands) > 1 else 0.0)

    if top["is_electronic"] and conf > 0.5:
        stream, msg = "e-waste", "Electronic waste - deep mineral appraisal available."
    elif not top["is_electronic"] and conf < 0.5:
        stream, msg = "other", "Not electronic - general waste stream."
    elif top["is_electronic"]:
        stream, msg = "e-waste", "Probably electronic, but the signal is weak. Confirm below."
    else:
        stream, msg = "other", "Probably general waste. Confirm below."

    if top["score"] < 0.30 or gap < 0.05:
        msg += " Low confidence - please confirm the item."

    # conf is the share of evidence backing the *stream*, so it saturates at 0/1
    # on flat synthetic colours. Clamp so the UI never claims absolute certainty.
    conf = min(max(conf, 0.03), 0.97)
    return dict(is_electronic=bool(top["is_electronic"]), confidence=round(conf, 3),
                stream=stream, message=msg, top_key=top["key"])


# ------------------------------------------------------------------- AI
_STOP = {"a", "an", "the", "of", "with", "and", "or", "in", "on", "is", "this",
         "that", "it", "some", "image", "photo", "picture", "object", "item",
         "appears", "shows", "showing", "looks", "like", "very", "single"}


def _words(text):
    return {w for w in "".join(c if c.isalnum() else " "
                               for c in (text or "").lower()).split()
            if len(w) > 2 and w not in _STOP}


def fuzzy_key(label, description, allowed):
    """Best catalogue key for a free-text description, or None.

    The model often names things the catalogue spells differently ("banana peel"
    vs "Fruit / vegetable peel"). Token overlap recovers those instead of
    discarding a correct identification.
    """
    query = _words(f"{label} {description}")
    if not query:
        return None
    best, best_score = None, 0.0
    for key in allowed:
        item = K.get(key)
        if not item:
            continue
        target = _words(f"{item['label']} {key.replace('_', ' ')}")
        if not target:
            continue
        overlap = len(query & target)
        # normalise by the smaller side so "peel" vs "fruit vegetable peel" scores well
        score = overlap / min(len(query), len(target))
        if score > best_score:
            best, best_score = key, score
    return best if best_score >= 0.34 else None


def allowed_keys():
    """Catalogue keys offered to the model - generics are hidden on purpose."""
    return sorted(set(list(K.DEVICES) + list(K.ITEMS)) - set(K.GENERIC_KEYS))


def classify_with_ai(image_bytes, features):
    """Optional real vision call. Returns None if no key is configured."""
    if not AI_KEY or AI_PROVIDER not in ("gemini", "openai"):
        return None
    allowed = allowed_keys()
    # Send key WITH its human label - bare keys like "fruit_peel" invite bad guesses
    catalog = ", ".join(f"{k} ({K.get(k)['label']})" for k in allowed)
    prompt = (
        "You analyse waste for a recycling app. Study the image, then answer.\n\n"
        "1. What exactly is this object? Be specific and plain, max 12 words.\n"
        "2. What materials can you actually SEE? Max 8 words, comma separated.\n"
        "3. Is it ELECTRONIC WASTE? Answer true only if it contains a circuit board, "
        "battery, chip, motor, display, transformer or electrical wiring. Otherwise false.\n"
        "4. Pick the closest key from this catalogue. If nothing is a genuinely good "
        "match, use null - do NOT guess something unrelated.\n"
        "Catalogue: " + catalog + "\n\n"
        "Return ONLY JSON:\n"
        "{\"description\": \"what you see, max 12 words\",\n"
        " \"materials\": \"comma separated, max 8 words\",\n"
        " \"key\": \"best catalogue key or null\",\n"
        " \"is_electronic\": true/false,\n"
        " \"confidence\": 0-1,\n"
        " \"label\": \"short human name\",\n"
        " \"reason\": \"one short sentence\"}"
    )
    b64 = base64.b64encode(image_bytes).decode()
    try:
        import requests
        if AI_PROVIDER == "gemini":
            body = {"contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}}]}],
                "generationConfig": {"responseMimeType": "application/json"}}
            # key in a header, not the URL, so it stays out of access logs
            head = {"x-goog-api-key": AI_KEY}
            if _working_model:
                models = [_working_model]
            else:
                models = GEMINI_MODELS
            last = ""
            for model in models:
                url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                       f"{model}:generateContent")
                r = requests.post(url, json=body, headers=head, timeout=25)
                if r.ok:
                    globals()["_working_model"] = model
                    txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    break
                last = f"{model}: HTTP {r.status_code} {r.text[:160]}"
            else:
                raise RuntimeError("no usable Gemini model - " + last)
        else:
            url = "https://api.openai.com/v1/chat/completions"
            head = {"Authorization": f"Bearer {AI_KEY}"}
            body = {"model": "gpt-4o-mini", "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]}
            r = requests.post(url, json=body, headers=head, timeout=45)
            txt = r.json()["choices"][0]["message"]["content"]
        data = json.loads(txt)
        # a null key is a valid, useful answer - it means "nothing in your list fits"
        data["_key_matched"] = data.get("key") in allowed
        return data
    except Exception as exc:                                   # noqa: BLE001
        return {"error": str(exc)[:200]}
    return None


def analyze(image_bytes):
    """Full first-pass analysis: features -> verdict -> candidates."""
    features = extract_features(image_bytes)
    cands = classify_heuristic(features)
    ai = classify_with_ai(image_bytes, features)

    ai_view = None      # what the model said, kept for display either way
    if ai and not ai.get("error") and (ai.get("key") or ai.get("description")):
        ai_view = dict(description=ai.get("description", ""),
                       materials=ai.get("materials", ""),
                       label=ai.get("label", ""),
                       reason=ai.get("reason", ""),
                       key=ai.get("key"),
                       matched=bool(ai.get("_key_matched")))
        # Resolve the model's answer to something the user can actually select:
        #   exact catalogue key -> fuzzy match on its wording -> generic profile
        key = ai.get("key") if ai.get("_key_matched") else None
        how = "exact"
        if not key:
            key = fuzzy_key(ai.get("label", ""), ai.get("description", ""),
                            allowed_keys())
            how = "fuzzy" if key else "generic"
        if not key:
            key = "ewaste_generic" if ai.get("is_electronic") else "waste_generic"
        item = K.get(key)
        # the model's own name for the object, so a generic profile still reads
        # "Banana peel" on screen instead of "Other general waste"
        ai_name = (ai.get("label") or ai.get("description")
                   or item.get("label", key)).strip()
        cands.insert(0, dict(
            key=key, kind=item["kind"], is_electronic=item["is_electronic"],
            score=float(ai.get("confidence", 0.9)),
            why=ai.get("reason", "Identified by vision model"),
            source="ai", display=ai_name, match=how))
        seen, ded = set(), []
        for c in cands:
            if c["key"] not in seen:
                seen.add(c["key"]); ded.append(c)
        cands = ded[:4]
        ai_view.update(chosen_key=key, match=how, name=ai_name)

        verdict = verdict_from_candidates(cands)
        verdict["engine"] = f"ai:{AI_PROVIDER}"
        if how == "exact":
            verdict["message"] = f"Identified by AI vision: {ai_name}."
        elif how == "fuzzy":
            verdict["message"] = (f"AI identified this as {ai_name} - matched to "
                                  f"{item['label']} for valuation.")
        else:
            verdict["message"] = (f"AI sees: {ai_name}. Not in the catalogue, so "
                                  "a generic profile is used - refine below.")
    else:
        verdict = verdict_from_candidates(cands)
        verdict["engine"] = "heuristic"

    for c in cands:
        c.setdefault("source", "heuristic")
        item = K.get(c["key"])
        c["label"] = item["label"] if item else c["key"]

    return dict(features=features, candidates=cands, verdict=verdict,
                ai_view=ai_view, ai_error=(ai or {}).get("error"))

````


## `engine/appraisal.py`

````python
"""Pure calculation engine. No I/O - every function is unit-testable."""
from . import knowledge as K
from . import overrides as O

# kg CO2 avoided per kg of material recycled (indicative, published LCA ranges)
IMPACT = {"aluminium": 9.0, "iron": 1.5, "copper": 3.5, "gold": 16.0, "silver": 5.0,
          "palladium": 30.0, "lithium": 2.0, "cobalt": 4.0, "nickel": 5.0,
          "neodymium": 8.0, "tin": 2.0, "lead": 1.0, "zinc": 2.0}
ORGANIC_IMPACT = 0.5


def _r(x, n=2):
    return round(float(x), n)


def electronic_appraisal(key, quantity=1.0, weight_kg=None, costs=None, prices=None):
    """Mineral recovery appraisal for one device / lot / tonne."""
    d = K.DEVICES[key]
    unit_kg = O.device_weight(key, d["avg_weight_g"]) / 1000.0
    total_kg = float(weight_kg) if weight_kg else unit_kg * float(quantity)
    total_kg = max(total_kg, 1e-6)
    override = dict(costs or {})
    # layer: shipped defaults < user's saved settings < this request's payload
    costs = O.costs(dict(K.DEFAULT_COSTS, **override))
    # Processing cost depends on the recovery ROUTE, not just weight: refining a
    # PCB for precious metal is far costlier per kg than shredding a steel fridge.
    # Only apply the route default when the caller hasn't overridden it.
    if "processing" not in override:
        costs["processing"] = O.processing(key, K.PROCESSING.get(key, K.DEFAULT_PROCESSING))

    rows, gross = [], 0.0
    yields = O.device_yields(key, d["yields"])
    for metal, kg_per_t in sorted(yields.items(),
                                  key=lambda kv: -kv[1] * K.METALS[kv[0]]["price_inr_per_kg"]):
        m = K.METALS[metal]
        default_price = O.metal_price(metal, m["price_inr_per_kg"])
        price = float((prices or {}).get(metal, default_price))
        recovery = O.metal_recovery(metal, m["recovery"])
        in_feed = kg_per_t / 1000.0 * total_kg          # kg of metal in this feed
        recovered = in_feed * recovery
        value = recovered * price
        gross += value
        precious = m["precious"]
        rows.append(dict(
            metal=metal, name=m["name"], symbol=m["symbol"], precious=precious,
            yield_per_tonne=_r(kg_per_t, 4 if precious else 2),
            yield_unit="g/t" if precious else "kg/t",
            yield_display=_r(kg_per_t * (1000 if precious else 1), 3 if precious else 2),
            in_feed=_r(in_feed * (1000 if precious else 1), 4 if precious else 4),
            in_feed_unit="g" if precious else "kg",
            recovery=recovery, price=_r(price, 2),
            price_unit="Rs/kg",            # `price` is always per kilogram
            price_display=_r(price / (1000 if precious else 1), 2),
            price_display_unit="Rs/g" if precious else "Rs/kg",
            value=_r(value, 2), source=m["source"]))

    cost_total = sum(costs.values()) * total_kg
    net = gross - cost_total
    scale = 1000.0 / total_kg                              # multiplier to reach 1 tonne

    is_el = bool(d.get("is_electronic", True))
    return dict(
        kind=("e-waste" if is_el else "metal"), is_electronic=is_el,
        key=key, label=d["label"], note=d.get("note", ""),
        hazardous=bool(d.get("hazardous")),
        bin=d.get("bin"), decomposition=d.get("decomposition"),
        unit_weight_g=_r(O.device_weight(key, d["avg_weight_g"]), 2),
        quantity=_r(quantity, 3),
        total_kg=_r(total_kg, 4),
        components=[dict(name=n, share=s, carries=c) for n, s, c in d["components"]],
        minerals=rows,
        gross=_r(gross), costs={k: _r(v * total_kg) for k, v in costs.items()},
        cost_total=_r(cost_total), net=_r(net),
        margin=_r((net / gross * 100) if gross else 0.0, 1),
        per_unit=_r(gross - sum(costs.values()) * unit_kg) if gross else 0.0,
        per_tonne_gross=_r(gross * scale), per_tonne_net=_r(net * scale),
        co2_saved_kg=_r(sum(O.impact(r["metal"], IMPACT.get(r["metal"], 0.0))
                            * (r["in_feed"] / (1000 if r["precious"] else 1))
                            for r in rows), 2),
        price_date=K.PRICE_DATE)


def waste_appraisal(key, weight_g, rate_override=None):
    """General-waste valuation and disposal guidance."""
    d = K.ITEMS[key]
    kg = max(float(weight_g), 0.0) / 1000.0
    rate = float(rate_override if rate_override is not None
                 else O.item_rate(key, d["rate_inr_per_kg"]))
    gross = kg * rate

    mats = []
    for name, share, rec, becomes in d["materials"]:
        mats.append(dict(name=name, share=share, recyclable=rec, becomes=becomes,
                         kg=_r(kg * share / 100.0, 4)))

    organic = d["bin"] == "wet"
    co2 = kg * O.item_rate("_co2_" + ("wet" if organic else "dry"),
                           ORGANIC_IMPACT if organic else 1.2)

    return dict(
        kind="waste", is_electronic=False, key=key, label=d["label"],
        note=d.get("note", ""),
        hazardous=bool(d.get("hazardous")), bin=d["bin"],
        decomposition=d["decomposition"], decomposition_short=d["decomposition"],
        unit_weight_g=O.item_weight(key, d["avg_weight_g"]), total_kg=_r(kg, 4),
        rate=_r(rate, 2), gross=_r(gross, 2), net=_r(gross, 2),
        materials=mats, co2_saved_kg=_r(co2, 2), price_date=K.PRICE_DATE,
        advice=_bin_advice(d["bin"], bool(d.get("hazardous"))))


def _bin_advice(bin_, hazardous):
    if hazardous:
        return ["Do not open, puncture or burn this item.",
                "Keep it out of the household bin.",
                "Hand it to an authorised collector or a hazardous-waste drive."]
    return {
        "wet": ["Goes in the WET / biodegradable bin.",
                "Keep it free of plastic and metal.",
                "Best home outcome: compost it or feed a biogas plant."],
        "dry": ["Goes in the DRY bin.",
                "Rinse off food residue and let it dry first.",
                "Flatten to save collection space."],
        "recyclable": ["Goes in the RECYCLABLE / dry bin.",
                       "Rinse and squash before you bin it.",
                       "Keep it dry - wet recyclables get rejected at sorting."],
    }.get(bin_, ["Follow your local municipal segregation rules."])


def appraise(key, weight_g=None, quantity=1.0, costs=None, prices=None, rate=None):
    if key in K.DEVICES:
        return electronic_appraisal(key, quantity=quantity,
                                    weight_kg=(weight_g / 1000.0 if weight_g else None),
                                    costs=costs, prices=prices)
    d = K.ITEMS.get(key)
    w = weight_g if weight_g is not None else (O.item_weight(key, d["avg_weight_g"]) if d else 100.0)
    return waste_appraisal(key, w, rate)

````


## `engine/overrides.py`

````python
"""User-editable numeric overrides.

Every number the app displays has a default baked into knowledge.py. Anything the
user changes in Settings is stored here as JSON and layered on top at read time,
so edits survive restarts and the defaults are always one "reset" away.
"""
import json
import os
import threading

PATH = os.environ.get("EWASTE_OVERRIDES", "/home/user/ewaste_app/overrides.json")
_lock = threading.Lock()

# shape of the override document
BLANK = {"costs": {}, "processing": {}, "metals": {},
         "devices": {}, "items": {}, "impact": {}}
_cache = None


def _read():
    global _cache
    if _cache is not None:
        return _cache
    data = json.loads(json.dumps(BLANK))
    try:
        with open(PATH) as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            for k in BLANK:
                if isinstance(loaded.get(k), dict):
                    data[k] = loaded[k]
    except (OSError, ValueError):
        pass
    _cache = data
    return data


def all_overrides():
    with _lock:
        return json.loads(json.dumps(_read()))


def _deep_merge(dst, src):
    """Merge src into dst recursively.

    A shallow update() would drop sibling fields: saving gold's recovery would
    wipe gold's already-edited price, because the UI saves one field at a time.
    """
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def save(data):
    """Merge a partial override document and persist it."""
    global _cache
    with _lock:
        cur = _read()
        for section in BLANK:
            incoming = data.get(section)
            if isinstance(incoming, dict):
                _deep_merge(cur.setdefault(section, {}), incoming)
        with open(PATH, "w") as fh:
            json.dump(cur, fh, indent=2, sort_keys=True)
        _cache = cur
        return json.loads(json.dumps(cur))


def reset():
    """Drop every override and go back to the shipped defaults."""
    global _cache
    with _lock:
        _cache = json.loads(json.dumps(BLANK))
        try:
            os.remove(PATH)
        except OSError:
            pass
        return json.loads(json.dumps(_cache))


def _num(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ------------------------------------------------------------------ getters
def costs(default):
    o = _read()["costs"]
    return {k: _num(o.get(k, v), v) for k, v in default.items()}


def processing(key, default):
    return _num(_read()["processing"].get(key), default)


def metal_price(metal, default):
    return _num(_read()["metals"].get(metal, {}).get("price"), default)


def metal_recovery(metal, default):
    v = _num(_read()["metals"].get(metal, {}).get("recovery"), default)
    return min(max(v, 0.0), 1.0)


def impact(metal, default):
    return _num(_read()["impact"].get(metal), default)


def device_weight(key, default):
    return _num(_read()["devices"].get(key, {}).get("weight_g"), default)


def device_yields(key, default_yields):
    """Default yields overlaid with any per-metal overrides."""
    out = dict(default_yields)
    for metal, val in (_read()["devices"].get(key, {}).get("yields") or {}).items():
        out[metal] = _num(val, out.get(metal, 0.0))
    return out


def item_weight(key, default):
    return _num(_read()["items"].get(key, {}).get("weight_g"), default)


def item_rate(key, default):
    return _num(_read()["items"].get(key, {}).get("rate"), default)

````


## `engine/store.py`

````python
"""SQLite persistence for scans, map reports, listings and recyclers."""
import os
import sqlite3
import time
import math

DB = os.environ.get("EWASTE_DB", "/home/user/ewaste_app/data.db")

# Chennai-area seed recyclers / authorised e-waste collection points
SEED_RECYCLERS = [
    ("Chennai E-Waste Recyclers", 13.0827, 80.2707, "authorized",
     "Computers, Phones, Batteries", "+91-44-2621-0001"),
    ("Kabadiwala - T. Nagar", 13.0418, 80.2341, "dealer",
     "Paper, Plastic, Metal, E-waste", "+91-98400-11223"),
    ("Adyar Scrap Mart", 13.0067, 80.2570, "dealer",
     "Metal, Appliances, Cables", "+91-98400-33445"),
    ("Anna Nagar E-Waste Point", 13.0850, 80.2100, "authorized",
     "Phones, Laptops, PCBs", "+91-44-2616-7788"),
    ("Velachery Metal & Cable Co.", 12.9815, 80.2180, "dealer",
     "Copper, Aluminium, Brass", "+91-98400-55667"),
    ("Guindy Industrial Recyclers", 13.0100, 80.2120, "recycler",
     "Appliances, Motors, Steel", "+91-44-2235-9900"),
    ("Tambaram E-Waste Drive", 12.9249, 80.1000, "authorized",
     "All electronics", "+91-98400-77889"),
    ("Porur Battery & Metal Recovery", 13.0380, 80.1560, "authorized",
     "Batteries, Inverters", "+91-44-2476-1234"),
]


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS scans(
          id INTEGER PRIMARY KEY, ts REAL, key TEXT, label TEXT,
          is_electronic INTEGER, confidence REAL, engine TEXT,
          weight_g REAL, value REAL, net REAL, verdict TEXT, co2 REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS reports(
          id INTEGER PRIMARY KEY, ts REAL, lat REAL, lng REAL, address TEXT,
          category TEXT, note TEXT, severity TEXT, upvotes INTEGER DEFAULT 0,
          status TEXT DEFAULT 'open');
        CREATE TABLE IF NOT EXISTS listings(
          id INTEGER PRIMARY KEY, ts REAL, lat REAL, lng REAL, address TEXT,
          item_key TEXT, label TEXT, qty REAL, asking REAL, note TEXT,
          status TEXT DEFAULT 'available');
        CREATE TABLE IF NOT EXISTS recyclers(
          id INTEGER PRIMARY KEY, name TEXT, lat REAL, lng REAL, type TEXT,
          accepts TEXT, phone TEXT, verified INTEGER DEFAULT 1);
        """)
        cols = [r[1] for r in c.execute("PRAGMA table_info(scans)")]
        if cols and "co2" not in cols:
            c.execute("ALTER TABLE scans ADD COLUMN co2 REAL DEFAULT 0")
        cols = [r[1] for r in c.execute("PRAGMA table_info(scans)")]
        if cols and "quantity" not in cols:
            c.execute("ALTER TABLE scans ADD COLUMN quantity REAL DEFAULT 1")
        if c.execute("SELECT COUNT(*) FROM recyclers").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO recyclers(name,lat,lng,type,accepts,phone) VALUES(?,?,?,?,?,?)",
                SEED_RECYCLERS)


def add_scan(key, label, is_el, conf, engine, weight_g, value, net, verdict,
             co2=0.0, quantity=1.0):
    with conn() as c:
        cur = c.execute("INSERT INTO scans(ts,key,label,is_electronic,confidence,engine,"
                        "weight_g,value,net,verdict,co2,quantity)"
                        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (time.time(), key, label, int(bool(is_el)), conf, engine,
                         float(weight_g or 0), value, net, verdict,
                         float(co2 or 0), float(quantity or 1)))
        return cur.lastrowid


def clear_history():
    """Wipe saved scans (used by the Settings reset - demo data is not real usage)."""
    with conn() as c:
        n = c.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        c.execute("DELETE FROM scans")
        return n


def stats():
    """Aggregate totals straight from the rows the user actually scanned."""
    with conn() as c:
        r = c.execute("SELECT COUNT(*) n, COALESCE(SUM(weight_g),0) g, "
                      "COALESCE(SUM(value),0) v, COALESCE(SUM(net),0) net, "
                      "COALESCE(SUM(co2),0) co2 FROM scans").fetchone()
        return dict(scans=r["n"], kg=round(r["g"] / 1000.0, 3), value=round(r["v"], 2),
                    net=round(r["net"], 2), co2=round(r["co2"], 2))


def history(limit=30):
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM scans ORDER BY ts DESC LIMIT ?", (limit,))]


def add_report(lat, lng, address, category, note, severity):
    with conn() as c:
        cur = c.execute("INSERT INTO reports(ts,lat,lng,address,category,note,severity)"
                        " VALUES(?,?,?,?,?,?,?)",
                        (time.time(), lat, lng, address, category, note, severity))
        return cur.lastrowid


def reports():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM reports ORDER BY ts DESC")]


def upvote_report(rid):
    with conn() as c:
        c.execute("UPDATE reports SET upvotes = upvotes + 1 WHERE id=?", (rid,))


def add_listing(lat, lng, address, item_key, label, qty, asking, note):
    with conn() as c:
        cur = c.execute("INSERT INTO listings(ts,lat,lng,address,item_key,label,qty,"
                        "asking,note) VALUES(?,?,?,?,?,?,?,?,?)",
                        (time.time(), lat, lng, address, item_key, label, qty, asking, note))
        return cur.lastrowid


def listings():
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM listings WHERE status='available' ORDER BY ts DESC")]


def recyclers():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM recyclers")]


def nearby(lat, lng, radius_km=25):
    out = []
    for r in recyclers():
        d = _haversine(lat, lng, r["lat"], r["lng"])
        if d <= radius_km:
            r = dict(r); r["distance_km"] = round(d, 2); out.append(r)
    return sorted(out, key=lambda x: x["distance_km"])


def _haversine(a1, o1, a2, o2):
    R = 6371.0
    p1, p2 = math.radians(a1), math.radians(a2)
    dp, dl = math.radians(a2 - a1), math.radians(o2 - o1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))

````


## `requirements.txt`

````text
fastapi>=0.110
uvicorn[standard]>=0.27
pillow>=10.0
numpy>=1.26
httpx>=0.27
python-multipart>=0.0.9

````


## `runtime.txt`

````text
python-3.12.4

````


## `Procfile`

````text
web: uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}

````


## `render.yaml`

````yaml
services:
  - type: web
    name: ewaste-appraiser
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn server:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/health
    envVars:
      - key: PYTHON_VERSION
        value: "3.12.4"
      - key: AI_PROVIDER
        value: gemini
      # paste your Gemini key here in the Render dashboard.
      # mark it as a secret - never commit it to git.
      - key: AI_API_KEY
        sync: false
      # without this the AI silently falls back to the offline guess
      - key: PYTHONUNBUFFERED
        value: "1"

````


## `PHONE_URL.txt`

````text
E-Waste Value Appraiser — phone link
====================================

CURRENT URL
  https://e64acc6c6c05ee.lhr.life

Open that on your phone. It is HTTPS, so the camera and GPS will work.

INSTALL AS AN APP (works offline afterwards)
  Android / Chrome : open the URL -> menu -> "Install app" / "Add to Home screen"
  iPhone / Safari  : open the URL -> Share -> "Add to Home Screen"

WHY THE LINK KEEPS CHANGING
  The app runs inside a sandbox that periodically shuts down background
  processes. When that happens the Cloudflare tunnel dies and a NEW random
  URL is issued on restart. There is no way to keep a fixed address from
  inside the sandbox.

  If the link stops working, ask me to re-issue it and I will put a fresh
  one here. It takes about a minute.

FOR A PERMANENT LINK  (recommended - files are ready)
  I have already added the deployment files to this folder:
    Procfile  render.yaml  requirements.txt  runtime.txt  DEPLOY.md
  Deploy free to Render, Railway or Fly.io and you get a FIXED url that
  survives restarts. No more chasing dead links.
  Full step-by-step instructions are in DEPLOY.md (open that file).
  I verified the app boots with no API key and degrades to the offline
  estimate, so a deploy cannot break - it just loses AI naming until you
  set AI_API_KEY in the host's environment settings.

WHAT IS RUNNING
  App server : uvicorn on port 8000, AI_PROVIDER=gemini
  Vision     : gemini flash family (auto-falls-back across models)
  Tunnel     : localhost.run (SSH) -> https://e64acc6c6c05ee.lhr.life
               cloudflared is the automatic fallback if this dies

CHOOSING THE AI'S ANSWER
  After a scan, the AI's identification is the FIRST option in the "Is this
  right?" list, marked with a lightning bolt, using the AI's own wording.

  If the object is not in the catalogue the app still lets you pick it - it
  falls back to a generic profile (mixed electronics / general waste) while
  keeping the AI's name on screen. You can always refine with the dropdown.

  Wording is also fuzzy-matched, so "banana peel" resolves to the catalogue's
  "Fruit / vegetable peel" instead of being thrown away.

IF THE APP LOOKS OLD OR A FIX IS MISSING
  The app installs offline support, which can keep an old copy.
  Chrome/Android: menu -> "Reload" or long-press reload.
  Safari/iOS: swipe down on the page, or Settings -> Safari -> Clear History.
  The offline layer is now set to serve app code from the network first, so a
  normal reload picks up new code. Old caches are cleared automatically.

  The Gemini key lives in /home/user/ewaste_app/.aikey (chmod 600) and is
  never exposed to the browser.

````
