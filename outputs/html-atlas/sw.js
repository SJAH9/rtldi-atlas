const CACHE = 'rtldi-atlas-app-v1';
const SHELL = ['app.html', 'app.css', 'app.js', 'bootstrap.js', 'embedded.css', 'manifest.webmanifest', 'offline.html', 'assets/icon-192.png', 'assets/icon-512.png', 'assets/icon-maskable-512.png', 'assets/icon-180.png', 'assets/maximize.svg', 'assets/minimize.svg', 'assets/menu.svg', 'assets/download.svg'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('rtldi-atlas-app-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  const scope = new URL(self.registration.scope);
  if (event.request.method !== 'GET' || url.origin !== scope.origin || !url.pathname.startsWith(scope.pathname)) return;
  if (!/\.(?:html|css|js|json|webmanifest|svg|png)$/.test(url.pathname)) return;
  const key = new Request(url.origin + url.pathname);
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(event.request);
      if (response.ok) {
        try {
          await cache.put(key, response.clone());
          const keys = await cache.keys();
          if (keys.length > 200) {
            const victim = keys.find(item => !SHELL.some(file => new URL(file, scope).pathname === new URL(item.url).pathname));
            if (victim) await cache.delete(victim);
          }
        } catch { /* Storage limits must not hide a successful network response. */ }
      }
      return response;
    } catch {
      const saved = await cache.match(key);
      if (saved) return saved;
      if (event.request.mode === 'navigate') return cache.match(new URL('offline.html', scope).href);
      return Response.error();
    }
  })());
});
