const whoamiEl = document.getElementById("whoami");
const logoutBtn = document.getElementById("logoutBtn");
const statusTabs = document.getElementById("statusTabs");
const reportListEl = document.getElementById("reportList");
const pageTabs = document.getElementById("pageTabs");
const reportsPage = document.getElementById("reportsPage");
const restaurantsPage = document.getElementById("restaurantsPage");

const CATEGORY_GROUPS = [
  "한식", "중식", "일식", "양식", "분식", "카페",
  "치킨", "술집", "뷔페", "패스트푸드", "아시안", "기타",
];
const CATEGORY_EMOJI = {
  "한식": "🍚", "중식": "🥢", "일식": "🍣", "양식": "🍝",
  "분식": "🍢", "카페": "☕", "치킨": "🍗", "술집": "🍺",
  "뷔페": "🍱", "패스트푸드": "🍔", "아시안": "🍜", "기타": "🍴",
};

let currentStatus = "open";

pageTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".pill");
  if (!btn) return;
  [...pageTabs.children].forEach((el) => el.classList.remove("active"));
  btn.classList.add("active");
  const isReports = btn.dataset.page === "reports";
  reportsPage.classList.toggle("hidden", !isReports);
  restaurantsPage.classList.toggle("hidden", isReports);
  if (!isReports) loadManualRestaurants();
});

async function loadMe() {
  const res = await fetch("/api/me");
  const data = await res.json();
  whoamiEl.textContent = data.username ? `${data.username}님 (관리자)` : "";
}

logoutBtn.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "/login";
});

function categoryOptions(current) {
  return CATEGORY_GROUPS.map(
    (g) => `<option value="${g}" ${g === current ? "selected" : ""}>${g}</option>`
  ).join("");
}

function renderReport(r) {
  const div = document.createElement("div");
  div.className = "card report-card";
  div.innerHTML = `
    <div class="top-row">
      <span class="name">${r.restaurant_name}</span>
      <span class="badge">${r.reason_label}</span>
    </div>
    <div class="meta">
      신고자 ${r.reporter} · ${new Date(r.created_at).toLocaleString("ko-KR")}
      ${r.detail ? `<br />"${r.detail}"` : ""}
    </div>

    <div class="field">
      <label>이름</label>
      <input type="text" class="edit-name" value="${r.restaurant_name}" />
    </div>
    <div class="field">
      <label>카테고리</label>
      <select class="edit-category">${categoryOptions(r.restaurant_category)}</select>
    </div>
    <div class="field">
      <label>주소</label>
      <input type="text" class="edit-address" value="${r.restaurant_address || ""}" />
    </div>
    <div class="collect-row">
      <div class="field">
        <label>위도</label>
        <input type="text" class="edit-lat" value="${r.restaurant_lat}" />
      </div>
      <div class="field">
        <label>경도</label>
        <input type="text" class="edit-lng" value="${r.restaurant_lng}" />
      </div>
    </div>

    <div class="collect-row">
      <button type="button" class="ghost-btn save-btn">💾 정보 저장</button>
      ${
        r.status === "open"
          ? `<button type="button" class="ghost-btn resolve-btn">✅ 해결됨</button>
             <button type="button" class="text-btn dismiss-btn">기각</button>`
          : `<span class="hint">상태: ${r.status}</span>`
      }
    </div>
  `;

  div.querySelector(".save-btn").addEventListener("click", async () => {
    await fetch(`/api/admin/restaurants/${r.restaurant_id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: div.querySelector(".edit-name").value.trim(),
        category: div.querySelector(".edit-category").value,
        address: div.querySelector(".edit-address").value.trim(),
        lat: div.querySelector(".edit-lat").value,
        lng: div.querySelector(".edit-lng").value,
      }),
    });
    div.querySelector(".save-btn").textContent = "✅ 저장됨";
  });

  const resolveBtn = div.querySelector(".resolve-btn");
  if (resolveBtn) {
    resolveBtn.addEventListener("click", () => setStatus(r.id, "resolved", div));
  }
  const dismissBtn = div.querySelector(".dismiss-btn");
  if (dismissBtn) {
    dismissBtn.addEventListener("click", () => setStatus(r.id, "dismissed", div));
  }

  return div;
}

async function setStatus(reportId, status, div) {
  await fetch(`/api/admin/reports/${reportId}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  div.remove();
}

async function loadReports() {
  reportListEl.innerHTML = '<div class="empty-state">불러오는 중...</div>';
  const res = await fetch(`/api/admin/reports?status=${currentStatus}`);
  const data = await res.json();
  reportListEl.innerHTML = "";
  if (data.reports.length === 0) {
    reportListEl.innerHTML = '<div class="empty-state">신고가 없어요.</div>';
    return;
  }
  for (const r of data.reports) reportListEl.appendChild(renderReport(r));
}

statusTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".pill");
  if (!btn) return;
  currentStatus = btn.dataset.status;
  [...statusTabs.children].forEach((el) => el.classList.remove("active"));
  btn.classList.add("active");
  loadReports();
});

