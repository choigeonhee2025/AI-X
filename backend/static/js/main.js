const whoamiEl = document.getElementById("whoami");
const logoutBtn = document.getElementById("logoutBtn");
const pillsEl = document.getElementById("categoryPills");
const locateBtn = document.getElementById("locateBtn");
const locateBtnText = document.getElementById("locateBtnText");
const locationStatus = document.getElementById("locationStatus");
const submitBtn = document.getElementById("submitBtn");
const submitBtnText = document.getElementById("submitBtnText");
const form = document.getElementById("form");
const resultsEl = document.getElementById("results");
const modelNoticeEl = document.getElementById("modelNotice");
const randomPickBtn = document.getElementById("randomPickBtn");
const favOnlyToggleBtn = document.getElementById("favOnlyToggleBtn");
const originSearchInput = document.getElementById("originSearchInput");
const originSearchResults = document.getElementById("originSearchResults");
const destSearchInput = document.getElementById("destSearchInput");
const destSearchResults = document.getElementById("destSearchResults");
const destStatus = document.getElementById("destStatus");

const CATEGORY_EMOJI = {
  "전체": "🍽️", "한식": "🍚", "중식": "🥢", "일식": "🍣", "양식": "🍝",
  "분식": "🍢", "카페": "☕", "치킨": "🍗", "술집": "🍺", "뷔페": "🍱",
  "패스트푸드": "🍔", "아시안": "🍜", "기타": "🍴",
};

let userLat = null;
let userLng = null;
let destLat = null;
let destLng = null;
let selectedCategory = "전체";
let currentUsername = null;
let latestFeasible = [];

attachPlaceSearch(originSearchInput, originSearchResults, (place) => {
  if (!place) return;
  userLat = place.lat;
  userLng = place.lng;
  locateBtn.classList.add("located");
  locationStatus.textContent = `출발 위치: ${place.name} (검색으로 선택됨)`;
  submitBtn.disabled = false;
});

attachPlaceSearch(destSearchInput, destSearchResults, (place) => {
  if (!place) {
    destLat = null;
    destLng = null;
    destStatus.textContent = "";
    return;
  }
  destLat = place.lat;
  destLng = place.lng;
  destStatus.textContent = `${place.name}로 복귀 예정`;
});
let favoriteIds = new Set();
let favOnlyActive = false;

async function toggleFavorite(restaurantId, cardEl) {
  const btn = cardEl.querySelector(".fav-btn");
  const isFav = favoriteIds.has(restaurantId);
  try {
    await fetch(`/api/favorites/${restaurantId}`, { method: isFav ? "DELETE" : "POST" });
  } catch {
    return; // 네트워크 오류면 상태 바꾸지 않음
  }
  if (isFav) {
    favoriteIds.delete(restaurantId);
    btn.textContent = "☆";
    btn.classList.remove("active");
    if (favOnlyActive) cardEl.style.display = "none";
  } else {
    favoriteIds.add(restaurantId);
    btn.textContent = "⭐";
    btn.classList.add("active");
  }
}

function applyFavFilter() {
  resultsEl.querySelectorAll(".result-card").forEach((card) => {
    const id = Number(card.dataset.id);
    card.style.display = favOnlyActive && !favoriteIds.has(id) ? "none" : "";
  });
}

function renderPills(categories) {
  pillsEl.innerHTML = "";
  for (const c of categories) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill" + (c === selectedCategory ? " active" : "");
    btn.textContent = `${CATEGORY_EMOJI[c] || "🍴"} ${c}`;
    btn.addEventListener("click", () => {
      selectedCategory = c;
      [...pillsEl.children].forEach((el) => el.classList.remove("active"));
      btn.classList.add("active");
    });
    pillsEl.appendChild(btn);
  }
}

async function loadCategories() {
  const res = await fetch("/api/restaurants");
  const data = await res.json();
  renderPills(data.categories);
}

async function loadMe() {
  const res = await fetch("/api/me");
  const data = await res.json();
  currentUsername = data.username;
  whoamiEl.textContent = currentUsername ? `${currentUsername}님` : "";
}

logoutBtn.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "/login";
});

locateBtn.addEventListener("click", () => {
  if (!navigator.geolocation) {
    locationStatus.textContent = "이 브라우저는 위치 정보를 지원하지 않습니다.";
    return;
  }
  locateBtnText.textContent = "위치 확인 중...";
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      userLat = pos.coords.latitude;
      userLng = pos.coords.longitude;
      originSearchInput.value = "";
      locateBtn.classList.add("located");
      locateBtnText.textContent = "위치 다시 가져오기";
      locationStatus.textContent = `현재 위치 확인됨 (${userLat.toFixed(5)}, ${userLng.toFixed(5)})`;
      submitBtn.disabled = false;
    },
    (err) => {
      locateBtnText.textContent = "현재 위치 가져오기";
      locationStatus.textContent = `위치를 가져오지 못했습니다: ${err.message}`;
    }
  );
});

