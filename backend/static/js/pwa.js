if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

// 설치 버튼 - manifest+서비스워커만 있으면 브라우저 주소창 구석에 작은 설치 아이콘이
// 뜨긴 하는데 눈에 잘 안 띄어서, 화면에 직접 "앱 설치하기" 버튼을 띄워줌.
(function setupInstallButton() {
  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  if (isStandalone) return; // 이미 설치해서 앱으로 열고 있으면 필요 없음

  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "pwaInstallBtn";
  btn.className = "pwa-install-btn hidden";
  btn.textContent = "📲 앱 설치하기";
  document.body.appendChild(btn);

  // iOS Safari는 beforeinstallprompt 자체가 없어서(설치를 코드로 띄울 방법이 없음),
  // 수동 설치 방법을 안내하는 버튼을 대신 보여줌.
  const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
  if (isIos) {
    btn.textContent = "📲 앱으로 설치하는 방법";
    btn.classList.remove("hidden");
    btn.addEventListener("click", () => {
      alert("Safari 하단의 공유 버튼(□↑) → '홈 화면에 추가'를 누르면 앱처럼 설치돼요.");
    });
    return;
  }

  let deferredPrompt = null;

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
    btn.classList.remove("hidden");
  });

  window.addEventListener("appinstalled", () => {
    btn.classList.add("hidden");
    deferredPrompt = null;
  });

  btn.addEventListener("click", async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    btn.classList.add("hidden");
  });
})();
