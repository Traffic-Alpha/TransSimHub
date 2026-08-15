<!--
 * @Author: WANG Maonan
 * @Date: 2026-08-11 10:00:00
 * @Description: 中观交通大屏的示例说明
 * @LastEditTime: 2026-08-11 10:00:00
-->
# 中观交通大屏 (实时)

TransSimHub 的第三条可视化路径, 回答的是「**整个路网哪里在堵、怎么扩散**」,
而不是「每一辆车在做什么」。

三种视图的分工:

| 视图 | 入口 | 看什么 |
| --- | --- | --- |
| 微观 | `TshubEnvironment.render(mode='sumo_gui')` / `use_gui=True` | 每一辆车的行为, 范围小 |
| **中观** | **`tshub.visualization.meso`** | **全路网的拥堵演化, 不到车辆粒度** |
| 空中 3D | `Tshub3DEnvironment` + `sensor_config` | UAV / 车载 / 路口相机的图像 |

## 数据从哪来

大屏只吃 `obs` 里的三个 key, 不反向依赖 env, 所以任何拿得到这些数据的循环都能推给它:

- `obs['lane_shape']` — 车道的**静态几何** (`is_map_builder_initialized=True`), 用来画路网;
- `obs['edge_state']` — 路段级**动态状态** (`is_edge_builder_initialized=True`), 用来着色;
- `obs['lane_state']` — 车道级**动态状态** (`is_lane_builder_initialized=True`), 切到「车道」粒度时用。

拥堵指数是 `speed_relative = 实际速度 / 限速` (与 SUMO meandata 的 `speedRelative` 同义):
1 表示自由流, 0 表示完全停死。空路段时 SUMO 返回的平均速度就是限速, 所以空路自然是 1。

> 注意 `obs['lane_shape']`(静态几何) 与 `obs['lane_state']`(动态状态) 是两回事,
> 用 `lane_id` 关联。前者来自 `tshub/map/`, 后者来自 `tshub/lane/`。

## 运行

```shell
# 1. 只看中观大屏 (不需要 3D 资产, 最快上手)
python examples/dashboard/run_meso_dashboard.py

# 2. 中观 + UAV 空中视角 (需要 3D 场景资产与显卡)
python examples/dashboard/run_meso_with_uav.py
```

然后打开终端里打印的地址 (默认 <http://127.0.0.1:8910>)。

想同时看微观, 把示例里的 `use_gui` 改成 `True`, SUMO-GUI 会和大屏一起开。

## 大屏上有什么

- **路网拥堵图** — Google Maps 风格。道路按 Google 的画法分三层:
  **灰色路缘 + 白色路面 + 上面一条较窄的拥堵色带** (占路宽 68%), 所以路网整体读作
  「浅色底上的白色网络」, 全图只有拥堵色带是饱和的。色带用 Google 交通图层的四档配色
  (停滞深红 / 缓行红 / 较慢橙 / 畅通绿)。底图按用地类型分层着色: 水系、公园、树林、
  住宅/商业用地、学校医疗、停车场、建筑。
  可拖拽平移、滚轮缩放、悬停看某条车道的详情; 左上角可在「路段」与「车道」
  粒度之间切换 (路段级看整体, 车道级能看出「左转道排队、直行道畅通」这种
  edge 级看不到的差异)。

  > **底图完全取决于 `poly_file`。** 不传 poly 文件的话, 周围就是一片纯色 ——
  > 没有任何地物数据可画。示例用 kowloon 场景正是因为它带完整的 poly
  > (7000+ 个多边形, 建筑/公园/树林/水系俱全)。像 `single_junction` 这种
  > 没有 poly 的场景, 无论怎么配色, 路网周围都只会是空的。
- **KPI** — 四个都带单位、方向直观的量:
  | 指标 | 含义 | 方向 |
  | --- | --- | --- |
  | Average speed | 在网车辆的平均车速 (km/h), 按车辆数加权 | 越低越堵 |
  | Network at free flow | 全网车速相当于限速的百分之几, 100% = 全部按限速行驶 | 越低越堵 |
  | Vehicles | 在网车辆数, 副标题给出其中排队停车的数量 | — |
  | Congested edges | 车速低于限速一半的路段占比 | 越高越堵 |
- **Network breakdown** — 四档路段的构成条 (停滞 / 缓行 / 较慢 / 畅通 各多少条),
  比单个平均值更能说明"全网到底是什么状况"。
- **趋势** — 畅通程度随时间的变化。
- **最拥堵路段** — 每行是「颜色 + 路段/街道名 + 实际车速/限速 + 状态 + 车辆数/排队数」。
  排序用的是 **延误影响 = (1 - 畅通程度) x 车辆数**, 而不是单纯按车速升序 ——
  后者的榜首会全是「只有一辆车停在红灯前」的小路段, 那不是真正的堵点。

> **关于 `speed_relative` 的方向**: 它是「实际速度 ÷ 限速」, **1 = 完全畅通,
> 0 = 完全堵死**。这个方向容易读反, 所以大屏上不直接显示这个裸数字, 而是换算成
> km/h、百分比和 Stopped/Slow/Moderate/Free flow 这样的文字状态。
- **UAV 回传** — UAV 的位置画在路网上, 机载相机的图像显示在侧栏,
  并标注这一帧 UAV 附近有多少车辆/路口 (`tshub.aircraft.aircraft_nearby`)。
  **点击图像可全屏放大**, 放大后仍然是实时更新的。

大屏界面是英文的。示例里 UAV 的航线是从 A 点飞到 B 点后停下悬停
(`POINT_A` / `POINT_B` / `ARRIVE_TOLERANCE`), 改这几个常量就能换航线。
机载相机只挂俯拍的 `aircraft_rgb` (正交俯视, 看机身正下方的地面), 用 `preset='720P'`,
因为再低的分辨率放到大屏上看不清路面。

## 实现说明

- 服务端只用标准库 (`http.server` + SSE), 没有 flask/fastapi;
  前端是手写的 Canvas 渲染器, 没有 vendored 任何 JS 库 ——
  SUMO 的坐标是笛卡尔米制而不是经纬度, 用不上地图库。
- 每帧的拥堵值量化成 `uint8` 再 base64, 所以一个 2000 边的路网每帧只有几 KB。
  量化往返误差不超过半个量化步长 (≈0.002), 对着色和排序没有影响。
- `push()` 永不阻塞仿真: 每个浏览器一个有界队列, 满了就丢最旧的帧。
  浏览器卡了或者关掉了, 仿真照常跑。
