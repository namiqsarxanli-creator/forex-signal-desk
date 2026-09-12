(function () {
  const textEl = document.getElementById("analysisText");
  const refreshBtn = document.getElementById("analysisRefreshBtn");
  if (!textEl) return;

  function renderAnalysis(text) {
    // Put the disclaimer on its own visually distinct line if present.
    const marker = "⚠️";
    const idx = text.indexOf(marker);
    if (idx === -1) {
      textEl.innerHTML = `<p>${text}</p>`;
      return;
    }
    const body = text.slice(0, idx).trim();
    const warning = text.slice(idx).trim();
    textEl.innerHTML = `<p>${body}</p><p class="ai-disclaimer">${warning}</p>`;
  }

  async function load() {
    if (refreshBtn) refreshBtn.disabled = true;
    textEl.innerHTML = '<span class="empty">Analiz hazırlanır…</span>';
    try {
      const res = await fetch("/market/analysis");
      const data = await res.json();
      renderAnalysis(data.analysis || "Analiz alına bilmədi.");
    } catch (err) {
      textEl.innerHTML = '<span class="empty">Analiz yüklənərkən xəta baş verdi.</span>';
    } finally {
      if (refreshBtn) refreshBtn.disabled = false;
    }
  }

  if (refreshBtn) refreshBtn.addEventListener("click", load);
  load();
})();
