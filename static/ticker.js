(function () {
  const track = document.getElementById("tickerTrack");
  if (!track) return;

  const PAIRS = [
    { base: "EUR", quote: "USD", label: "EUR/USD" },
    { base: "GBP", quote: "USD", label: "GBP/USD" },
    { base: "USD", quote: "JPY", label: "USD/JPY" },
  ];

  function render(items) {
    const html = items
      .map(
        (item) =>
          `<span class="ticker-item"><b>${item.label}</b> ${item.value}` +
          `<i class="${item.dir}">${item.dir === "up" ? "▲" : "▼"}</i></span>`
      )
      .join("");
    track.innerHTML = html + html; // duplicate for seamless CSS loop
  }

  async function fetchRates() {
    try {
      const res = await fetch("https://api.frankfurter.app/latest?from=EUR&to=USD,GBP,JPY", {
        cache: "no-store",
      });
      if (!res.ok) throw new Error("rate fetch failed");
      const data = await res.json();
      const eurUsd = data.rates.USD;
      const eurGbp = data.rates.GBP;
      const eurJpy = data.rates.JPY;

      const gbpUsd = eurUsd / eurGbp;
      const usdJpy = eurJpy / eurUsd;

      const previous = window.__lastRates || {};
      const items = [
        { label: "EUR/USD", value: eurUsd.toFixed(4), dir: eurUsd >= (previous.eurUsd ?? eurUsd) ? "up" : "down" },
        { label: "GBP/USD", value: gbpUsd.toFixed(4), dir: gbpUsd >= (previous.gbpUsd ?? gbpUsd) ? "up" : "down" },
        { label: "USD/JPY", value: usdJpy.toFixed(3), dir: usdJpy >= (previous.usdJpy ?? usdJpy) ? "up" : "down" },
      ];
      window.__lastRates = { eurUsd, gbpUsd, usdJpy };
      render(items);
    } catch (err) {
      track.innerHTML =
        '<span class="ticker-item">FX kursları hazırda əlçatan deyil (internet bağlantısını yoxlayın)</span>';
    }
  }

  fetchRates();
  setInterval(fetchRates, 60000);
})();
