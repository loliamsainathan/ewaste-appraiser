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
