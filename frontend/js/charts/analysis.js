/* 算法结果区（动作 8）：聚类散点 / PCA载荷 / 簇雷达 / 异常时间线 / 事件表 */

const CLUSTER_COLORS = ["#dc2626", "#2563eb", "#16a34a"]; /* 按簇 id 着色 */

/* ① 城市聚类散点：PC1×PC2 投影，随批次联动 */
async function renderCluster() {
  const batch = $("#batchSelect").value || "all";
  const data = await api("/api/analysis/cluster", { batch });
  const groups = {};
  data.points.forEach((p) => (groups[p.cluster_id] = groups[p.cluster_id] || []).push(p));
  const names = { all: "全期", winter: "冬季", summer: "夏季" };
  makeChart("chart-cluster").setOption({
    title: { text: names[batch] + "批次 · 前 2 主成分投影", left: "center", textStyle: { fontSize: 12, color: "#6b7280" } },
    tooltip: { formatter: (p) => `${p.data.cityName}<br>PC1=${p.value[0].toFixed(2)}　PC2=${p.value[1].toFixed(2)}` },
    legend: { top: 18, textStyle: { fontSize: 11 } },
    grid: { left: 55, right: 25, top: 60, bottom: 50 },
    xAxis: { name: "PC1 燃煤/机动车强度", nameLocation: "middle", nameGap: 28, nameFontSize: 11 },
    yAxis: { name: "PC2 臭氧对比轴", nameGap: 40, nameFontSize: 11 },
    series: Object.keys(groups).map((cid) => ({
      name: groups[cid][0].cluster_label,
      type: "scatter", symbolSize: 18,
      itemStyle: { color: CLUSTER_COLORS[cid % 3], opacity: 0.85 },
      label: { show: true, position: "top", formatter: (p) => p.data.cityName, fontSize: 10, color: "#374151" },
      data: groups[cid].map((p) => ({ value: [p.pc1, p.pc2], cityName: p.city }))
    }))
  });
}

/* ② PCA 载荷条形图：15 指标 × PC1/PC2，按 |PC1| 排序 */
async function renderLoadings() {
  const d = await api("/api/analysis/pca-loadings");
  const rows = d.loadings.slice().sort((a, b) => Math.abs(b.pc1) - Math.abs(a.pc1));
  const pct = d.explained_variance_ratio.map((x) => (x * 100).toFixed(1));
  makeChart("chart-loadings").setOption({
    title: { text: `PC1 贡献 ${pct[0]}% · PC2 贡献 ${pct[1]}% · 累计 ${(d.cumulative_variance_ratio[1] * 100).toFixed(1)}%`, left: "center", textStyle: { fontSize: 12, color: "#6b7280" } },
    tooltip: { trigger: "axis" },
    legend: { top: 18 },
    grid: { left: 95, right: 30, top: 55, bottom: 25 },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: rows.map((r) => r.measure), axisLabel: { fontSize: 10 } },
    series: [
      { name: "PC1", type: "bar", barMaxWidth: 10, data: rows.map((r) => r.pc1), itemStyle: { color: "#2563eb" } },
      { name: "PC2", type: "bar", barMaxWidth: 10, data: rows.map((r) => r.pc2), itemStyle: { color: "#06b6d4" } }
    ]
  });
}

/* ③ 簇画像雷达：三类城市六指标 min-max 归一后对比，随批次联动 */
async function renderRadar() {
  const batch = $("#batchSelect").value || "all";
  const data = await api("/api/analysis/cluster", { batch });
  const cs = data.centers;
  const dims = [["aqi", "AQI"], ["pm25", "PM2.5"], ["pm10", "PM10"], ["so2", "SO2"], ["no2", "NO2"], ["o3", "O3"]];
  const norm = cs.map(() => ({}));
  dims.forEach(([k]) => {
    const vs = cs.map((c) => Number(c[k]) || 0);
    const min = Math.min(...vs), max = Math.max(...vs);
    cs.forEach((c, i) => (norm[i][k] = max > min ? (vs[i] - min) / (max - min) : 0.5));
  });
  makeChart("chart-radar").setOption({
    tooltip: {},
    legend: { top: 0, textStyle: { fontSize: 11 } },
    radar: { indicator: dims.map((d) => ({ name: d[1], max: 1 })), radius: "60%", center: ["50%", "58%"], axisName: { fontSize: 11 } },
    series: [{
      type: "radar",
      data: cs.map((c, i) => ({
        name: c.cluster_label,
        value: dims.map(([k]) => +norm[i][k].toFixed(3)),
        itemStyle: { color: CLUSTER_COLORS[c.cluster_id % 3] },
        areaStyle: { opacity: 0.12 }
      }))
    }]
  });
}

/* ④ 异常分数时间线：24h 分数折线 + AQI 柱（异常时刻染红），随城市/日期联动 */
async function renderTimeline() {
  const city = $("#citySelect").value || "北京";
  const date = $("#tlDate").value || "";
  const d = await api(`/api/analysis/anomaly/timeline/${encodeURIComponent(city)}`, date ? { date } : {});
  const pts = d.points;
  makeChart("chart-timeline").setOption({
    title: { text: `${d.city} · ${d.date}（红色柱 = 模型判定异常）`, left: "center", textStyle: { fontSize: 12, color: "#6b7280" } },
    tooltip: { trigger: "axis" },
    legend: { top: 18 },
    grid: { left: 55, right: 50, top: 55, bottom: 25 },
    xAxis: { type: "category", data: pts.map((p) => p.hour + "时") },
    yAxis: [
      { type: "value", name: "异常分数" },
      { type: "value", name: "AQI" }
    ],
    series: [
      { name: "异常分数", type: "line", showSymbol: false, data: pts.map((p) => +Number(p.score).toFixed(3)), itemStyle: { color: "#8b5cf6" }, lineStyle: { color: "#8b5cf6" } },
      {
        name: "AQI", type: "bar", yAxisIndex: 1, barMaxWidth: 12,
        data: pts.map((p) => ({ value: p.aqi, isAnomaly: p.is_anomaly === 1 })),
        itemStyle: { color: (pr) => (pr.data && pr.data.isAnomaly ? "#dc2626" : "#cbd5e1") }
      }
    ]
  });
}

