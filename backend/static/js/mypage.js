const whoamiEl = document.getElementById("whoami");
const logoutBtn = document.getElementById("logoutBtn");

logoutBtn.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "/login";
});

async function load() {
  const res = await fetch("/api/mypage");
  const data = await res.json();

  whoamiEl.textContent = data.username ? `${data.username}님` : "";
  document.getElementById("recommendCount").textContent = data.recommend_count;
  document.getElementById("favoriteCount").textContent = data.favorite_count;
  document.getElementById("tripCount").textContent = data.trip_count;
  document.getElementById("topCategory").textContent = data.top_category
    ? `${data.top_category} (가장 자주 선택함)`
    : "아직 추천을 받아본 적이 없어요.";
  document.getElementById("personalizationNotice").textContent = data.using_trained_model
    ? "실측 데이터로 학습된 개인화 모델을 사용 중이에요."
    : data.trip_count > 0
    ? "개인 평균 속도를 사용 중이에요 (모델 학습에는 전체 5건 이상 필요)."
    : "아직 이동시간 기록이 없어 전체 평균 속도(67m/분)를 기본값으로 써요.";
}

load();
