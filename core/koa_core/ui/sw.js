// Service worker minimo: cachea el shell, red primero para /v1/*.
const CACHE = "koa-shell-v2";
const SHELL = ["/", "/style.css", "/i18n.js", "/app.js", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(SHELL);
    }).catch(function () { /* offline en el primer install: no pasa nada */ })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", function (event) {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/v1/")) {
    event.respondWith(fetch(event.request).catch(function () {
      // "offline" es un código, no un mensaje: app.js decide el texto en el
      // idioma de la UI a partir de body.offline, no de este string.
      return new Response(JSON.stringify({ error: "offline", offline: true }), {
        status: 503, headers: { "Content-Type": "application/json" },
      });
    }));
    return;
  }
  event.respondWith(
    caches.match(event.request).then(function (cached) {
      return cached || fetch(event.request);
    })
  );
});
