// 카카오톡 공유하기. 지도(map.js)에서 쓰는 카카오맵 SDK와는 다른 SDK라서 따로 불러옵니다.
let kakaoShareReady = null;

function loadKakaoShareSdk() {
  if (kakaoShareReady) return kakaoShareReady;
  kakaoShareReady = fetch("/api/config")
    .then((res) => res.json())
    .then(
      (config) =>
        new Promise((resolve, reject) => {
          if (!config.kakao_js_key) {
            reject(new Error("카카오 키가 설정되지 않았습니다."));
            return;
          }
          if (window.Kakao) {
            if (!window.Kakao.isInitialized()) window.Kakao.init(config.kakao_js_key);
            resolve();
            return;
          }
          const script = document.createElement("script");
          script.src = "https://t1.kakaocdn.net/kakao_js_sdk/2.7.4/kakao.min.js";
          script.onload = () => {
            window.Kakao.init(config.kakao_js_key);
            resolve();
          };
          script.onerror = () => reject(new Error("카카오 SDK 로드 실패"));
          document.head.appendChild(script);
        })
    );
  return kakaoShareReady;
}

async function shareRestaurant(restaurant) {
  try {
    await loadKakaoShareSdk();
  } catch (e) {
    alert(e.message);
    return;
  }

  try {
    window.Kakao.Share.sendDefault({
      objectType: "feed",
      content: {
        title: `🍱 ${restaurant.name}`,
        description: `공강 시간 안에 다녀올 수 있는 곳으로 추천받았어요! (도보 ${restaurant.distance_m}m · 총 ${restaurant.total_needed_min}분)`,
        imageUrl: `${location.origin}/icons/icon-512.png`,
        link: { mobileWebUrl: location.origin, webUrl: location.origin },
      },
      buttons: [{ title: "나도 추천받기", link: { mobileWebUrl: location.origin, webUrl: location.origin } }],
    });
  } catch (e) {
    alert("공유 창을 여는 데 실패했어요. 카카오 디벨로퍼스에서 '카카오톡 공유' 제품이 켜져 있는지 확인해주세요.");
  }
}

window.shareRestaurant = shareRestaurant;
