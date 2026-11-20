const CACHE_NAME = 'physioflex-shell-v1';
const SHELL = ['/static/manifest.webmanifest', '/static/icons/physioflex.svg'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) return;
  if (req.mode === 'navigate') {
    event.respondWith(fetch(req).catch(() => new Response('<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><title>PhysioFlex offline</title><body style="font-family:system-ui;padding:2rem"><h1>PhysioFlex</h1><p>You are offline. Reconnect to access your secure dashboard and clinical data.</p></body></html>', {headers:{'Content-Type':'text/html; charset=utf-8'}})));
    return;
  }
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(caches.match(req).then(cached => cached || fetch(req).then(res => {
      if (res.ok && res.type === 'basic') { const copy = res.clone(); caches.open(CACHE_NAME).then(cache => cache.put(req, copy)); }
      return res;
    })));
  }
});
