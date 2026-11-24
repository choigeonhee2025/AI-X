const reportModal = document.getElementById("reportModal");
const reportModalTitle = document.getElementById("reportModalTitle");
const reportModalClose = document.getElementById("reportModalClose");
const reportReasonEl = document.getElementById("reportReason");
const reportDetailEl = document.getElementById("reportDetail");
const reportSubmitBtn = document.getElementById("reportSubmitBtn");
const reportModalMsg = document.getElementById("reportModalMsg");

let reportTargetId = null;

function openReportModal(restaurantId, restaurantName) {
  reportTargetId = restaurantId;
  reportModalTitle.textContent = `🚩 ${restaurantName} 신고`;
  reportReasonEl.value = "category";
  reportDetailEl.value = "";
  reportModalMsg.textContent = "";
  reportSubmitBtn.disabled = false;
  reportSubmitBtn.textContent = "신고하기";
  reportModal.classList.remove("hidden");
}

reportModalClose.addEventListener("click", () => {
  reportModal.classList.add("hidden");
});

reportSubmitBtn.addEventListener("click", async () => {
  reportSubmitBtn.disabled = true;
  reportSubmitBtn.textContent = "보내는 중...";
  try {
    const res = await fetch("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_id: reportTargetId,
        reason: reportReasonEl.value,
        detail: reportDetailEl.value.trim(),
      }),
    });
    if (!res.ok) throw new Error();
    reportModalMsg.textContent = "신고가 접수됐어요. 감사합니다!";
    setTimeout(() => reportModal.classList.add("hidden"), 1200);
  } catch {
    reportModalMsg.textContent = "신고 접수에 실패했어요. 다시 시도해주세요.";
    reportSubmitBtn.disabled = false;
    reportSubmitBtn.textContent = "신고하기";
  }
});

window.openReportModal = openReportModal;
