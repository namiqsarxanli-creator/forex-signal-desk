(function () {
  const liveDot = document.getElementById("liveDot");
  const openCard = document.querySelector('[data-live="open_positions"]');
  const signalsCard = document.querySelector('[data-live="signals_today"]');
  const rsiBody = document.querySelector("#rsiTable tbody");
  const recentBody = document.getElementById("recentSignalsBody");
  const closedBody = document.getElementById("closedTradesBody");
  if (!liveDot) return;

  function actionBadge(action) {
    if (action === "BUY") return '<span class="pill buy-pill">BUY</span>';
    if (action === "SELL") return '<span class="pill sell-pill">SELL</span>';
    return '<span class="pill neutral-pill">—</span>';
  }

  function bump(el) {
    if (!el) return;
    el.classList.remove("bump");
    void el.offsetWidth; // restart animation
    el.classList.add("bump");
  }

  function updateRsiTable(readings) {
    if (!rsiBody || !readings || !readings.length) return;
    rsiBody.innerHTML = readings
      .map((r) => {
        const rsi = r.rsi === null || r.rsi === undefined ? "—" : r.rsi.toFixed(1);
        const price = r.last_price ? r.last_price.toFixed(5) : "—";
        return `<tr><td>${r.symbol}</td><td>${price}</td><td>${rsi}</td><td>${actionBadge(r.action)}</td></tr>`;
      })
      .join("");
  }

  function updateClosedTrades(trades) {
    if (!closedBody || !trades || !trades.length) return;
    closedBody.innerHTML = trades
      .map((t) => {
        const sign = t.profit_loss >= 0 ? "+" : "";
        return (
          `<tr><td>${t.symbol}</td><td>${t.exit_price}</td>` +
          `<td class="${t.profit_loss >= 0 ? "buy" : "sell"}">${sign}${t.profit_loss.toFixed(2)}</td>` +
          `<td>${t.closed_at}</td></tr>`
        );
      })
      .join("");
  }

  function updateRecentSignals(signals) {
    if (!recentBody) return;
    if (!signals || !signals.length) {
      recentBody.innerHTML = '<tr><td colspan="4" class="empty">Hələ siqnal qəbul edilməyib.</td></tr>';
      return;
    }
    recentBody.innerHTML = signals
      .map(
        (s) =>
          `<tr><td>${s.symbol}</td><td class="${(s.action || "").toLowerCase()}">${s.action}</td>` +
          `<td>${s.source}</td><td>${s.confidence ?? "-"}</td></tr>`
      )
      .join("");
  }

  function handleTick(data) {
    if (openCard) {
      const strong = openCard.querySelector("strong");
      if (strong && strong.textContent !== String(data.open_positions)) {
        strong.textContent = data.open_positions;
        bump(openCard);
      }
    }
    if (signalsCard) {
      const strong = signalsCard.querySelector("strong");
      if (strong && strong.textContent !== String(data.signals_today)) {
        strong.textContent = data.signals_today;
        bump(signalsCard);
      }
    }
    updateRsiTable(data.rsi_readings);
    updateRecentSignals(data.recent_signals);
    updateClosedTrades(data.closed_trades);
  }

  let retryDelay = 2000;

  function connect() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${location.host}/ws/live`);

    ws.onopen = () => {
      liveDot.classList.add("on");
      retryDelay = 2000;
    };
    ws.onclose = () => {
      liveDot.classList.remove("on");
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 1.5, 20000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.type === "tick") {
          handleTick(data);
        } else if (data.type === "signal_fired") {
          const dirWord = data.action === "BUY" ? "AL (BUY)" : "SAT (SELL)";
          if (window.showToast) {
            const volText = data.volume ? `${data.volume} lot @ ${data.entry_price}` : `@ ${data.entry_price}`;
            window.showToast(`${data.symbol} ${dirWord}`, `Yeni siqnal icra olundu — ${volText}`, data.action === "BUY" ? "buy" : "sell");
          }
          if (window.playDing) window.playDing();
        } else if (data.type === "trade_closed") {
          const profit = data.profit_loss;
          const sign = profit >= 0 ? "+" : "";
          if (window.showToast) {
            window.showToast(`${data.symbol} bağlandı`, `Nəticə: ${sign}${profit.toFixed(2)} USD`, profit >= 0 ? "buy" : "sell");
          }
          window.dispatchEvent(new CustomEvent("equity:refresh"));
        }
      } catch (err) {
        /* ignore malformed frame */
      }
    };
  }

  connect();
})();
