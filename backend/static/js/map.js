const mapModal = document.getElementById("mapModal");
const mapModalClose = document.getElementById("mapModalClose");
const mapModalTitle = document.getElementById("mapModalTitle");
const mapModalSummary = document.getElementById("mapModalSummary");
const mapContainer = document.getElementById("mapContainer");

let kakaoReadyPromise = null;
let kakaoMap = null;
let routePolyline = null;
let routeMarkers = [];

function loadKakaoSdk() {
  if (kakaoReadyPromise) return kakaoReadyPromise;
  kakaoReadyPromise = fetch("/api/config")
    .then((res) => res.json())
    .then(
      (config) =>
        new Promise((resolve, reject) => {
          if (!config.kakao_js_key) {
            reject(new Error("카카오 지도 키가 설정되지 않았습니다."));
            return;
          }
          const script = document.createElement("script");
          script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${config.kakao_js_key}&autoload=false&libraries=services`;
          script.onload = () => window.kakao.maps.load(resolve);
          script.onerror = () => reject(new Error("카카오 지도 SDK 로드 실패"));
          document.head.appendChild(script);
        })
    );
  return kakaoReadyPromise;
}

function clearRoute() {
  if (routePolyline) routePolyline.setMap(null);
  routeMarkers.forEach((m) => m.setMap(null));
  routePolyline = null;
  routeMarkers = [];
}

async function openRouteMap(restaurant, userLat, userLng) {
  mapModal.classList.remove("hidden");
  mapModalTitle.textContent = `📍 ${restaurant.name}`;
  mapModalSummary.textContent = "경로를 불러오는 중...";

  try {
    await loadKakaoSdk();
  } catch (e) {
    kakaoReadyPromise = null; // 다음 클릭에 다시 시도할 수 있게 캐시된 실패를 지움
    mapModalSummary.textContent = e.message;
    return;
  }

  const kakao = window.kakao;
  if (!kakaoMap) {
    kakaoMap = new kakao.maps.Map(mapContainer, {
      center: new kakao.maps.LatLng(userLat, userLng),
      level: 4,
    });
  } else {
    clearRoute();
    // 모달이 숨겨져 있다가 다시 보일 때 카카오맵이 크기를 잘못 잡는 문제 방지
    setTimeout(() => kakaoMap.relayout(), 0);
  }

  const userPos = new kakao.maps.LatLng(userLat, userLng);
  const destPos = new kakao.maps.LatLng(restaurant.lat, restaurant.lng);

  routeMarkers.push(new kakao.maps.Marker({ map: kakaoMap, position: userPos, title: "내 위치" }));
  routeMarkers.push(new kakao.maps.Marker({ map: kakaoMap, position: destPos, title: restaurant.name }));

  const bounds = new kakao.maps.LatLngBounds();
  bounds.extend(userPos);
  bounds.extend(destPos);
  kakaoMap.setBounds(bounds);

  try {
    const res = await fetch("/api/directions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        origin_lat: userLat,
        origin_lng: userLng,
        dest_lat: restaurant.lat,
        dest_lng: restaurant.lng,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "경로를 찾을 수 없습니다.");

    const path = data.path.map((p) => new kakao.maps.LatLng(p.lat, p.lng));
    routePolyline = new kakao.maps.Polyline({
      map: kakaoMap,
      path,
      strokeWeight: 5,
      strokeColor: "#ff6b35",
      strokeOpacity: 0.85,
      strokeStyle: "solid",
    });
    path.forEach((p) => bounds.extend(p));
    kakaoMap.setBounds(bounds);

    const minutes = Math.round(data.duration_sec / 60);
    mapModalSummary.textContent = `도보 ${data.distance_m}m · 약 ${minutes}분`;
  } catch (e) {
    mapModalSummary.textContent = `경로를 불러오지 못했습니다: ${e.message}`;
  }
}

mapModalClose.addEventListener("click", () => {
  mapModal.classList.add("hidden");
});

window.openRouteMap = openRouteMap;
