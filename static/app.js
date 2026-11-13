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
  // Tiles load straight from the provider in the browser. They used to be
  // proxied through the server, but hosts like Render share an outbound IP and
  // get rate-limited into receiving blank placeholder tiles. A real browser
  // sends a real User-Agent, so it gets the real tile.
  L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    subdomains: 'abc',
    maxZoom: 17,
    crossOrigin: true,
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
