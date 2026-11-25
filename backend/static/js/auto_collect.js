// 수동으로 출발/도착 버튼 누르는 대신, 웹을 켜놓고 걸어다니는 동안 자동으로
// 이동시간(trips) 기록을 모읍니다. GPS가 흔들리는 것까지 다 기록되면 안 되니까
// "어느 정도 이상 계속 움직였다가 멈췄을 때"만 한 구간으로 묶어서 저장합니다.
//
// 흐름: 위치가 바뀔 때마다 직전 지점과의 거리를 보고, MOVE_THRESHOLD_M보다 많이
// 움직였으면 "아직 걷는 중"으로 보고 lastMovedAt을 갱신. STOP_TIMEOUT_MS 동안 그런
// 움직임이 없으면 그 구간(세그먼트 시작 ~ 마지막으로 움직인 지점)을 trip으로 저장.
(function () {
  const MOVE_THRESHOLD_M = 10;
  const STOP_TIMEOUT_MS = 90 * 1000;
  const MIN_TRIP_DISTANCE_M = 80;
  const MIN_TRIP_DURATION_SEC = 20;
  const MAX_TRIP_DURATION_MIN = 45;
  const CHECK_INTERVAL_MS = 15 * 1000;
  const STORAGE_KEY = "autoCollectEnabled";

  function haversineM(lat1, lng1, lat2, lng2) {
    const R = 6371000;
    const toRad = (d) => (d * Math.PI) / 180;
    const dPhi = toRad(lat2 - lat1);
    const dLambda = toRad(lng2 - lng1);
    const a =
      Math.sin(dPhi / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLambda / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  let segmentStart = null; // {lat, lng, ts}
  let lastMovedPoint = null; // 마지막으로 "움직였다"고 판단된 지점
  let lastMovedAt = null;
  let watchId = null;

  function resetSegment() {
    segmentStart = null;
    lastMovedPoint = null;
    lastMovedAt = null;
  }

  async function saveTrip(start, end) {
    try {
      await fetch("/api/trips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_lat: start.lat,
          start_lng: start.lng,
          end_lat: end.lat,
          end_lng: end.lng,
          start_ts: start.ts,
          end_ts: end.ts,
        }),
      });
    } catch {
      // 네트워크 문제면 이번 구간은 포기 (다음 구간부터 다시 시도)
    }
  }

  function maybeFinalizeSegment() {
    if (!segmentStart || !lastMovedPoint) return;
    const elapsedSinceMove = Date.now() - lastMovedAt;
    if (elapsedSinceMove < STOP_TIMEOUT_MS) return;

    const distance = haversineM(segmentStart.lat, segmentStart.lng, lastMovedPoint.lat, lastMovedPoint.lng);
    const durationSec = (lastMovedPoint.ts - segmentStart.ts) / 1000;
    const durationMin = durationSec / 60;

    if (distance >= MIN_TRIP_DISTANCE_M && durationSec >= MIN_TRIP_DURATION_SEC && durationMin <= MAX_TRIP_DURATION_MIN) {
      saveTrip(segmentStart, lastMovedPoint);
    }
    resetSegment();
  }

  function onPosition(pos) {
    const point = { lat: pos.coords.latitude, lng: pos.coords.longitude, ts: Date.now() };

    if (!lastMovedPoint) {
      segmentStart = point;
      lastMovedPoint = point;
      lastMovedAt = point.ts;
      return;
    }

    const moved = haversineM(lastMovedPoint.lat, lastMovedPoint.lng, point.lat, point.lng);
    if (moved >= MOVE_THRESHOLD_M) {
      lastMovedPoint = point;
      lastMovedAt = point.ts;
    }
  }

  function start() {
    if (watchId !== null || !navigator.geolocation) return;
    resetSegment();
    watchId = navigator.geolocation.watchPosition(onPosition, () => {}, {
      enableHighAccuracy: true,
      maximumAge: 5000,
    });
    setInterval(maybeFinalizeSegment, CHECK_INTERVAL_MS);
  }

  function stop() {
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
    resetSegment();
  }

  function isEnabled() {
    try {
      return localStorage.getItem(STORAGE_KEY) !== "off"; // 기본값: 켜짐
    } catch {
      return true;
    }
  }

  function setEnabled(enabled) {
    try {
      localStorage.setItem(STORAGE_KEY, enabled ? "on" : "off");
    } catch {
      // 저장 안 돼도(시크릿 모드 등) 이번 세션 동작엔 지장 없음
    }
    if (enabled) start();
    else stop();
  }

  if (isEnabled()) start();

  window.autoCollect = { isEnabled, setEnabled };
})();
