/* 统计图表区（动作 7）：6 张图接 /api/stats/*，联动城市/年份筛选器 */

let AQI_LEVELS = [];

/* 按 AQI 值取官方等级色 */
function levelColor(v) {
  const lv = AQI_LEVELS.find((l) => v >= l.lower && v <= l.upper);
  return lv ? lv.color : "#2563eb";
}

/* ① 四季 PM2.5 / O3 / AQI 均值：双柱 + 折线，随城市/年份联动 */
async function renderSeasonal() {
  const city = $("#citySelect").value;
  const year = $("#yearSelect").value;
  const rows = await api("/api/stats/seasonal", { city, year });
  const order = ["春季", "夏季", "秋季", "冬季"];
  rows.sort((a, b) => order.indexOf(a.season) - order.indexOf(b.season));
  const scope = [city || "20 城均值", year ? year + " 年" : "全期"].join(" · ");
  makeChart("chart-seasonal").setOption({
    title: { text: scope, left: "center", textStyle: { fontSize: 12, color: "#6b7280" } },
    tooltip: { trigger: "axis" },
    legend: { top: 0 },
    grid: { left: 55, right: 50, top: 40, bottom: 25 },
    xAxis: { type: "category", data: rows.map((r) => r.season) },
    yAxis: [
      { type: "value", name: "μg/m³" },
      { type: "value", name: "AQI" }
    ],
    series: [
      { name: "PM2.5", type: "bar", barMaxWidth: 26, data: rows.map((r) => r.avg_pm25), itemStyle: { color: "#f97316" } },
      { name: "O3", type: "bar", barMaxWidth: 26, data: rows.map((r) => r.avg_o3), itemStyle: { color: "#06b6d4" } },
      { name: "AQI", type: "line", yAxisIndex: 1, data: rows.map((r) => r.avg_aqi), itemStyle: { color: "#2563eb" } }
    ]
  });
}

/* ② 24 小时昼夜曲线：3 条平滑折线，随城市/年份/季节联动 */
async function renderHourly() {
  const city = $("#citySelect").value;
  const year = $("#yearSelect").value;
  const season = $("#batchSelect").value;
  const rows = await api("/api/stats/hourly", { city, year, season: season === "all" ? "" : season });
  const seasonName = { winter: "冬季", summer: "夏季" }[season] || "";
  const scope = [city || "20 城均值", year ? year + " 年" : "全期", seasonName].filter(Boolean).join(" · ");
  makeChart("chart-hourly").setOption({
    title: { text: scope, left: "center", textStyle: { fontSize: 12, color: "#6b7280" } },
    tooltip: { trigger: "axis" },
    legend: { top: 18 },
    grid: { left: 55, right: 50, top: 60, bottom: 25 },
    xAxis: { type: "category", data: rows.map((r) => r.hour + "时") },
    yAxis: [
      { type: "value", name: "μg/m³" },
      { type: "value", name: "AQI" }
    ],
    series: [
      { name: "PM2.5", type: "line", smooth: true, showSymbol: false, data: rows.map((r) => r.avg_pm25), itemStyle: { color: "#f97316" } },
      { name: "O3", type: "line", smooth: true, showSymbol: false, data: rows.map((r) => r.avg_o3), itemStyle: { color: "#06b6d4" } },
      { name: "AQI", type: "line", smooth: true, yAxisIndex: 1, showSymbol: false, data: rows.map((r) => r.avg_aqi), itemStyle: { color: "#2563eb" } }
    ]
  });
}

/* ③ 城市 AQI 排行榜：横向条形（按 AQI 等级官方色着色），随年份联动 */
async function renderRanking() {
  const year = $("#yearSelect").value;
  const rows = await api("/api/stats/ranking", { year });
  rows.sort((a, b) => a.avg_aqi - b.avg_aqi); /* 升序 → 最高值显示在最顶部 */
  makeChart("chart-ranking").setOption({
    title: { text: year ? `${year} 年` : "全期 2022-2024", left: "center", textStyle: { fontSize: 12, color: "#6b7280" } },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 70, right: 55, top: 35, bottom: 25 },
    xAxis: { type: "value", name: "AQI 均值" },
    yAxis: { type: "category", data: rows.map((r) => r.city) },
    series: [{
      type: "bar", barMaxWidth: 14,
      data: rows.map((r) => ({ value: r.avg_aqi, itemStyle: { color: levelColor(r.avg_aqi) } })),
      label: { show: true, position: "right", fontSize: 11, color: "#6b7280" }
    }]
  });
}

