const whoamiEl = document.getElementById("whoami");
const logoutBtn = document.getElementById("logoutBtn");
const pillsEl = document.getElementById("categoryPills");
const customCategoryEl = document.getElementById("customCategory");
const locateBtn = document.getElementById("locateBtn");
const locateBtnText = document.getElementById("locateBtnText");
const locationStatus = document.getElementById("locationStatus");
const latInput = document.getElementById("lat");
const lngInput = document.getElementById("lng");
const form = document.getElementById("form");
const submitBtn = document.getElementById("submitBtn");
const submitBtnText = document.getElementById("submitBtnText");
const formMsg = document.getElementById("formMsg");
const restaurantListEl = document.getElementById("restaurantList");
const dummyNoticeEl = document.getElementById("dummyNotice");
const clearDummyBtn = document.getElementById("clearDummyBtn");

const CATEGORY_EMOJI = {
  "한식": "🍚", "중식": "🥢", "일식": "🍣", "양식": "🍝",
  "분식": "🍢", "카페": "☕", "치킨": "🍗", "술집": "🍺",
  "뷔페": "🍱", "패스트푸드": "🍔", "아시안": "🍜", "기타": "🍴",
};

let selectedCategory = null;

function renderPills(categories) {
  pillsEl.innerHTML = "";
  for (const c of categories) {
    if (c === "전체") continue;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill";
    btn.textContent = `${CATEGORY_EMOJI[c] || "🍴"} ${c}`;
    btn.addEventListener("click", () => {
      selectedCategory = c;
      customCategoryEl.value = "";
      [...pillsEl.children].forEach((el) => el.classList.remove("active"));
      btn.classList.add("active");
    });
    pillsEl.appendChild(btn);
  }
}

function loadCategories() {
  renderPills(Object.keys(CATEGORY_EMOJI));
}

async function loadMe() {
  const res = await fetch("/api/me");
  const data = await res.json();
  whoamiEl.textContent = data.username ? `${data.username}님` : "";
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
      latInput.value = pos.coords.latitude.toFixed(6);
      lngInput.value = pos.coords.longitude.toFixed(6);
      locateBtnText.textContent = "지금 내 위치 사용";
      locationStatus.textContent = `좌표 채워짐 (${latInput.value}, ${lngInput.value})`;
    },
    (err) => {
      locateBtnText.textContent = "지금 내 위치 사용";
      locationStatus.textContent = `위치를 가져오지 못했습니다: ${err.message}`;
    }
  );
});

function renderRestaurantList(restaurants) {
  const dummyCount = restaurants.filter((r) => r.source === "dummy_sample").length;
  dummyNoticeEl.textContent = dummyCount > 0 ? `더미 데이터 ${dummyCount}개 남음` : "더미 데이터 없음";

  restaurantListEl.innerHTML = "";
  if (restaurants.length === 0) {
    restaurantListEl.innerHTML = '<div class="empty-state">아직 등록된 음식점이 없어요.</div>';
    return;
  }
  for (const r of restaurants) {
    const div = document.createElement("div");
    div.className = "result-card feasible";
    const isDummy = r.source === "dummy_sample";
    div.innerHTML = `
      <div class="top-row">
        <div><span class="name">${CATEGORY_EMOJI[r.category] || "🍴"} ${r.name}</span><span class="cat">${r.category}</span></div>
        <button type="button" class="text-btn" style="color:#b23a3a;" data-id="${r.id}">삭제</button>
      </div>
      <div class="meta">${r.address || "주소 없음"} · ${isDummy ? "더미 데이터" : r.source}</div>
    `;
    div.querySelector("button").addEventListener("click", async () => {
      await fetch(`/api/restaurants/${r.id}`, { method: "DELETE" });
      loadRestaurants();
    });
    restaurantListEl.appendChild(div);
  }
}

async function loadRestaurants() {
  const res = await fetch("/api/restaurants/list");
  const data = await res.json();
  renderRestaurantList(data.restaurants);
}

clearDummyBtn.addEventListener("click", async () => {
  await fetch("/api/restaurants/dummy", { method: "DELETE" });
  loadRestaurants();
});

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtnText.innerHTML = isLoading ? '<span class="spinner"></span>추가 중...' : "추가하기";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  formMsg.textContent = "";

  const category = customCategoryEl.value.trim() || selectedCategory;
  const lat = parseFloat(latInput.value);
  const lng = parseFloat(lngInput.value);

  if (!category) {
    formMsg.textContent = "카테고리를 선택하거나 입력해주세요.";
    return;
  }
  if (Number.isNaN(lat) || Number.isNaN(lng)) {
    formMsg.textContent = "좌표가 필요해요 (위치 버튼을 누르거나 직접 입력).";
    return;
  }

  setLoading(true);
  try {
    const res = await fetch("/api/restaurants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: document.getElementById("name").value.trim(),
        category,
        lat,
        lng,
        address: document.getElementById("address").value.trim(),
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      formMsg.textContent = data.error || "추가하지 못했어요.";
      return;
    }
    form.reset();
    selectedCategory = null;
    [...pillsEl.children].forEach((el) => el.classList.remove("active"));
    locationStatus.textContent = "버튼을 누르거나, 아래에 좌표를 직접 입력하세요.";
    formMsg.textContent = "추가됐어요!";
    loadRestaurants();
  } finally {
    setLoading(false);
  }
});

loadMe();
loadCategories();
loadRestaurants();
