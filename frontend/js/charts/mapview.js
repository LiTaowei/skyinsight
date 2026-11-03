/* 地图与钻取区（动作 9）：全国 AQI 地图 + 城市时间序列钻取 */

let MAP_READY = false;
async function ensureMap() {
  if (MAP_READY) return;
  const res = await fetch("/js/china.json");
  if (!res.ok) throw new Error("china.json 加载失败 " + res.status);
  echarts.registerMap("china", await res.json());
  MAP_READY = true;
}

/* ① 全国 AQI 地图：等级官方色散点，点城市 → 联动钻取 */
async function renderMap() {
  await ensureMap();
  const d = await api("/api/map/aqi");
  const chart = makeChart("chart-map");
  chart.setOption({
    title: { text: `${d.date} ${String(d.hour).padStart(2, "0")}:00 · 圆点大小与颜色=AQI 等级`, left: "center", textStyle: { fontSize: 12, color: "#6b7280" } },
    tooltip: { formatter: (p) => `${p.data.name}<br>AQI ${p.value[2]}（${p.data.level}）<br>点击查看该城市趋势` },
    geo: {
      map: "china", roam: false, zoom: 1.18, top: 42, bottom: 8,
      itemStyle: { areaColor: "#eef2f7", borderColor: "#cbd5e1" },
      emphasis: { disabled: true }
    },
    series: [{
      type: "scatter", coordinateSystem: "geo", zlevel: 2,
      symbolSize: (v) => 8 + (Math.min(v[2], 300) / 300) * 14,
      label: { show: true, position: "right", formatter: (p) => p.data.name, fontSize: 10, color: "#374151" },
      data: d.points.map((p) => ({
        name: p.city, value: [p.lng, p.lat, p.aqi], level: p.level_name,
        itemStyle: { color: p.color, borderColor: "#374151", borderWidth: 1, opacity: 0.95 }
      }))
    }]
  });
  if (!chart.__mapBound) {
    chart.on("click", (p) => {
      if (p.data && p.data.name) {
        $("#citySelect").value = p.data.name;
        $("#citySelect").dispatchEvent(new Event("change"));
        /* 点击后滚到钻取卡并高亮，让联动效果可见 */
        const card = $("#chart-series").closest(".card");
        if (card) {
          card.scrollIntoView({ behavior: "smooth", block: "center" });
          card.classList.add("flash");
          setTimeout(() => card.classList.remove("flash"), 1800);
        }
      }
    });
    chart.__mapBound = true;
  }
}

/* ② 城市钻取：默认近 90 天日均，>31 天自动降采样已由后端处理 */
async function renderSeries() {
  const city = $("#citySelect").value || "北京";
  const d = await api(`/api/city/${encodeURIComponent(city)}/series`);
  const ts = d.points.map((p) =>
    p.hour === null || p.hour === undefined ? p.date : `${p.date} ${String(p.hour).padStart(2, "0")}:00`
  );
  const colors = { aqi: "#dc2626", pm25: "#f97316", pm10: "#eab308", no2: "#8b5cf6", so2: "#64748b", o3: "#06b6d4", co: "#94a3b8" };
  const gran = (d.granularity || "").indexOf("day") >= 0 ? "日均" : "逐小时";
  makeChart("chart-series").setOption({
    title: { text: `${d.city} · ${d.start} ~ ${d.end}（${gran}）`, left: "center", textStyle: { fontSize: 12, color: "#6b7280" } },
    tooltip: { trigger: "axis" },
    legend: { top: 18 },
    grid: { left: 50, right: 25, top: 55, bottom: 30 },
    xAxis: { type: "category", data: ts, axisLabel: { fontSize: 10, interval: Math.max(Math.ceil(ts.length / 8) - 1, 0) } },
    yAxis: { type: "value" },
    series: d.fields.map((f) => ({
      name: f.toUpperCase(), type: "line", smooth: true, showSymbol: false,
      itemStyle: { color: colors[f] || "#2563eb" },
      data: d.points.map((p) => p[f])
    }))
  });
}

function initMapview() {
  renderMap().catch((e) => chartError("chart-map", e.message));
  renderSeries().catch((e) => chartError("chart-series", e.message));
  $("#citySelect").addEventListener("change", () => renderSeries().catch(console.error));
}

initMapview();