/* ④ 多城市月度走势：卡片内城市多选（默认北方 4 城），与全局城市筛选解耦 */
let MONTHLY_CITIES = ["北京", "天津", "济南", "郑州"];
const MONTHLY_DEFAULT = [...MONTHLY_CITIES];

async function renderMonthly() {
  const cities = MONTHLY_CITIES;
  const chart = makeChart("chart-monthly");
  $("#monthlyPickerCount").textContent = cities.length;
  if (!cities.length) {
    chart.clear();
    chart.setOption({
      title: { text: "请先勾选城市", left: "center", top: "middle", textStyle: { fontSize: 13, color: "#9ca3af" } }
    });
    return;
  }
  const rows = await api("/api/stats/monthly", { cities: cities.join(",") });
  const yms = [...new Set(rows.map((r) => r.ym))].sort();
  const cityNames = [...new Set(rows.map((r) => r.city))];
  const colors = ["#2563eb", "#dc2626", "#16a34a", "#f97316", "#8b5cf6", "#0d9488", "#d946ef", "#64748b"];
  chart.setOption({
    title: {
      text: cityNames.length <= 5 ? cityNames.join(" · ") : `${cityNames.length} 城对比`,
      left: "center", textStyle: { fontSize: 12, color: "#6b7280" }
    },
    tooltip: { trigger: "axis" },
    legend: { top: 18, type: "scroll" },
    grid: { left: 50, right: 25, top: 60, bottom: 45 },
    xAxis: { type: "category", data: yms, axisLabel: { interval: 5, rotate: 30 } },
    yAxis: { type: "value", name: "AQI 均值" },
    series: cityNames.map((cn, i) => ({
      name: cn, type: "line", smooth: true, showSymbol: false,
      itemStyle: { color: colors[i % colors.length] },
      data: yms.map((ym) => {
        const hit = rows.find((x) => x.ym === ym && x.city === cn);
        return hit ? hit.avg_aqi : null;
      })
    }))
  });
}

/* 月度卡城市多选面板：拉城市清单 → 勾选联动 → 快捷按钮 */
async function initMonthlyPicker() {
  try {
    const cities = await api("/api/cities");
    $("#monthlyPickerList").innerHTML = cities.map((c) =>
      `<label class="picker-item"><input type="checkbox" value="${c.city}">${c.city}</label>`).join("");
    syncMonthlyChecked();
    $("#monthlyPickerList").addEventListener("change", () => {
      MONTHLY_CITIES = [...document.querySelectorAll("#monthlyPickerList input:checked")].map((cb) => cb.value);
      renderMonthly().catch((e) => console.error(e));
    });
  } catch (e) { console.error("initMonthlyPicker", e); }
}

function syncMonthlyChecked() {
  document.querySelectorAll("#monthlyPickerList input[type=checkbox]").forEach((cb) => {
    cb.checked = MONTHLY_CITIES.includes(cb.value);
  });
}

function bindMonthlyPicker() {
  const panel = $("#monthlyPickerPanel");
  $("#monthlyPickerBtn").addEventListener("click", () => { panel.hidden = !panel.hidden; });
  document.addEventListener("click", (e) => {
    if (!panel.hidden && !$("#monthlyPicker").contains(e.target)) panel.hidden = true;
  });
  panel.querySelectorAll("[data-quick]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const q = btn.dataset.quick;
      if (q === "all") MONTHLY_CITIES = [...document.querySelectorAll("#monthlyPickerList input")].map((cb) => cb.value);
      else MONTHLY_CITIES = [];
      syncMonthlyChecked();
      renderMonthly().catch((e) => console.error(e));
    });
  });
}

