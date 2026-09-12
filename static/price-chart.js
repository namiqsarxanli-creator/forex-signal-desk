(function () {
  const svg = document.getElementById("priceSvg");
  const metaEl = document.getElementById("priceMeta");
  const symbolEl = document.getElementById("priceSymbol");
  if (!svg || !symbolEl) return;

  function draw(points) {
    const w = 600, h = 220, pad = 12;
    if (!points.length) {
      svg.innerHTML = "";
      return;
    }
    const closes = points.map((p) => p.close);
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const range = max - min || 1;
    const stepX = points.length > 1 ? (w - pad * 2) / (points.length - 1) : 0;

    const coords = points.map((p, i) => {
      const x = points.length > 1 ? pad + i * stepX : w / 2;
      const y = h - pad - ((p.close - min) / range) * (h - pad * 2);
      return [x, y];
    });

    const linePath = coords
      .map((c, i) => (i === 0 ? "M" : "L") + c[0].toFixed(1) + "," + c[1].toFixed(1))
      .join(" ");
    const areaPath =
      linePath +
      ` L${coords[coords.length - 1][0].toFixed(1)},${(h - pad).toFixed(1)}` +
      ` L${coords[0][0].toFixed(1)},${(h - pad).toFixed(1)} Z`;

    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.innerHTML = `
      <defs>
        <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.3"></stop>
          <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"></stop>
        </linearGradient>
      </defs>
      <path d="${areaPath}" fill="url(#priceGrad)" stroke="none"></path>
      <path id="priceLine" d="${linePath}" fill="none" stroke="var(--accent)" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round"></path>
    `;

    const lineEl = document.getElementById("priceLine");
    const len = lineEl.getTotalLength();
    lineEl.style.strokeDasharray = String(len);
    lineEl.style.strokeDashoffset = String(len);
    lineEl.getBoundingClientRect();
    lineEl.style.transition = "stroke-dashoffset .9s ease-out";
    requestAnimationFrame(() => { lineEl.style.strokeDashoffset = "0"; });
  }

  async function load(symbol) {
    metaEl.textContent = "Yüklənir…";
    try {
      const res = await fetch(`/market/history/${symbol}`);
      const data = await res.json();
      draw(data.points);
      if (!data.points.length) {
        metaEl.textContent = "Qiymət tarixçəsi hazırda əlçatan deyil.";
        return;
      }
      const first = data.points[0].close;
      const last = data.points[data.points.length - 1].close;
      const change = last - first;
      const changePct = first ? (change / first) * 100 : 0;
      const sign = change >= 0 ? "+" : "";
      metaEl.innerHTML =
        `<span>${symbol}</span>` +
        `<span>Son qiymət <b>${last}</b></span>` +
        `<span class="${change >= 0 ? "buy" : "sell"}">${sign}${change.toFixed(5)} (${sign}${changePct.toFixed(2)}%)</span>` +
        `<span>${data.points.length} gün, ECB/Frankfurter</span>`;
    } catch (err) {
      metaEl.textContent = "Qrafik yüklənərkən xəta baş verdi.";
    }
  }

  symbolEl.addEventListener("change", () => load(symbolEl.value));
  load(symbolEl.value);
  setInterval(() => load(symbolEl.value), 5 * 60 * 1000);
})();
