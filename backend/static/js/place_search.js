// 입력창에 건물/장소 이름을 치면 카카오 로컬 검색으로 캠퍼스 근처 결과를 보여주고,
// 고르면 onSelect(place)로 좌표를 넘겨줌 (place가 null이면 선택 해제됨).
function attachPlaceSearch(inputEl, resultsEl, onSelect) {
  let debounceTimer = null;

  function hideResults() {
    resultsEl.classList.add("hidden");
    resultsEl.innerHTML = "";
  }

  inputEl.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = inputEl.value.trim();
    if (q.length === 0) {
      onSelect(null);
      hideResults();
      return;
    }
    if (q.length < 2) {
      hideResults();
      return;
    }
    debounceTimer = setTimeout(async () => {
      let data;
      try {
        const res = await fetch(`/api/search-place?q=${encodeURIComponent(q)}`);
        data = await res.json();
      } catch {
        hideResults();
        return;
      }
      resultsEl.innerHTML = "";
      if (!data.places || data.places.length === 0) {
        hideResults();
        return;
      }
      for (const p of data.places) {
        const item = document.createElement("div");
        item.className = "place-search-item";
        item.innerHTML = `<strong>${p.name}</strong><span>${p.address || ""}</span>`;
        item.addEventListener("click", () => {
          inputEl.value = p.name;
          hideResults();
          onSelect(p);
        });
        resultsEl.appendChild(item);
      }
      resultsEl.classList.remove("hidden");
    }, 300);
  });

  document.addEventListener("click", (e) => {
    if (e.target !== inputEl && !resultsEl.contains(e.target)) hideResults();
  });
}

window.attachPlaceSearch = attachPlaceSearch;
