const memberSelect = document.getElementById("memberSelect");
const pillsEl = document.getElementById("categoryPills");
const locateBtn = document.getElementById("locateBtn");
const locateBtnText = document.getElementById("locateBtnText");
const locationStatus = document.getElementById("locationStatus");
const submitBtn = document.getElementById("submitBtn");
const submitBtnText = document.getElementById("submitBtnText");
const form = document.getElementById("form");
const resultsEl = document.getElementById("results");
const modelNoticeEl = document.getElementById("modelNotice");

const CATEGORY_EMOJI = {
  "전체": "🍽️", "한식": "🍚", "중식": "🥢", "일식": "🍣",
  "양식": "🍝", "분식": "🍢", "카페": "☕", "패스트푸드": "🍔", "아시안": "🍜",
};

let userLat = null;
let userLng = null;
let selectedCategory = "전체";

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

async function loadMembers() {
  const res = await fetch("/api/members");
  const data = await res.json();
  memberSelect.innerHTML = "";
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "선택 안 함(전체 평균)";
  memberSelect.appendChild(noneOpt);
  for (const m of data.members) {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    memberSelect.appendChild(opt);
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
      userLat = pos.coords.latitude;
      userLng = pos.coords.longitude;
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
  const emoji = CATEGORY_EMOJI[r.category] || "🍴";
  const usedPct = Math.min(100, Math.round((r.total_needed_min / (r.total_needed_min + Math.max(r.slack_min, 0))) * 100)) || 100;

  div.innerHTML = `
    <div class="top-row">
      <div><span class="name">${emoji} ${r.name}</span><span class="cat">${r.category}</span></div>
      <span class="badge">${feasible ? `여유 ${r.slack_min}분` : `${Math.abs(r.slack_min)}분 초과`}</span>
    </div>
    <div class="meta">도보 거리 ${r.distance_m}m · 왕복 ${r.round_trip_min}분 + 식사 ${Math.round(r.total_needed_min - r.round_trip_min)}분 = 총 ${r.total_needed_min}분</div>
    <div class="progress-track"><div class="progress-fill" style="width:${usedPct}%"></div></div>
  `;
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
    member: memberSelect.value || null,
  };

  try {
    const res = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    const tierText = {
      model: `실측 데이터 ${data.trip_count}건으로 학습된 개인화 모델 사용 중`,
      personal_avg: `${memberSelect.value}님 본인 기록 기반 개인 평균 속도 사용 중`,
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
  } finally {
    setLoading(false);
  }
});

loadCategories();
loadMembers();
