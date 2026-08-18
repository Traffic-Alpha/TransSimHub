<!--
 * @Author: WANG Maonan
 * @Date: 2026-08-18 14:20:39
 * @Description: TSHub3D Scene 静态场景生成
 * @LastEditTime: 2026-08-18 14:36:40
 * @LastEditors: WANG Maonan
-->
# scene —— 静态场景生成

把 **SUMO 路网**变成**可渲染的 3D 静态场景**。这里生成「不动的东西」路面、车道线、建筑、树、路灯。

---

## 流水线

```
 SUMO map.net.xml  (+ 可选 map.poly.xml)
        │
        │  Stage 1   纯 Python (sumolib + shapely)，在 tshub 环境里跑
        ▼
   scene.json                          ← 纯数据，不含任何引擎概念
        │
        │  Stage 2   blender/build_scene.py   (bpy)
        ▼
   map.glb  ground.glb  road_lines.glb  lane_lines.glb
   buildings.glb  vegetation.glb  props.glb
        │
        ├───────────────────────►  Tshub3DEnvironment(scenario_glb_dir=…)
        │                          Panda3D 在线渲染直接吃 glb
        │
        │  Stage 3   blender/build_blend.py  (bpy)
        ▼
   scene.blend
        │
        └───────────────────────►  renderers/blender/render_episode.py
                                   Cycles 离线渲染
```

**为什么要分两段跑**：
1. Blender 自带的 Python 装不了 `sumolib`/`shapely`，所以路网解析必须在 tshub 环境完成、落成 JSON；
2. Blender 侧只读 JSON。Stage 2/3 的脚本是被 `blender --background --python` **直接执行**的，不通过 `import`，因此它们不能 import 本仓库的其它模块。

---

## 快速开始

仓库里两个 example 分别对应两种输入模式，直接跑即可（需要 Blender，默认 `/home/wmn/blender/blender`，
或用环境变量 `BLENDER=` 指定）：

```bash
# 不带 poly：只有路网
python examples/tshub_env3d/single_junction/build_static_scene.py

# 带 poly：路网 + OSM 建筑轮廓
python examples/tshub_env3d/ymt_area/build_static_scene.py
python examples/tshub_env3d/ymt_area/build_static_scene.py --skip-blend   # 只到 glb，不建 .blend
```

只想要 Stage 1 的 JSON：

```python
from tshub.tshub_env3d.scene import export_scene_geometry

export_scene_geometry("map.net.xml", "scene.json")                       # 不带 poly
export_scene_geometry("map.net.xml", "scene.json",
                      buildings_poly="add/map.poly.xml")                 # 带 poly
```

也可当 CLI：`python -m tshub.tshub_env3d.scene.scene_export map.net.xml scene.json --buildings add/map.poly.xml`

手动跑 Stage 2/3：

```bash
blender --background --python tshub/tshub_env3d/scene/blender/build_scene.py -- scene.json out_dir
blender --background --python tshub/tshub_env3d/scene/blender/build_blend.py -- out_dir scene.blend \
        --style day --samples 64 --resolution 1280x720
```

---

## 两种输入模式

由 `export_scene_geometry(..., buildings_poly=...)` 给不给决定，**没有额外开关**——
Blender 侧看 `scene.json` 里有没有真实轮廓自动分流。

|  | **带 poly** | **不带 poly** |
|---|---|---|
| 额外输入 | `map.poly.xml`（`tshub.sumo_tools.osm_build` 从 OSM 生成） | 无 |
| 建筑 | 真实轮廓挤出灰模，高度取自 OSM param<br>（`height` / `building:height` / `building:levels × 3.2m`，都没有则 12m） | 沿街摆放建筑**模型**，成组连续立面，尺寸不求真 |
| 树 | 沿街树 **+ 绿地（公园/林地）内的树** | 只有沿街树 |
| 适合 | 真实城区（尺度、遮挡都对） | 单路口/合成路网（只求观感） |

路面、路缘铺装带、车道线、边线、转向箭头、路边小物件（路灯/长椅）两种模式**完全一样**。

---

## 目录结构

```
scene/
├── scene_export.py     ← 唯一对外入口（根目录只有它）
├── road_network/       【内部】SUMO 路网 → 道路几何
│   ├── sumo_net.py         SumoNet3D：路面多边形 + 车道/边线折线 + 包围盒
│   ├── geometry.py         buffered_shape（折线 → 带宽度多边形）
│   └── map_elements/       RoadMap / Lane / Road / Surface / Feature（SMARTS 派生）
├── scene_data/         【内部】几何 + OSM + 摆放 → scene.json 数据
│   ├── static_scene.py     总装，两种输入在这里分流
│   ├── road_surface.py     路面/apron 三角网格、折线转 JSON     ← 两模式共用
│   ├── lane_markings.py    车道转向箭头                        ← 两模式共用
│   ├── osm_poly.py         map.poly.xml → 建筑轮廓+高度 / 绿地  ← 仅「带 poly」
│   └── scatter.py          树/小物件（共用）+ 沿街建筑（仅「不带 poly」）
└── blender/            【内部, bpy】只能在 Blender 里跑
    ├── build_scene.py      scene.json → 分类 glb
    ├── build_blend.py      glb → scene.blend（导入 + 打光 + 渲染设置）
    └── scene_assembly.py   装配库（导入/世界环境/相机/实例化）；渲染侧也复用
```

