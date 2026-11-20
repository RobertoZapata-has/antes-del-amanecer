const CACHE = 'amanecer-v3';
const CORE = ['./', './index.html', './manifest.json', './cover.jpg', './icon-192.png', './icon-512.png', './village.glb', './layout.json', './sky.jpg',
  'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js',
  'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(CORE.map(u => c.add(u).catch(() => {})))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const local = new URL(req.url).origin === location.origin;
  if (local && (req.mode === 'navigate' || req.url.endsWith('.html') || req.url.endsWith('.json') || req.url.endsWith('.glb'))) {
    // la página: primero red (para recibir actualizaciones), si no hay señal, la guardada
    e.respondWith(fetch(req).then(r => { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); return r; }).catch(() => caches.match(req).then(r => r || caches.match('./index.html'))));
    return;
  }
  // todo lo demás (Three.js, fuentes, imágenes): primero lo guardado
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => {
    if (r.ok || r.type === 'opaque') { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); }
    return r;
  })));
});
