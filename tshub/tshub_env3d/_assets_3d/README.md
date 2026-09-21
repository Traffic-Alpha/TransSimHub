# tshub_env3d 3D 资源 (_assets_3d)

本目录存放 3D 渲染用到的静态资源。其中体积较大的车辆/环境模型 **不随仓库分发**，需自行准备后放到指定位置。

```
_assets_3d/
├── vehicles/     车辆 + 飞行器 3D 模型 (未入库, 见下文)
├── environment/  静态场景道具: 建筑 / 树木 / 路边小物件 (供 scene/ 的生成流水线摆放)
├── skybox/       天空盒: skybox.bam + 程序化渐变 shader + IBL 环境贴图 (env_day / env_dust)
└── shader/       Panda3D 语义分割 shader (segmentation.vert / .frag)
```

---

## 车辆模型 (vehicles/)

只维护 **一套** 模型 (没有 low/high poly 之分)。「车辆类型 → 模型」的映射由渲染器无关的
`tshub/tshub_env3d/core/models/vehicle_models.py` 提供，Panda3D (在线) 与 Blender (离线)
两条渲染路径共用，保证同一辆车在两边是同一个模型。

### 目录与命名 (映射依赖文件名，务必对应)

```
vehicles/
├── background/        sedan suv hatchback taxi compact wagon minivan
│                      offroad pickup coupe sport (.glb)   # 背景车, 按权重随机
├── public_transport/  police.glb emergency.glb fire_engine.glb
├── ego/               ego.glb                              # ego 车辆
├── event/             crash_vehicle.glb barrier_A..E.glb pedestrian.glb
│                      tree_branch_1lane.glb tree_branch_3lanes.glb other_accidents.glb
└── evetol/            evetol_design_2022.glb               # 飞行器 (aircraft_models.py)
```

- **替换某个模型**：直接覆盖同名 `.glb` 即可，无需改代码，下一次渲染立即生效。
- **增加背景车种类**：把新 `.glb` 放进 `background/`，再到
  `core/models/vehicle_models.py` 的 `_BACKGROUND_MODELS` / `_BACKGROUND_WEIGHTS` 里登记。
- `vehicles/` 整个目录体积大、未入库，模型只保存在本地。

### 模型规格 (代码要求，务必满足)

| 项目 | 要求 |
|------|------|
| 格式 | **`.glb`** (glTF 二进制，内嵌网格与材质/贴图) |
| 尺寸 | **真实世界米制**。模型按其自身大小渲染，**不会**被缩放到 SUMO 车长 |
| 朝向 | **车头 = 局部 +Z**，**车顶 = +Y**，车宽 = X |
| 原点 | X 居中、**Y 在车底 (贴地)**、Z 居中 —— 摆放代码按「原点在地面」放车 |
| 材质 | 车漆偏哑光；颜色可以在 `baseColorFactor` 或 `baseColorTexture` 里 |
| 面数 | ≈ 7k 三角面 (现有 CC0 车模的量级) |

现有模型参考尺寸 (长度在 **Z** 轴)：轿车 `4.4×1.9×1.35 m`、SUV `4.6×2.1×1.7 m`、
皮卡 `5.2×2.1×1.7 m`、消防车 `8.0 m`。

> **判断颜色不要用 trimesh 的 `main_color`**：CC0 模型常把颜色放在贴图里，trimesh 不采样
> 贴图会一律报灰色；Blender / simplepbr 都会正确采样。同理别用 `trimesh.util.concatenate`
> 合并部件，会把贴图拍平成灰色。

> **保证朝向/尺寸的可靠做法**：在 Blender 里先导入一个现有模型 (`background/sedan.glb`)
> 作参照，把新车对齐到相同朝向、调到相近大小，删掉参照后再导出 `.glb`。

### 去哪里下载

- **Kenney** — <https://kenney.nl> → "Car Kit" / "City Kit"。CC0 (免署名)，风格统一。
- **Quaternius** — <https://quaternius.com> → 车辆包 / 建筑包。CC0。
- **Poly Pizza** — <https://poly.pizza>。CC-BY，可直接下载 `.glb`。
- **Sketchfab** — 筛选 **Downloadable** + **CC0/CC-BY**，"Download → glTF"，写实车型最多。

> 非 `.glb` 的素材 (`.obj/.fbx/.gltf`) 先在 Blender 里导入，按上面的规格调整后导出为 `.glb`。

---

## 环境道具 (environment/)

`buildings/` `trees/` `props/` 三类 `.glb`，由 `scene/blender/build_scene.py` 按
`<category>/*.glb` 通配加载。要求同样是：直立、底面 z=0、XY 居中、真实米制。

**摆放不是随机撒的**：位姿由 Stage 1 的 `scene/scene_data/scatter.py` 用 shapely 算好，
连同**资产文件名**（不含 `.glb`）一起写进 scene.json，Blender 侧按名字查模板实例化。
所以新增/改名资产要同步 `SCATTER_STYLE`：

- `trees` — `SCATTER_STYLE["trees"]["assets"]` 列出可选树种（整张图只用其中一种，
  行道树本就是同一批栽的，混种反而杂乱）。
- `buildings` — `SCATTER_STYLE["buildings"]["assets"]` 里每项是
  `(资产名, 门面宽 m, 进深 m)`，尺寸用来算占地、做足迹相交检测。约定**局部 −Y 是开窗立面**，
  摆放时会把它转向最近的路面。
- `props` — 每种小物件（路灯/长椅…）单独一组参数：离路缘距离、间距、是否朝向车道。

---

## 天空盒与环境光 (skybox/)

- Panda3D 天空 = `skybox.bam` + 程序化 city-builder 渐变 shader (`skybox.vert/frag.glsl`)。
  环境参数 `sky='day'|'dust'` 只选择预设渐变颜色，不依赖 HDR 贴图。
- `env_day/` `env_dust/` 是与渐变天空一致的 cubemap，用于 simplepbr 的 IBL 环境光照
  (否则会出现「天空亮、地面和车暗」)。改了 shader 里的 `SKY_COLORS` 之后，重跑
  `python skybox/gen_env_cubemap.py` 重新生成。

Blender 侧不使用这些资源：它的天空与太阳是程序化物理天空，见
`scene/blender/scene_assembly.py` 的 `LIGHT_STYLES`。
