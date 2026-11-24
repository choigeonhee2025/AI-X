const whoamiEl = document.getElementById("whoami");
const logoutBtn = document.getElementById("logoutBtn");
const statusTabs = document.getElementById("statusTabs");
const reportListEl = document.getElementById("reportList");

const CATEGORY_GROUPS = [
  "한식", "중식", "일식", "양식", "분식", "카페",
  "치킨", "술집", "뷔페", "패스트푸드", "아시안", "기타",
];

let currentStatus = "open";

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

loadMe();
loadReports();