// ---------- 음식점 관리 ----------

const pillsEl = document.getElementById("categoryPills");
const customCategoryEl = document.getElementById("customCategory");
const locateBtn = document.getElementById("locateBtn");
const locateBtnText = document.getElementById("locateBtnText");
const locationStatus = document.getElementById("locationStatus");
const latInput = document.getElementById("lat");
const lngInput = document.getElementById("lng");
const addForm = document.getElementById("addForm");
const submitBtn = document.getElementById("submitBtn");
const submitBtnText = document.getElementById("submitBtnText");
const formMsg = document.getElementById("formMsg");
const manualListEl = document.getElementById("manualRestaurantList");
const dummyNoticeEl = document.getElementById("dummyNotice");
const clearDummyBtn = document.getElementById("clearDummyBtn");
const restaurantSearchInput = document.getElementById("restaurantSearchInput");
const restaurantSearchResults = document.getElementById("restaurantSearchResults");

let selectedCategory = null;

function renderCategoryPills() {
  pillsEl.innerHTML = "";
  for (const c of CATEGORY_GROUPS) {
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

function renderRestaurantRow(r, { onDelete }) {
  const div = document.createElement("div");
  div.className = "card report-card";
  const isDummy = r.source === "dummy_sample";
  div.innerHTML = `
    <div class="top-row">
      <div><span class="name">${CATEGORY_EMOJI[r.category] || "🍴"} ${r.name}</span><span class="cat">${r.category}</span></div>
      <button type="button" class="text-btn" style="color:#b23a3a;">삭제</button>
    </div>
    <div class="meta">${r.address || "주소 없음"} · ${isDummy ? "더미 데이터" : r.source}</div>
  `;
  div.querySelector("button").addEventListener("click", async () => {
    await fetch(`/api/restaurants/${r.id}`, { method: "DELETE" });
    onDelete();
  });
  return div;
}

async function loadManualRestaurants() {
  const res = await fetch("/api/admin/restaurants/list");
  const data = await res.json();
  const dummyCount = data.restaurants.filter((r) => r.source === "dummy_sample").length;
  dummyNoticeEl.textContent = dummyCount > 0 ? `더미 데이터 ${dummyCount}개 남음` : "더미 데이터 없음";

  manualListEl.innerHTML = "";
  if (data.restaurants.length === 0) {
    manualListEl.innerHTML = '<div class="empty-state">직접 추가한 음식점이 없어요.</div>';
    return;
  }
  for (const r of data.restaurants) {
    manualListEl.appendChild(renderRestaurantRow(r, { onDelete: loadManualRestaurants }));
  }
}

clearDummyBtn.addEventListener("click", async () => {
  await fetch("/api/restaurants/dummy", { method: "DELETE" });
  loadManualRestaurants();
});

function setAddLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtnText.innerHTML = isLoading ? '<span class="spinner"></span>추가 중...' : "추가하기";
}

addForm.addEventListener("submit", async (e) => {
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

  setAddLoading(true);
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
    addForm.reset();
    selectedCategory = null;
    [...pillsEl.children].forEach((el) => el.classList.remove("active"));
    locationStatus.textContent = "버튼을 누르거나, 아래에 좌표를 직접 입력하세요.";
    formMsg.textContent = "추가됐어요!";
    loadManualRestaurants();
  } finally {
    setAddLoading(false);
  }
});

let searchDebounce = null;
restaurantSearchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  const q = restaurantSearchInput.value.trim();
  if (q.length < 2) {
    restaurantSearchResults.innerHTML = "";
    return;
  }
  searchDebounce = setTimeout(async () => {
    const res = await fetch(`/api/admin/restaurants/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    restaurantSearchResults.innerHTML = "";
    if (data.restaurants.length === 0) {
      restaurantSearchResults.innerHTML = '<div class="empty-state">결과 없음</div>';
      return;
    }
    for (const r of data.restaurants) {
      restaurantSearchResults.appendChild(
        renderRestaurantRow(r, {
          onDelete: () => restaurantSearchInput.dispatchEvent(new Event("input")),
        })
      );
    }
  }, 300);
});

renderCategoryPills();
loadMe();
loadReports();
