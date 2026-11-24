// 설치 가능한 PWA로 만들기 위한 최소한의 서비스워커입니다.
// 로그인/추천 데이터는 항상 최신이어야 하므로 HTML 페이지와 /api/*는 캐싱하지 않고
// 그대로 네트워크로 보냅니다. css/js/아이콘 같은 정적 파일만 캐시해서 재방문을 빠르게 합니다.
const CACHE_NAME = "lunchbreak-static-v1";
const STATIC_ASSETS = [
  "/css/style.css",
  "/js/main.js",
  "/js/map.js",
  "/js/report.js",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return; // 항상 최신 데이터

  event.respondWith(
    caches.match(event.request).then(
      (cached) =>
        cached ||
        fetch(event.request).then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return res;
        })
    )
  );
});