/* ⑤ 逐年优良天数：城市×日均 AQI 判定，柱 = 优良/超标天数，线 = 优良率，仅随城市联动 */
async function renderGoodDays() {
  const city = $("#citySelect").value;
  const rows = await api("/api/stats/good-days", { city });
  rows.sort((a, b) => a.yr - b.yr);
  makeChart("chart-good-days").setOption({
    title: {
      text: city || "20 城年均",
      left: "center", textStyle: { fontSize: 12, color: "#6b7280" }
    },
    tooltip: { trigger: "axis", valueFormatter: (v) => v + " 天" },
    legend: { top: 0 },
    grid: { left: 60, right: 55, top: 60, bottom: 25 },
    xAxis: { type: "category", data: rows.map((r) => r.yr + "年") },
    yAxis: [
      { type: "value", name: "天数", minInterval: 1 },
      { type: "value", name: "优良率 %", max: 100 }
    ],
    series: [
      { name: "优良", type: "bar", stack: "t", barMaxWidth: 40, data: rows.map((r) => r.good_days), itemStyle: { color: "#16a34a" } },
      { name: "超标", type: "bar", stack: "t", barMaxWidth: 40, data: rows.map((r) => (r.total_days - r.good_days).toFixed(1)), itemStyle: { color: "#ef4444" } },
      { name: "优良率", type: "line", yAxisIndex: 1, data: rows.map((r) => r.good_ratio_pct), itemStyle: { color: "#2563eb" }, label: { show: true, formatter: "{c}%", fontSize: 11, color: "#2563eb" } }
    ]
  });
}

/* ⑥ 首要污染物频次：环形图，随城市/年份/季节联动 */
async function renderPP() {
  const city = $("#citySelect").value;
  const year = $("#yearSelect").value;
  const season = $("#batchSelect").value;
  const rows = await api("/api/stats/primary-pollutant", { city, year, season: season === "all" ? "" : season });
  const seasonName = { winter: "冬季", summer: "夏季" }[season] || "";
  const scope = [city || "20 城合计", year ? year + " 年" : "全期", seasonName].filter(Boolean).join(" · ");
  const colors = { "PM2.5": "#f97316", "PM10": "#eab308", "NO2": "#8b5cf6", "O3": "#06b6d4", "SO2": "#64748b", "CO": "#94a3b8" };
  makeChart("chart-pp").setOption({
    title: { text: scope, left: "center", textStyle: { fontSize: 12, color: "#6b7280" } },
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { orient: "vertical", right: 10, top: "center", textStyle: { fontSize: 12 } },
    series: [{
      type: "pie", radius: ["42%", "68%"], center: ["42%", "55%"],
      itemStyle: { borderColor: "#fff", borderWidth: 2 },
      label: { show: false },
      data: rows.map((r) => ({ name: r.pollutant, value: r.cnt, itemStyle: { color: colors[r.pollutant] || "#9ca3af" } }))
    }]
  });
}

/* 入口：拉等级色 → 渲染 6 图 → 绑筛选器联动 */
async function initStats() {
  try { AQI_LEVELS = await api("/api/meta/aqi-levels"); } catch (e) { /* 等级色失败不影响绘图 */ }
  bindMonthlyPicker();
  initMonthlyPicker();
  const jobs = [renderSeasonal, renderHourly, renderRanking, renderMonthly, renderGoodDays, renderPP];
  for (const fn of jobs) {
    try { await fn(); } catch (e) { console.error(fn.name, e); }
  }
  $("#citySelect").addEventListener("change", () => {
    renderSeasonal().catch((e) => console.error(e));
    renderHourly().catch((e) => console.error(e));
    renderGoodDays().catch((e) => console.error(e));
    renderPP().catch((e) => console.error(e));
  });
  $("#yearSelect").addEventListener("change", () => {
    renderSeasonal().catch((e) => console.error(e));
    renderRanking().catch((e) => console.error(e));
    renderHourly().catch((e) => console.error(e));
    renderPP().catch((e) => console.error(e));
  });
  $("#batchSelect").addEventListener("change", () => {
    renderHourly().catch((e) => console.error(e));
    renderPP().catch((e) => console.error(e));
  });
}

initStats();
