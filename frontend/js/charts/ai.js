/* AI 一问一答：为各卡片注入「AI 问答」按钮，展开卡片内迷你对话窗口
   首次打开自动请求开场解读；之后用户可连续追问，历史上下文随请求携带；
   后端每轮重新装配该卡真实数据（queries 层同源），模型只做洞察生成 */
(function () {
  "use strict";

  /* 图表容器 id → 后端卡片标识 */
  const CARD_MAP = {
    "chart-seasonal": "seasonal",
    "chart-hourly": "hourly",
    "chart-good-days": "gooddays",
    "chart-pp": "pp",
    "chart-monthly": "monthly",
    "chart-cluster": "cluster",
    "table-events": "anomaly",
  };

  const OPENING_QUESTION = "请结合数据对这张图表做整体解读";

  async function askAI(cardKey, question, history) {
    const body = {
      card: cardKey,
      question,
      history,
      city: $("#citySelect").value || null,
      year: $("#yearSelect").value ? Number($("#yearSelect").value) : null,
      season: $("#batchSelect").value || "all",
    };
    const res = await fetch("/api/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : `接口错误 ${res.status}`);
    return data.text;
  }

  function bubble(cls, text) {
    const div = document.createElement("div");
    div.className = `ai-msg ${cls}`;
    div.textContent = text;
    return div;
  }

  function setupCard(chartId, cardKey) {
    const el = document.getElementById(chartId);
    if (!el) return;
    const card = el.closest(".card");
    const h2 = card && card.querySelector("h2");
    if (!card || !h2) return;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ai-btn";
    btn.textContent = "AI 问答";
    h2.appendChild(btn);

    /* 对话面板：消息流 + 输入行 */
    const panel = document.createElement("div");
    panel.className = "ai-chat";
    panel.hidden = true;
    panel.innerHTML =
      '<div class="ai-msgs"></div>' +
      '<div class="ai-input"><input type="text" maxlength="500" placeholder="针对这张图提问，回车发送…">' +
      '<button type="button">发送</button></div>';
    h2.after(panel);

    const msgs = panel.querySelector(".ai-msgs");
    const input = panel.querySelector("input");
    const sendBtn = panel.querySelector(".ai-input button");
    const history = [];   /* 本卡对话上下文 {role, content} */
    let busy = false;
    let pending = null;   /* busy 期间的排队问题，加载完自动补发 */

    const scrollBottom = () => { msgs.scrollTop = msgs.scrollHeight; };

    async function runSend(question) {
      busy = true;
      sendBtn.disabled = true;
      const typing = bubble("ai-msg-ai", "思考中…");
      msgs.appendChild(typing);
      scrollBottom();
      try {
        const text = await askAI(cardKey, question, history);
        typing.textContent = text;
        history.push({ role: "user", content: question });
        history.push({ role: "assistant", content: text });
      } catch (e) {
        typing.textContent = `请求失败：${e.message}`;
        typing.classList.add("ai-msg-err");
      } finally {
        busy = false;
        sendBtn.disabled = false;
        scrollBottom();
        if (pending) { const q = pending; pending = null; runSend(q); }
      }
    }

    function send(question, showBubble) {
      if (showBubble) {
        msgs.appendChild(bubble("ai-msg-user", question));
        scrollBottom();
      }
      if (busy) { pending = question; return; }
      runSend(question);
    }

    btn.addEventListener("click", async () => {
      if (!panel.hidden) { panel.hidden = true; btn.classList.remove("active"); return; }
      panel.hidden = false;
      btn.classList.add("active");
      if (!history.length) await send(OPENING_QUESTION, false); /* 开场解读：不显示用户气泡 */
      input.focus();
    });

    function submit() {
      const q = input.value.trim();
      if (!q || busy) return;
      input.value = "";
      send(q, true);
    }
    sendBtn.addEventListener("click", submit);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
  }

  document.addEventListener("DOMContentLoaded", () => {
    for (const [id, key] of Object.entries(CARD_MAP)) setupCard(id, key);
  });
})();
