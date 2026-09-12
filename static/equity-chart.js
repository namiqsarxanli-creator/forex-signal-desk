(function () {
  const svg = document.getElementById("equitySvg");
  const metaEl = document.getElementById("equityMeta");
  if (!svg) return;

  function draw(points) {
    const w = 600, h = 200, pad = 12;
    const balances = points.map((p) => p.balance);
    const min = Math.min(...balances);
    const max = Math.max(...balances);
    const range = max - min || 1;
    const stepX = points.length > 1 ? (w - pad * 2) / (points.length - 1) : 0;

    const coords = points.map((p, i) => {
      const x = points.length > 1 ? pad + i * stepX : w / 2;
      const y = h - pad - ((p.balance - min) / range) * (h - pad * 2);
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
        <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.35"></stop>
          <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"></stop>
        </linearGradient>
      </defs>
      <path d="${areaPath}" fill="url(#eqGrad)" stroke="none"></path>
      <path id="eqLine" d="${linePath}" fill="none" stroke="var(--accent)" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round"></path>
    `;

    const lineEl = document.getElementById("eqLine");
    const len = lineEl.getTotalLength();
    lineEl.style.strokeDasharray = String(len);
    lineEl.style.strokeDashoffset = String(len);
    lineEl.getBoundingClientRect();
    lineEl.style.transition = "stroke-dashoffset 1.1s ease-out";
    requestAnimationFrame(() => { lineEl.style.strokeDashoffset = "0"; });
  }

  async function load() {
    try {
      const res = await fetch("/equity/history");
      const data = await res.json();
      draw(data.points);
      const pnl = data.current_balance - data.starting_balance;
      const pnlPct = data.starting_balance ? (pnl / data.starting_balance) * 100 : 0;
      const sign = pnl >= 0 ? "+" : "";
      metaEl.innerHTML =
        `<span>Cari balans <b>$${data.current_balance.toLocaleString()}</b></span>` +
        `<span class="${pnl >= 0 ? "buy" : "sell"}">${sign}${pnl.toFixed(2)} (${sign}${pnlPct.toFixed(2)}%)</span>` +
        `<span>${data.trade_count} bağlanmış PAPER trade</span>`;
    } catch (err) {
      metaEl.innerHTML = '<span class="empty">Equity məlumatı yüklənə bilmədi.</span>';
    }
  }

  load();
  setInterval(load, 60000);
  window.addEventListener("equity:refresh", load);
})();
