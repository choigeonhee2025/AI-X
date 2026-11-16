const form = document.getElementById("form");
const submitBtn = document.getElementById("submitBtn");
const submitBtnText = document.getElementById("submitBtnText");
const errorMsg = document.getElementById("errorMsg");

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtnText.innerHTML = isLoading ? '<span class="spinner"></span>확인 중...' : "시작하기";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorMsg.textContent = "";
  setLoading(true);

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  try {
    const loginRes = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (loginRes.ok) {
      window.location.href = "/";
      return;
    }

    // 로그인 실패 -> 처음 쓰는 이름일 수 있으니 가입 시도
    const signupRes = await fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const signupData = await signupRes.json();
    if (signupRes.ok) {
      window.location.href = "/";
      return;
    }

    if (signupData.error && signupData.error.includes("이미 있는 이름")) {
      errorMsg.textContent = "비밀번호가 틀렸어요.";
    } else {
      errorMsg.textContent = signupData.error || "문제가 생겼어요. 다시 시도해주세요.";
    }
  } catch (err) {
    errorMsg.textContent = `오류: ${err.message}`;
  } finally {
    setLoading(false);
  }
});
