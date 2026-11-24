// 설치 가능한 PWA로 만들기 위한 최소한의 서비스워커입니다.
// 로그인/추천 데이터는 항상 최신이어야 하므로 HTML 페이지와 /api/*는 캐싱하지 않고
// 그대로 네트워크로 보냅니다. css/js/아이콘 같은 정적 파일은 "네트워크 먼저, 실패하면
// 캐시" 방식으로 처리합니다 (캐시 먼저로 하면 배포해서 파일을 고쳐도 브라우저가 옛날
// 버전을 계속 쓰는 문제가 생겨서 이렇게 바꿈).
const CACHE_NAME = "lunchbreak-static-v2";
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
    fetch(event.request)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }
        return res;
      })
      .catch(() => caches.match(event.request))
  );
});
