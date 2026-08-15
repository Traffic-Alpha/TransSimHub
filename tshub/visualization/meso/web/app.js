/*
 * @Author: WANG Maonan
 * @Date: 2026-08-11 10:00:00
 * @Description: 中观大屏前端. 手写 Canvas 渲染路网 —— SUMO 的坐标是笛卡尔米制而不是经纬度,
 *   用不上地图库; 也因此整个大屏不依赖任何外部 JS 库。
 * @LastEditTime: 2026-08-11 10:00:00
 */
'use strict';

// 拥堵配色: 直接用 Google Maps 交通图层的四档配色 (停滞/缓行/较慢/畅通).
// 浅色底图上只有这一组饱和色, 视线自然落在数据上
const RAMP = ['#811f1f', '#f23c32', '#ff974d', '#63d668'];
function congestionColor(v) {
  if (v < 0.25) return RAMP[0];
  if (v < 0.50) return RAMP[1];
  if (v < 0.75) return RAMP[2];
  return RAMP[3];
}

// 底图配色. Google 并不公开其默认样式的色值, 这里是按 Google Maps 的观感调的一组近似色:
// 关键是层次 —— 陆地最浅, 地物只做极轻微的区分, 道路是最亮的白色, 全图只有拥堵色带是饱和的。
const MAP_STYLE = {
  land: '#f5f3ef',          // 陆地: 极浅的暖灰
  water: '#aad3f0',         // 水系
  park: '#c9e8b2',          // 公园 / 绿地
  forest: '#b4dda0',        // 树林 (比公园略深)
  farm: '#f0eddc',          // 农田 / 裸地
  residential: '#f0eeea',   // 住宅用地: 几乎与陆地同色, 只是隐约可辨
  commercial: '#f3ece5',    // 商业 / 工业用地
  institution: '#f0e6dc',   // 学校 / 医疗等公共设施 (淡褐)
  parking: '#eceae5',       // 停车场
  building: '#e6e2db',      // 建筑物本体
  buildingLine: '#dbd6cd',
  road: '#ffffff',          // 路面: 全图最亮, 这是 Google Maps 观感的关键
  roadCasing: '#d9d4ca',    // 路缘描边
};

// 底图的绘制顺序 (先大面积的用地, 后小面积的建筑), 与 payload 的 kind 对应
const BASEMAP_ORDER = ['water', 'farm', 'residential', 'commercial', 'institution',
                       'parking', 'forest', 'park', 'building'];

const state = {
  static: null,
  frame: null,
  granularity: 'edge',
  view: { scale: 1, tx: 0, ty: 0 },   // 世界坐标 -> 屏幕
  trend: [],                          // 全网拥堵指数的历史
  imageNames: '',                     // 当前回传图像的集合, 变了才重建 DOM
  zoomedImage: null,                  // 正在全屏查看的图像名 (null 表示未打开)
};

const canvas = document.getElementById('map');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');

// ---------------- 坐标变换 ---------------- //
function fitView() {
  if (!state.static) return;
  const [xmin, ymin, xmax, ymax] = state.static.bbox;
  const pad = 24;
  const w = canvas.width, h = canvas.height;
  const scale = Math.min((w - 2 * pad) / Math.max(xmax - xmin, 1e-6),
                         (h - 2 * pad) / Math.max(ymax - ymin, 1e-6));
  state.view.scale = scale;
  state.view.tx = (w - (xmax - xmin) * scale) / 2 - xmin * scale;
  // SUMO 的 y 向上, canvas 的 y 向下, 这里翻转
  state.view.ty = (h + (ymax - ymin) * scale) / 2 + ymin * scale;
}

const toScreenX = (x) => x * state.view.scale + state.view.tx;
const toScreenY = (y) => -y * state.view.scale + state.view.ty;

function resize() {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  fitView();
  draw();
}
window.addEventListener('resize', resize);

// ---------------- 绘制 ---------------- //
function tracePolygons(shapes) {
  ctx.beginPath();
  for (const shape of shapes) {
    ctx.moveTo(toScreenX(shape[0][0]), toScreenY(shape[0][1]));
    for (let i = 1; i < shape.length; i++) ctx.lineTo(toScreenX(shape[i][0]), toScreenY(shape[i][1]));
    ctx.closePath();
  }
}

