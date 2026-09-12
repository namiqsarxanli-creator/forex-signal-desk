(function () {
  const btn = document.getElementById("demoBtn");
  if (!btn) return;

  const STEPS = [
    { icon: "🔍", text: "Bazar məlumatı oxunur..." },
    { icon: "🤖", text: "RSI mühərriki qərar verir..." },
    { icon: "🛡️", text: "Risk zənciri yoxlayır (icazəli cüt, MAX_VOLUME, SL/TP)..." },
    { icon: "⚡", text: "Siqnal icra olunur..." },
  ];

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function buildOverlay() {
    const overlay = document.createElement("div");
    overlay.className = "demo-overlay";
    overlay.innerHTML = `
      <div class="demo-card">
        <h3>Canlı Demo</h3>
        <ol class="demo-steps" id="demoSteps"></ol>
        <div class="demo-result" id="demoResult"></div>
      </div>
    `;
    document.body.appendChild(overlay);
    return overlay;
  }

  async function run() {
    btn.disabled = true;
    const overlay = buildOverlay();
    const stepsEl = overlay.querySelector("#demoSteps");
    const resultEl = overlay.querySelector("#demoResult");

    const requestPromise = fetch("/demo/run", { method: "POST" }).then((r) => r.json());

    for (const step of STEPS) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="demo-icon">${step.icon}</span><span>${step.text}</span>`;
      stepsEl.appendChild(li);
      await sleep(600);
      li.classList.add("done");
    }

    try {
      const data = await requestPromise;
      const dirWord = data.action === "BUY" ? "AL (BUY)" : "SAT (SELL)";
      const closeLi = document.createElement("li");
      closeLi.className = "done";
      closeLi.innerHTML = `<span class="demo-icon">📈</span><span>Bazar Take-Profit səviyyəsinə çatdı, mövqe bağlanır...</span>`;
      stepsEl.appendChild(closeLi);

      resultEl.innerHTML = `
        <div class="demo-result-row"><strong>${data.symbol}</strong> ${dirWord} ${data.volume} lot @ ${data.entry_price}</div>
        <div class="demo-result-sub">SL ${data.stop_loss} · TP ${data.take_profit} · balansa görə hesablanmış lot · Risk mühərrikindən keçdi ✓</div>
      `;

      if (data.closed_profit_loss !== null && data.closed_profit_loss !== undefined) {
        await sleep(300);
        const sign = data.closed_profit_loss >= 0 ? "+" : "";
        const pnlRow = document.createElement("div");
        pnlRow.className = "demo-result-pnl";
        pnlRow.textContent = `Nəticə: ${sign}${data.closed_profit_loss.toFixed(2)} USD`;
        resultEl.appendChild(pnlRow);
      }
    } catch (err) {
      resultEl.innerHTML = `<div class="demo-result-row error">Xəta baş verdi, backend loqlarını yoxlayın.</div>`;
    }

    await sleep(3200);
    overlay.classList.add("closing");
    await sleep(300);
    overlay.remove();
    btn.disabled = false;
  }

  btn.addEventListener("click", run);
})();
