(function () {
  const tableBody = document.querySelector("#rsiTable tbody");
  const runBtn = document.getElementById("runNowBtn");
  const runStatus = document.getElementById("runNowStatus");
  const runResults = document.getElementById("runNowResults");
  if (!tableBody) return;

  function actionBadge(action) {
    if (action === "BUY") return '<span class="pill buy-pill">BUY</span>';
    if (action === "SELL") return '<span class="pill sell-pill">SELL</span>';
    return '<span class="pill neutral-pill">—</span>';
  }

  function renderReadings(readings) {
    if (!readings || !readings.length) {
      tableBody.innerHTML = '<tr><td colspan="4" class="empty">RSI məlumatı əlçatan deyil.</td></tr>';
      return;
    }
    tableBody.innerHTML = readings
      .map((r) => {
        const rsi = r.rsi === null || r.rsi === undefined ? "—" : r.rsi.toFixed(1);
        const price = r.last_price ? r.last_price.toFixed(5) : "—";
        return `<tr><td>${r.symbol}</td><td>${price}</td><td>${rsi}</td><td>${actionBadge(r.action)}</td></tr>`;
      })
      .join("");
  }

  async function loadPreview() {
    try {
      const res = await fetch("/signals/preview");
      const data = await res.json();
      renderReadings(data.readings);
    } catch (err) {
      tableBody.innerHTML = '<tr><td colspan="4" class="empty">RSI yüklənərkən xəta baş verdi.</td></tr>';
    }
  }

  async function runNow() {
    runBtn.disabled = true;
    runBtn.textContent = "İşləyir…";
    runStatus.textContent = "";
    runResults.innerHTML = "";
    try {
      const res = await fetch("/signals/run-now", { method: "POST" });
      const data = await res.json();
      const fired = (data.results || []).filter((r) => r.action);
      runStatus.textContent = fired.length
        ? `${fired.length} siqnal yaradıldı.`
        : "Hazırda heç bir cütdə RSI həddi keçilməyib (siqnal yoxdur).";

      runResults.innerHTML = (data.results || [])
        .map((r) => {
          if (!r.action) {
            return `<div class="run-row neutral"><b>${r.symbol}</b> RSI ${r.rsi ?? "—"} · siqnal yoxdur</div>`;
          }
          const status = r.result && r.result.status ? r.result.status : "unknown";
          return (
            `<div class="run-row ${r.action.toLowerCase()}">` +
            `<b>${r.symbol}</b> ${r.action} @ ${r.entry_price} · RSI ${r.rsi} · SL ${r.stop_loss} / TP ${r.take_profit} ` +
            `<span class="pill">${status}</span></div>`
          );
        })
        .join("");

      loadPreview();
    } catch (err) {
      runStatus.textContent = "Xəta baş verdi, backend loqlarını yoxlayın.";
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Siqnalı indi yarat";
    }
  }

  if (runBtn) runBtn.addEventListener("click", runNow);
  loadPreview();
  setInterval(loadPreview, 60000);
})();