function traceCenterline(center) {
  ctx.moveTo(toScreenX(center[0][0]), toScreenY(center[0][1]));
  for (let i = 1; i < center.length; i++) {
    ctx.lineTo(toScreenX(center[i][0]), toScreenY(center[i][1]));
  }
}

/* 按「宽度(或宽度+颜色)」分组批量描线, 否则大路网每帧上万次 stroke 会卡 */
function strokeLaneGroups(groups, dpr, minPx) {
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const [key, group] of groups) {
    ctx.strokeStyle = group.color;
    ctx.lineWidth = Math.max(group.width * state.view.scale, minPx * dpr);
    ctx.beginPath();
    for (const lane of group.lanes) traceCenterline(lane.center);
    ctx.stroke();
  }
}

function draw() {
  if (!state.static) return;
  const w = canvas.width, h = canvas.height;
  const dpr = window.devicePixelRatio || 1;

  // 陆地底色 (而不是 clearRect 留白)
  ctx.fillStyle = MAP_STYLE.land;
  ctx.fillRect(0, 0, w, h);

  // 底图分层: 大面积的用地在前, 建筑在后
  for (const kind of BASEMAP_ORDER) {
    const shapes = state.static.basemap.filter((poly) => poly.kind === kind).map((poly) => poly.shape);
    if (!shapes.length) continue;
    ctx.fillStyle = MAP_STYLE[kind];
    tracePolygons(shapes);
    ctx.fill();
    if (kind === 'building') {  // 建筑给一圈细描边, 密集区才分得出单体
      ctx.strokeStyle = MAP_STYLE.buildingLine;
      ctx.lineWidth = 1 * dpr;
      ctx.stroke();
    }
  }

  // ---- 道路: 照 Google Maps 的画法分三层 ----
  // 1) 路缘描边 (比路面宽一点的灰) 2) 白色路面 3) 上面一条较窄的拥堵色带。
  // 这样路网整体读作「浅色底上的白色网络」, 全图只有拥堵色带是饱和的。
  const lanes = state.static.lanes;
  const values = currentValues();

  const byWidth = new Map();
  for (const lane of lanes) {
    if (!byWidth.has(lane.width)) byWidth.set(lane.width, { width: lane.width, color: '', lanes: [] });
    byWidth.get(lane.width).lanes.push(lane);
  }

  // 路口先用路面色填掉, 免得交叉口是一个个空洞 (那里没有拥堵数据)
  const junctions = state.static.nodes || [];

  for (const group of byWidth.values()) group.color = MAP_STYLE.roadCasing;
  strokeLaneGroups(byWidth, dpr, 3);
  if (junctions.length) {
    ctx.strokeStyle = MAP_STYLE.roadCasing;
    ctx.lineWidth = 2 * dpr;
    tracePolygons(junctions);
    ctx.stroke();
  }

  for (const group of byWidth.values()) group.color = MAP_STYLE.road;
  strokeLaneGroups(byWidth, dpr, 2);
  if (junctions.length) {
    ctx.fillStyle = MAP_STYLE.road;
    tracePolygons(junctions);
    ctx.fill();
  }

  // 拥堵色带: 按 (颜色, 宽度) 分组, 宽度取路面的 0.68 倍, 留出白色路缘
  if (values) {
    const byColor = new Map();
    for (let i = 0; i < lanes.length; i++) {
      const lane = lanes[i];
      const v = state.granularity === 'lane'
        ? values[i]
        : (lane.edge >= 0 ? values[lane.edge] : 1);
      const color = congestionColor(v);
      const key = color + '@' + lane.width;
      if (!byColor.has(key)) byColor.set(key, { width: lane.width * 0.68, color, lanes: [] });
      byColor.get(key).lanes.push(lane);
    }
    strokeLaneGroups(byColor, dpr, 1.2);
  }

  drawAircraft();
}

function currentValues() {
  if (!state.frame) return null;
  const b64 = state.granularity === 'lane' ? state.frame.lane : state.frame.edge;
  return decodeQuantized(b64);
}

function decodeQuantized(b64) {
  const bin = atob(b64);
  const out = new Float32Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i) / 255;
  return out;
}

