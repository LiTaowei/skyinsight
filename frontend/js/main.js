/* 骨架引导：健康状态 + 城市下拉填充；图表在动作 7-9 逐个接通 */
async function initHealth() {
  try {
    const h = await api("/api/health");
    $("#healthDot").classList.add(h.db ? "ok" : "bad");
    $("#healthText").textContent = h.db ? "数据库已连接" : "数据库断开";
  } catch (e) {
    $("#healthDot").classList.add("bad");
    $("#healthText").textContent = "后端未连接";
  }
}

async function initCities() {
  const cities = await api("/api/cities");
  const sel = $("#citySelect");
  for (const c of cities) sel.add(new Option(c.city, c.city));
  $(".filters .hint").textContent = `已加载 ${cities.length} 个城市 · 全部图表联动已启用`;
}

initHealth();
initCities().catch((e) => {
  $(".filters .hint").textContent = "城市列表加载失败：" + e.message;
});
