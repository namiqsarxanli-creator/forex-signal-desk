(function () {
  const panel = document.getElementById("calculator");
  if (!panel) return;

  const maxVolume = parseFloat(panel.dataset.maxVolume || "0.01");
  const balanceEl = document.getElementById("calcBalance");
  const riskEl = document.getElementById("calcRisk");
  const symbolEl = document.getElementById("calcSymbol");
  const slEl = document.getElementById("calcSl");
  const resultEl = document.getElementById("calcResult");

  function pipValuePerLot(symbol) {
    // Approximate USD value of 1 pip on a 1.0 standard lot. Real value depends
    // on the live cross rate and the broker; this is a planning estimate only.
    return symbol.endsWith("JPY") ? 9.1 : 10;
  }

  function calc() {
    const balance = parseFloat(balanceEl.value) || 0;
    const riskPct = parseFloat(riskEl.value) || 0;
    const sl = parseFloat(slEl.value) || 0;
    const symbol = symbolEl.value;

    const riskAmount = balance * (riskPct / 100);
    const pipValue = pipValuePerLot(symbol);
    const rawLots = sl > 0 ? riskAmount / (sl * pipValue) : 0;
    const lots = Math.round(rawLots * 100) / 100;
    const exceeds = lots > maxVolume;

    resultEl.innerHTML = `
      <div class="calc-row"><span>Tövsiyə olunan lot ölçüsü</span><strong>${lots.toFixed(2)}</strong></div>
      <div class="calc-row"><span>Risk edilən məbləğ</span><strong>$${riskAmount.toFixed(2)}</strong></div>
      <div class="calc-row"><span>Sistemin MAX_VOLUME həddi</span><strong>${maxVolume}</strong></div>
      ${
        exceeds
          ? `<p class="calc-warn">⚠ Hesablanan lot sistemin risk limitini aşır — icra zamanı risk mühərriki avtomatik ${maxVolume} lota qədər məhdudlaşdıracaq.</p>`
          : `<p class="calc-ok">✓ Bu ölçü sistemin risk qaydalarına (MAX_VOLUME) uyğundur.</p>`
      }
    `;
  }

  [balanceEl, riskEl, symbolEl, slEl].forEach((el) => el.addEventListener("input", calc));
  calc();
})();