function drawAircraft() {
  if (!state.frame || !state.frame.aircraft) return;
  for (const uav of state.frame.aircraft) {
    const x = toScreenX(uav.x), y = toScreenY(uav.y);
    // 感知范围的示意光晕
    ctx.beginPath();
    ctx.arc(x, y, 22, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(26, 115, 232, .15)';
    ctx.fill();
    // UAV 本体画成一个三角形, 与路网的矩形色块区分开
    ctx.beginPath();
    ctx.moveTo(x, y - 9); ctx.lineTo(x - 7, y + 6); ctx.lineTo(x + 7, y + 6);
    ctx.closePath();
    ctx.fillStyle = '#1a73e8';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    // 标签描白边, 免得压在深色路段上看不清
    const label = `${uav.id} (${uav.z.toFixed(0)}m)`;
    ctx.font = '600 11px Roboto, sans-serif';
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#fff';
    ctx.strokeText(label, x + 12, y + 4);
    ctx.fillStyle = '#202124';
    ctx.fillText(label, x + 12, y + 4);
  }
}

// ---------------- 交互: 拖拽 / 缩放 / 悬停 ---------------- //
let dragging = false, lastX = 0, lastY = 0;
canvas.addEventListener('mousedown', (e) => { dragging = true; lastX = e.clientX; lastY = e.clientY; });
window.addEventListener('mouseup', () => { dragging = false; });
canvas.addEventListener('mousemove', (e) => {
  const dpr = window.devicePixelRatio || 1;
  if (dragging) {
    state.view.tx += (e.clientX - lastX) * dpr;
    state.view.ty += (e.clientY - lastY) * dpr;
    lastX = e.clientX; lastY = e.clientY;
    draw();
  } else {
    showTooltip(e);
  }
});
canvas.addEventListener('mouseleave', () => { tooltip.style.opacity = 0; });
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const mx = (e.clientX - rect.left) * dpr, my = (e.clientY - rect.top) * dpr;
  const k = e.deltaY < 0 ? 1.15 : 1 / 1.15;
  // 以鼠标位置为中心缩放
  state.view.tx = mx - (mx - state.view.tx) * k;
  state.view.ty = my - (my - state.view.ty) * k;
  state.view.scale *= k;
  draw();
}, { passive: false });

document.getElementById('reset-view').addEventListener('click', () => { fitView(); draw(); });
for (const radio of document.querySelectorAll('input[name=granularity]')) {
  radio.addEventListener('change', (e) => { state.granularity = e.target.value; draw(); });
}

function showTooltip(e) {
  if (!state.static || !state.frame) return;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const mx = (e.clientX - rect.left) * dpr, my = (e.clientY - rect.top) * dpr;
  const values = currentValues();
  const lanes = state.static.lanes;
  for (let i = 0; i < lanes.length; i++) {
    // 命中判定改成「到中心线的距离 < 半个路宽」(几何已经是中心线而不是多边形了)
    const halfWidth = Math.max(lanes[i].width * 0.5 * state.view.scale, 3);
    if (distanceToPolyline(mx, my, lanes[i].center) > halfWidth) continue;
    const lane = lanes[i];
    const edgeId = lane.edge >= 0 ? state.static.edge_ids[lane.edge] : '-';
    const rel = lane.edge >= 0 ? values[state.granularity === 'lane' ? i : lane.edge] : NaN;
    const name = lane.edge >= 0 ? state.static.edge_names[lane.edge] : '';
    // 显示实际车速与限速, 而不是只有一个归一化数字
    const speeds = state.frame.speed ? decodeQuantized(state.frame.speed) : null;
    const kmh = (speeds && lane.edge >= 0)
      ? (speeds[lane.edge] * state.static.speed_scale * 3.6).toFixed(0) : '?';
    const limit = lane.edge >= 0 ? state.static.edge_limits_kmh[lane.edge].toFixed(0) : '?';
    tooltip.textContent =
      `${LEVEL_NAMES[levelIndex(rel)]}  ·  ${kmh} / ${limit} km/h\n`
      + `Edge ${edgeId}${name ? ' · ' + name : ''}\n`
      + `Lane ${lane.id}`;
    tooltip.style.left = (e.clientX - rect.left + 14) + 'px';
    tooltip.style.top = (e.clientY - rect.top + 14) + 'px';
    tooltip.style.opacity = 1;
    return;
  }
  tooltip.style.opacity = 0;
}