function renderCard(r, feasible) {
  const div = document.createElement("div");
  div.className = `result-card ${feasible ? "feasible" : "infeasible"}`;
  div.dataset.id = r.id;
  const group = r.category_group || r.category;
  const emoji = CATEGORY_EMOJI[group] || "🍴";
  const usedPct = Math.min(100, Math.round((r.total_needed_min / (r.total_needed_min + Math.max(r.slack_min, 0))) * 100)) || 100;

  const waitMin = r.wait_min || 0;
  const mealMin = Math.round(r.total_needed_min - r.round_trip_min - waitMin);
  const waitPart = waitMin > 0 ? ` + 대기 ${waitMin}분` : "";
  const congestionBadge =
    r.congestion_pct != null
      ? `<span class="badge-congestion">혼잡도 ${Math.round(r.congestion_pct)}%</span>`
      : "";

  const sameReturnPoint = r.return_distance_m === r.distance_m;
  const distanceLine = sameReturnPoint
    ? `도보 거리 ${r.distance_m}m · 왕복 ${r.round_trip_min}분`
    : `도보 ${r.distance_m}m(갈 때 ${r.one_way_min}분) + ${r.return_distance_m}m(올 때 ${r.return_min}분) = 이동 ${r.round_trip_min}분`;

  div.innerHTML = `
    <div class="top-row">
      <div><span class="name">${emoji} ${r.name}</span><span class="cat" title="${r.category}">${group}</span>${congestionBadge}</div>
      <div class="top-row-right">
        <button type="button" class="report-btn" title="신고">🚩</button>
        <button type="button" class="fav-btn${r.is_favorite ? " active" : ""}" title="즐겨찾기">${r.is_favorite ? "⭐" : "☆"}</button>
        <span class="badge">${feasible ? `여유 ${r.slack_min}분` : `${Math.abs(r.slack_min)}분 초과`}</span>
      </div>
    </div>
    <div class="meta">${distanceLine} + 식사 ${mealMin}분${waitPart} = 총 ${r.total_needed_min}분</div>
    <div class="progress-track"><div class="progress-fill" style="width:${usedPct}%"></div></div>
    <div class="card-actions">
      <button type="button" class="map-link-btn">🗺 지도 보기</button>
      <button type="button" class="share-btn">💬 공유</button>
    </div>
  `;
  div.querySelector(".share-btn").addEventListener("click", () => window.shareRestaurant(r));
  div.querySelector(".map-link-btn").addEventListener("click", () => {
    window.openRouteMap({ name: r.name, lat: r.lat, lng: r.lng }, userLat, userLng);
  });
  div.querySelector(".fav-btn").addEventListener("click", () => toggleFavorite(r.id, div));
  div.querySelector(".report-btn").addEventListener("click", () => window.openReportModal(r.id, r.name));
  return div;
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtnText.innerHTML = isLoading ? '<span class="spinner"></span>찾는 중...' : "추천받기";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (userLat === null) return;

  setLoading(true);
  resultsEl.innerHTML = "";

  const payload = {
    break_minutes: Number(document.getElementById("breakMinutes").value),
    meal_minutes: Number(document.getElementById("mealMinutes").value),
    category: selectedCategory,
    lat: userLat,
    lng: userLng,
    dest_lat: destLat,
    dest_lng: destLng,
  };

  try {
    const res = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.status === 401) {
      window.location.href = "/login";
      return;
    }
    const data = await res.json();

    const tierText = {
      model: `실측 데이터 ${data.trip_count}건으로 학습된 개인화 모델 사용 중`,
      personal_avg: `${data.member}님 본인 기록 기반 개인 평균 속도 사용 중`,
      default: `아직 개인 기록이 부족해 전체 평균 보행속도(67m/분) 기본값 사용 중`,
    };
    modelNoticeEl.textContent = `${tierText[data.personalization_tier] || ""} (전체 실측 ${data.trip_count}건)`;

    if (data.feasible.length === 0 && data.infeasible.length === 0) {
      resultsEl.innerHTML = '<div class="empty-state">해당 카테고리의 음식점이 없어요.</div>';
    } else if (data.feasible.length === 0) {
      resultsEl.innerHTML = '<div class="empty-state">이 공강 시간 안에 다녀올 수 있는 곳이 없어요 😢<br />시간을 늘리거나 다른 음식을 선택해보세요.</div>';
    }

    for (const r of data.feasible) resultsEl.appendChild(renderCard(r, true));
    for (const r of data.infeasible.slice(0, 3)) resultsEl.appendChild(renderCard(r, false));

    latestFeasible = data.feasible;
    randomPickBtn.classList.toggle("hidden", latestFeasible.length === 0);

    favoriteIds = new Set(
      [...data.feasible, ...data.infeasible].filter((r) => r.is_favorite).map((r) => r.id)
    );
    favOnlyToggleBtn.classList.remove("hidden");
    if (favOnlyActive) applyFavFilter();
  } finally {
    setLoading(false);
  }
});

randomPickBtn.addEventListener("click", () => {
  const pool = favOnlyActive ? latestFeasible.filter((r) => favoriteIds.has(r.id)) : latestFeasible;
  if (pool.length === 0) return;
  const pick = pool[Math.floor(Math.random() * pool.length)];
  const card = resultsEl.querySelector(`[data-id="${pick.id}"]`);
  if (!card) return;
  resultsEl.querySelectorAll(".result-card.picked").forEach((el) => el.classList.remove("picked"));
  card.classList.add("picked");
  card.scrollIntoView({ behavior: "smooth", block: "center" });
  randomPickBtn.textContent = `🎲 오늘은 ${pick.name} 어때요?`;
  setTimeout(() => {
    randomPickBtn.textContent = "🎲 오늘은 여기! 랜덤 추천";
  }, 3000);
});

favOnlyToggleBtn.addEventListener("click", () => {
  favOnlyActive = !favOnlyActive;
  favOnlyToggleBtn.classList.toggle("active", favOnlyActive);
  applyFavFilter();
});

loadCategories();
loadMe();
