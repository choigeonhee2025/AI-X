const memberSelect = document.getElementById("memberSelect");
const startBtn = document.getElementById("startBtn");
const endBtn = document.getElementById("endBtn");
const resetBtn = document.getElementById("resetBtn");
const statusEl = document.getElementById("status");
const tripCountEl = document.getElementById("tripCount");
const modelStatusEl = document.getElementById("modelStatus");
const perMemberEl = document.getElementById("perMember");
const tripTableBody = document.querySelector("#tripTable tbody");

let pendingStart = null; // { lat, lng, ts }

async function loadMembers() {
  const res = await fetch("/api/members");
  const data = await res.json();
  memberSelect.innerHTML = "";
  for (const m of data.members) {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    memberSelect.appendChild(opt);
  }
}

function getPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("이 브라우저는 위치 정보를 지원하지 않습니다."));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true });
  });
}

async function refreshStatus() {
  const res = await fetch("/api/trips/count");
  const data = await res.json();
  tripCountEl.textContent = data.trip_count;
  modelStatusEl.textContent = data.using_trained_model
    ? "학습된 회귀 모델 사용 중"
    : "아직 베이스라인(평균 속도) 사용 중 — 5건 이상 모이면 models/train_model.py를 실행해 학습하세요.";
  const perMemberText = Object.entries(data.per_member || {})
    .map(([name, n]) => `${name} ${n}건`)
    .join(" · ");
  perMemberEl.textContent = perMemberText ? `회원별: ${perMemberText}` : "";
}

async function loadRecentTrips() {
  const res = await fetch("/api/trips/recent");
  const data = await res.json();
  tripTableBody.innerHTML = "";
  for (const t of data.trips) addRow(t);
}

startBtn.addEventListener("click", async () => {
  try {
    statusEl.textContent = "출발 위치를 가져오는 중...";
    const pos = await getPosition();
    pendingStart = { lat: pos.coords.latitude, lng: pos.coords.longitude, ts: Date.now() };
    statusEl.textContent = "출발 기록됨. 식당에 도착하면 '도착 기록'을 눌러주세요.";
    startBtn.disabled = true;
    endBtn.disabled = false;
    memberSelect.disabled = true;
  } catch (err) {
    statusEl.textContent = `오류: ${err.message}`;
  }
});

endBtn.addEventListener("click", async () => {
  if (!pendingStart) return;
  try {
    statusEl.textContent = "도착 위치를 가져오는 중...";
    const pos = await getPosition();
    const end = { lat: pos.coords.latitude, lng: pos.coords.longitude, ts: Date.now() };

    const res = await fetch("/api/trips", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member: memberSelect.value,
        start_lat: pendingStart.lat,
        start_lng: pendingStart.lng,
        end_lat: end.lat,
        end_lng: end.lng,
        start_ts: pendingStart.ts,
        end_ts: end.ts,
      }),
    });
    const data = await res.json();
    if (data.error) {
      statusEl.textContent = `저장 실패: ${data.error}`;
    } else {
      statusEl.textContent = `저장됨: ${data.saved.distance_m}m, ${data.saved.duration_min}분`;
      addRow(data.saved);
    }
  } catch (err) {
    statusEl.textContent = `오류: ${err.message}`;
  } finally {
    pendingStart = null;
    startBtn.disabled = false;
    endBtn.disabled = true;
    memberSelect.disabled = false;
    refreshStatus();
  }
});

resetBtn.addEventListener("click", () => {
  pendingStart = null;
  startBtn.disabled = false;
  endBtn.disabled = true;
  memberSelect.disabled = false;
  statusEl.textContent = "취소되었습니다.";
});

function addRow(trip) {
  const tr = document.createElement("tr");
  const dowNames = ["월", "화", "수", "목", "금", "토", "일"];
  tr.innerHTML = `<td>${trip.member}</td><td>${trip.distance_m}</td><td>${trip.duration_min}</td><td>${trip.hour}시</td><td>${dowNames[trip.dow]}</td>`;
  tripTableBody.prepend(tr);
}

loadMembers();
refreshStatus();
loadRecentTrips();