/* 点到折线的最短距离 (屏幕坐标), 用于悬停命中判定 */
function distanceToPolyline(px, py, center) {
  let best = Infinity;
  for (let i = 1; i < center.length; i++) {
    const x1 = toScreenX(center[i - 1][0]), y1 = toScreenY(center[i - 1][1]);
    const x2 = toScreenX(center[i][0]), y2 = toScreenY(center[i][1]);
    const dx = x2 - x1, dy = y2 - y1;
    const lenSq = dx * dx + dy * dy;
    let t = lenSq > 0 ? ((px - x1) * dx + (py - y1) * dy) / lenSq : 0;
    t = Math.max(0, Math.min(1, t));   // 投影落在线段外时取端点
    const ex = px - (x1 + t * dx), ey = py - (y1 + t * dy);
    best = Math.min(best, Math.hypot(ex, ey));
  }
  return best;
}

// ---------------- 侧栏 ---------------- //
/* 拥堵等级: 与地图上的四种颜色一一对应, 给出人能读懂的名字 */
const LEVEL_NAMES = ['Stopped', 'Slow', 'Moderate', 'Free flow'];
function levelIndex(v) {
  if (v < 0.25) return 0;
  if (v < 0.50) return 1;
  if (v < 0.75) return 2;
  return 3;
}

/* 街道名等来自 OSM 文件, 属于外部数据, 拼进 innerHTML 前必须转义 */
function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (ch) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]
  ));
}

