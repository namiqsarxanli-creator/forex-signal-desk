(function () {
  const toggleBtn = document.getElementById("chatToggle");
  const panel = document.getElementById("chatPanel");
  const closeBtn = document.getElementById("chatClose");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSend");
  const messagesEl = document.getElementById("chatMessages");
  if (!toggleBtn) return;

  const history = [];

  function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function openPanel() {
    panel.classList.add("open");
    if (!messagesEl.children.length) {
      addMessage("bot", "Salam! Mən Forex Trading Bot-un AI köməkçisiyəm. Sayt, strategiya və PAPER mövqələriniz haqqında sual verə bilərsiniz.");
    }
    input.focus();
  }

  toggleBtn.addEventListener("click", () => {
    panel.classList.contains("open") ? panel.classList.remove("open") : openPanel();
  });
  closeBtn.addEventListener("click", () => panel.classList.remove("open"));

  form.addEventListener("submit", async (evt) => {
    evt.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    addMessage("user", text);
    history.push({ role: "user", content: text });
    input.value = "";
    sendBtn.disabled = true;

    const typingEl = addMessage("bot typing", "yazır…");

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: history.slice(0, -1) }),
      });
      const data = await res.json();
      typingEl.remove();
      const reply = data.reply || "Cavab alına bilmədi.";
      addMessage("bot", reply);
      history.push({ role: "assistant", content: reply });
    } catch (err) {
      typingEl.remove();
      addMessage("bot", "Xəta baş verdi, bir az sonra yenidən cəhd edin.");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  });
})();