/* ⑤ 异常事件表：全量缓存（分页拉取）→ TOP50 按时长 / 全部分页两种视图，随城市/≥6h 联动 */
let EVT_ALL = null; /* 全库事件缓存，离线静态数据只需拉一次 */
const EVT_PAGE_SIZE = 20;
let evtPage = 0;

async function fetchAllEvents() {
  const PAGE = 100;
  const items = await api("/api/analysis/anomaly/events", { limit: PAGE, offset: 0 }).then((d) => d.items || []);
  while (true) { /* 整库共 243 条，100 条一页循环拉全 */
    const more = await api("/api/analysis/anomaly/events", { limit: PAGE, offset: items.length }).then((d) => d.items || []);
    if (!more.length) break;
    items.push(...more);
    if (more.length < PAGE) break;
  }
  return items;
}

async function renderEvents() {
  if (!EVT_ALL) {
    EVT_ALL = await fetchAllEvents();
    $("#evtTotal").textContent = EVT_ALL.length;
  }
  const city = $("#citySelect").value;
  const min = $("#evtMin6").checked ? 6 : 0;
  let items = EVT_ALL;
  if (city) items = items.filter((x) => x.city === city);
  if (min) items = items.filter((x) => Number(x.duration_hours) >= min);

  const view = $("#evtView").value;
  const pager = $("#evtPager");
  if (view === "top") {
    pager.hidden = true;
    items = items.slice().sort((a, b) => b.duration_hours - a.duration_hours).slice(0, 50);
  } else {
    pager.hidden = false;
    items = items.slice().sort((a, b) => (a.start_time < b.start_time ? 1 : -1));
    const pages = Math.max(1, Math.ceil(items.length / EVT_PAGE_SIZE));
    evtPage = Math.min(evtPage, pages - 1);
    items = items.slice(evtPage * EVT_PAGE_SIZE, (evtPage + 1) * EVT_PAGE_SIZE);
    $("#evtPageInfo").textContent = `${evtPage + 1} / ${pages}`;
    $("#evtPrev").disabled = evtPage === 0;
    $("#evtNext").disabled = evtPage >= pages - 1;
  }

  const f = (s) => (s || "").replace("T", " ").slice(0, 16);
  const keep = ["aqi", "pm25", "pm10", "no2", "so2", "co", "o3"];
  const topAttr = (it) => {
    const z = it.attribution && it.attribution.zscores;
    if (!z) return "-";
    return Object.entries(z)
      .filter(([k]) => keep.includes(k))
      .sort((a, b) => b[1] - a[1]).slice(0, 2)
      .map(([k, v]) => `${k.toUpperCase()} +${Number(v).toFixed(1)}σ`)
      .join(" / ");
  };
  $("#table-events").innerHTML =
    `<table><thead><tr><th>城市</th><th>开始</th><th>结束</th><th>时长h</th><th>峰值AQI</th><th>主控</th><th>归因（偏离σ）</th></tr></thead><tbody>` +
    (items.map((it) =>
      `<tr><td>${it.city}</td><td>${f(it.start_time)}</td><td>${f(it.end_time)}</td><td>${it.duration_hours}</td><td>${it.peak_aqi}</td><td>${(it.main_pollutant || "").toUpperCase()}</td><td>${topAttr(it)}</td></tr>`
    ).join("") || `<tr><td colspan="7"><div class="empty-tip">无匹配事件</div></td></tr>`) +
    `</tbody></table>`;
  try {
    const s = await api("/api/analysis/anomaly/summary");
    $("#evtKpis").innerHTML =
      [`事件总数 ${s.total}`, `平均时长 ${s.avg_duration}h`, `最长 ${s.max_duration}h`, `平均峰值AQI ${s.avg_peak_aqi}`]
        .map((t) => `<span>${t}</span>`).join("");
  } catch (e) { /* KPI 失败不影响表格 */ }
}

function initAnalysis() {
  const safe = (fn, id) => fn().catch((e) => (id ? chartError(id, e.message) : console.error(e)));
  safe(renderCluster, "chart-cluster");
  safe(renderLoadings, "chart-loadings");
  safe(renderRadar, "chart-radar");
  safe(renderTimeline, "chart-timeline");
  safe(renderEvents);
  $("#batchSelect").addEventListener("change", () => { safe(renderCluster, "chart-cluster"); safe(renderRadar, "chart-radar"); });
  $("#citySelect").addEventListener("change", () => { safe(renderTimeline, "chart-timeline"); safe(renderEvents); });
  $("#tlDate").addEventListener("change", () => safe(renderTimeline, "chart-timeline"));
  $("#evtMin6").addEventListener("change", () => { evtPage = 0; safe(renderEvents); });
  $("#evtView").addEventListener("change", () => { evtPage = 0; safe(renderEvents); });
  $("#evtPrev").addEventListener("click", () => { if (evtPage > 0) { evtPage--; safe(renderEvents); } });
  $("#evtNext").addEventListener("click", () => { evtPage++; safe(renderEvents); });
}

initAnalysis();
