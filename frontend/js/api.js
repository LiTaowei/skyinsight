/* 统一接口封装：fetch + 查询串拼装 + 错误抛出 */
async function api(path, params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== "" && v !== null && v !== undefined) qs.set(k, v);
  }
  const q = qs.toString();
  const res = await fetch(path + (q ? "?" + q : ""));
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

/* 便捷取 DOM */
const $ = (sel) => document.querySelector(sel);

/* ECharts 公共初始化：按容器 id 建图并自适应宽度（实例缓存，重复调用返回同一实例） */
const _charts = {};
function makeChart(id) {
  if (_charts[id]) {
    _charts[id].clear();
    return _charts[id];
  }
  const el = document.getElementById(id);
  const chart = echarts.init(el);
  window.addEventListener("resize", () => chart.resize());
  _charts[id] = chart;
  return chart;
}

/* 容器内错误提示 */
function chartError(id, msg) {
  document.getElementById(id).innerHTML = `<div class="empty-tip">加载失败：${msg}</div>`;
}