---

## 产物

**`scene.json`**（纯数据，Blender 侧唯一输入）

| key | 内容 |
|---|---|
| `bbox` | `[xmin, ymin, xmax, ymax]`，SUMO 平面坐标（米） |
| `roads` / `apron` | `[{vertices: [[x,y],…], faces: [[i,j,k],…]}]` 三角网格 |
| `lane_dividers` / `edge_borders` | 折线 `[[[x,y],…],…]`，车道线 / 道路边线 |
| `turn_markings` | 车道转向箭头：`{lane_id, turn, center, heading, lane_width}` |
| `buildings` | **仅带 poly**：`[{footprint: [[x,y],…], height: h}]` |
| `scatter` | `{trees, buildings, props}`，每项 `{asset, pos, yaw, scale}`——**含资产文件名** |

**glb**（Stage 2 输出，按语义分文件，渲染侧据此打语义分割标签）

`map`（路面+apron）· `ground`（远处绿地）· `road_lines` · `lane_lines` · `buildings` · `vegetation` · `props`
——某类为空则不生成对应文件（并删掉旧的）。

**`scene.blend`**（Stage 3 输出）：静态场景 + 打光 + 渲染设置。可以用 Blender GUI 打开手工微调后存盘，
离线渲染会沿用你的修改；**自动化和手调不冲突**。

---

## 素材与摆放的约定

**摆放不是在 Blender 里随机撒的**：位姿由 Stage 1 的 `scene_data/scatter.py` 用 shapely 算好，
连同**资产文件名**写进 JSON，Blender 只按名字查模板做实例化。好处是一个资产只存一份网格
（1500 棵树也只有几个 mesh），glb 很小。

所以**新增/改名素材要同步 `SCATTER_STYLE`**（在 `scene_data/scatter.py`）：

- `trees.assets` —— 可选树种。**整张图只用其中一种**：行道树本就是同一批栽的，混种反而杂乱。
  想混种就把 `rng.choice` 挪到 `_tree()` 里逐棵抽。
- `buildings.assets` —— 每项是 `(资产名, 门面宽 m, 进深 m)`。尺寸用来算占地做**足迹相交检测**，
  约定**局部 −Y 是开窗立面**，摆放时会转向最近的路面。
- `props.*` —— 每种小物件一组参数（离路缘距离、间距、`face_road` 是否朝向车道）。

素材本身的规格（朝向、原点、米制）见 [`_assets_3d/README.md`](../_assets_3d/README.md)。

---

## 想改什么，去改哪

| 想改 | 改哪里 |
|---|---|
| 路面/车道线/建筑灰模的**颜色、线宽、高度层次** | `blender/build_scene.py` 的 `CITY_BUILDER_STYLE` |
| 树/建筑/小物件的**密度、间距、离路距离** | `scene_data/scatter.py` 的 `SCATTER_STYLE` |
| 场景里**最多**多少树/小物件 | `scatter.py` 的 `MAX_TREES` / `MAX_PROPS` |
| 每类最多用几种**不同**模型 | `build_scene.py` 的 `ASSET_LIMITS`（超出时跨排序列表均匀取样，保证高矮/品种有变化） |
| 路缘铺装带宽度 | `export_scene_geometry(apron_width=…)` |
| OSM 每层楼按几米算 | `export_scene_geometry(building_level_height=…)` |
| **打光 / 曝光 / 色调**（烘进 .blend 的） | `blender/scene_assembly.py` 的 `LIGHT_STYLES`（day / noon / golden / dusk / overcast）；建 .blend 时用 `build_blend.py --style`，渲染时也能用 `render_blender.py --style` 临时覆盖 |

---

## 约定与坑

- **坐标**：全程 SUMO 平面坐标，单位米。Blender 内是 Z-up；glTF 导出会转成 Y-up，再导入回来又转回 Z-up，
  所以**坐标数值在整条链路里不变**，相机位姿可以直接用 tshub 世界坐标。
- **`blender/` 里的脚本不能 import 本仓库其它模块**（Blender 的 Python 是独立环境）。
  它们靠 `sys.path` 找同目录模块；`renderers/blender/render_episode.py` 复用 `scene_assembly.py`
  也是这么做的。
- **SUMO 的道路多边形偶尔自相交**，union 前先 `buffer(0)` 清洗，否则 shapely 会抛
  "side location conflict"；apron 整段都有 try/except 兜底。
- **internal edge（路口内连接段）不参与路面生成**，否则路口会被一堆重叠的连接带 z-fighting 成黑色；
  路口面积由 junction 多边形覆盖。
- OSM 的数值字段很脏（`"12"` / `"12.5 m"` / `"40 ft"`），`osm_poly._parse_osm_number` 只取第一个数字
  并处理英尺，取不到就退回默认高度。