function formatClock(seconds) {
  const s = Math.round(seconds);
  const hh = Math.floor(s / 3600), mm = Math.floor((s % 3600) / 60), ss = s % 60;
  const mmss = `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
  return hh > 0 ? `${hh}:${mmss}` : mmss;
}

function updateSidePanel() {
  const frame = state.frame;
  if (!frame) return;
  document.getElementById('clock').textContent = `${formatClock(frame.time)}  (t = ${frame.time}s)`;

  // KPI 都用有单位、方向直观的量: 速度越低越堵, 百分比越低越堵
  document.getElementById('kpi-speed').textContent = frame.kpi.avg_speed_kmh.toFixed(0) + ' km/h';
  document.getElementById('kpi-freeflow').textContent = (frame.kpi.free_flow * 100).toFixed(0) + '%';
  document.getElementById('kpi-vehicles').textContent = frame.kpi.vehicles;
  document.getElementById('kpi-halting-sub').textContent = `${frame.kpi.halting} stopped in queue`;
  document.getElementById('kpi-jam').textContent = (frame.kpi.jam_ratio * 100).toFixed(0) + '%';

  state.trend.push(frame.kpi.free_flow);
  if (state.trend.length > 240) state.trend.shift();
  drawTrend();
  updateLevels();
  updateRanking();
  updateUav();
}

/* 四档路段的构成条: 比单个平均值更能说明「全网到底是什么状况」 */
function updateLevels() {
  const levels = state.frame.levels || [];
  const total = levels.reduce((a, b) => a + b, 0) || 1;
  document.getElementById('levels').innerHTML = levels
    .map((count, i) => {
      const pct = (count / total) * 100;
      if (pct <= 0) return '';
      return `<span class="level-seg" style="width:${pct}%;background:${RAMP[i]}"
                    title="${LEVEL_NAMES[i]}: ${count} edges (${pct.toFixed(0)}%)">${
        pct > 8 ? count : ''}</span>`;
    })
    .join('');
}

function drawTrend() {
  const c = document.getElementById('trend');
  const dpr = window.devicePixelRatio || 1;
  const rect = c.getBoundingClientRect();
  c.width = rect.width * dpr; c.height = 110 * dpr;
  const g = c.getContext('2d');
  const w = c.width, h = c.height;
  g.clearRect(0, 0, w, h);

  // 参考线: 0.4 是「拥堵」的阈值, 与 KPI 里的拥堵路段占比同一标准
  g.strokeStyle = '#dadce0'; g.lineWidth = 1 * dpr;
  g.beginPath(); g.moveTo(0, h * 0.6); g.lineTo(w, h * 0.6); g.stroke();

  const data = state.trend;
  if (data.length < 2) return;
  g.beginPath();
  for (let i = 0; i < data.length; i++) {
    const x = (i / (data.length - 1)) * w;
    const y = h - data[i] * h;
    i === 0 ? g.moveTo(x, y) : g.lineTo(x, y);
  }
  g.strokeStyle = '#1a73e8'; g.lineWidth = 1.6 * dpr;
  g.stroke();
}

/* 排名直接用服务端算好的行: 带街道名、实际车速、限速与排队数,
   而不是只甩一个 0~1 的归一化数字 (那个数字 0 表示「堵死」, 很容易被读反) */
function updateRanking() {
  const rows = state.frame.ranking || [];
  const el = document.getElementById('ranking');
  if (!rows.length) {
    el.innerHTML = '<li class="empty">No congested edges — network is flowing freely</li>';
    return;
  }
  el.innerHTML = rows.map((row) => {
    const level = levelIndex(row.rel);
    const label = escapeHtml(row.id + (row.name ? ` · ${row.name}` : ''));
    return `<li>
      <i class="chip" style="background:${RAMP[level]}"></i>
      <span class="rank-id" title="${label}">${label}</span>
      <span class="rank-speed">${row.kmh.toFixed(0)}<em>/${row.limit.toFixed(0)} km/h</em></span>
      <span class="rank-sub">${LEVEL_NAMES[level]} · ${row.veh} veh, ${row.halt} stopped</span>
    </li>`;
  }).join('');
}

function updateUav() {
  const frame = state.frame;
  const meta = document.getElementById('uav-meta');
  const grid = document.getElementById('images');

  if (!frame.aircraft || frame.aircraft.length === 0) {
    meta.textContent = 'No UAV';
    grid.innerHTML = '';
    return;
  }
  meta.textContent = frame.aircraft.map((uav) => {
    const near = frame.nearby[uav.id] || {};
    const nVeh = (near.vehicle || []).length;
    const nTls = (near.tls || []).length;
    return `${uav.id} @ (${uav.x.toFixed(0)}, ${uav.y.toFixed(0)}, ${uav.z.toFixed(0)}m)`
         + ` · nearby ${nVeh} vehicles / ${nTls} junctions`;
  }).join('\n');

  // 只在图像集合发生变化时重建 DOM, 否则每帧替换 innerHTML 会让放大层里的图闪烁
  const images = frame.images || {};
  const names = Object.keys(images);
  if (names.join('|') !== state.imageNames) {
    state.imageNames = names.join('|');
    grid.innerHTML = names
      .map((name) => {
        const safe = escapeHtml(name);
        return `<figure><img data-name="${safe}" alt="${safe}"><figcaption>${safe}</figcaption></figure>`;
      })
      .join('');
  }
  for (const img of grid.querySelectorAll('img')) {
    img.src = images[img.dataset.name];
  }
  // 放大层开着的时候也跟着更新, 这样能全屏看实时画面而不是一张静止的截图
  if (state.zoomedImage && images[state.zoomedImage]) {
    document.getElementById('lightbox-img').src = images[state.zoomedImage];
  }
}

// 点击回传图像后全屏查看 (侧栏再宽也有限, 细节还是得放大看)
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightbox-img');
const lightboxCaption = document.getElementById('lightbox-caption');

document.getElementById('images').addEventListener('click', (e) => {
  if (e.target.tagName !== 'IMG') return;
  state.zoomedImage = e.target.dataset.name;
  lightboxImg.src = e.target.src;
  lightboxCaption.textContent = e.target.dataset.name;
  lightbox.classList.add('open');
});
lightbox.addEventListener('click', () => {
  state.zoomedImage = null;
  lightbox.classList.remove('open');
});
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { state.zoomedImage = null; lightbox.classList.remove('open'); }
});

// ---------------- 数据接入 ---------------- //
async function boot() {
  // 静态数据是仿真 reset 之后才 set 的; 浏览器可能开得比仿真快, 这时拿到的是空对象。
  // 轮询等它就绪, 否则页面会卡在一个永远画不出东西的状态
  const conn = document.getElementById('conn');
  conn.textContent = 'Waiting for simulation…';
  while (true) {
    try {
      const payload = await (await fetch('static.json', { cache: 'no-store' })).json();
      if (payload && payload.lanes && payload.lanes.length) { state.static = payload; break; }
    } catch (err) { /* 服务还没起来, 继续等 */ }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  resize();

  const source = new EventSource('stream');
  source.onopen = () => { conn.textContent = 'Connected'; conn.className = 'badge online'; };
  source.onerror = () => { conn.textContent = 'Disconnected'; conn.className = 'badge offline'; };
  source.onmessage = (event) => {
    state.frame = JSON.parse(event.data);
    draw();
    updateSidePanel();
  };
}

boot();
