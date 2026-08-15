# tshub_env3d 3D 资源 (_assets_3d)

本目录存放 3D 渲染用到的静态资源。其中体积较大的车辆模型素材 **不随仓库分发**，需自行下载放到指定位置。

```
_assets_3d/
├── vehicles/        车辆 3D 模型 (low/high poly, 未入库, 见下文)
├── skybox/          天空盒: skybox.bam + 程序化渐变 shader
├── map_road_lines/  道路线 shader
├── shader/          通用 unlit shader
├── terrain/         地面 shader
└── simple_car.glb   占位/示例车辆
```

---

## 车辆模型 (vehicles/)

车辆模型按 **low poly / high poly** 两套并存，通过环境参数 `vehicle_model='low'|'high'` 选择
(`low` 渲染更快)。两套渲染器 (Panda3D / Open3D) 共用同一套模型与「车辆类型 → 模型」映射
(`tshub/tshub_env3d/scene/vehicle_models.py`)。

### 目录与命名 (映射依赖文件名，务必对应)

```
vehicles/{vehicles_low_poly | vehicles_high_poly}/
├── background/        a.glb b.glb c.glb d.glb e.glb f.glb   # 普通背景车 (按权重随机选取)
├── public_transport/  taxi.glb police.glb emergency.glb fire_engine.glb
├── ego/               ego.glb                                # ego 车辆
└── event/             crash_vehicle.glb barrier_A..E.glb pedestrian.glb
                       tree_branch_1lane.glb tree_branch_3lanes.glb other_accidents.glb
```

- **替换某个模型**：直接覆盖同名 `.glb` 即可，无需改代码，下一次渲染立即生效。
- **增加背景车种类**：把 `g.glb`、`h.glb`… 放进 `background/`，再到
  `scene/vehicle_models.py` 的 `_BACKGROUND_MODELS` / `_BACKGROUND_WEIGHTS` 里登记。
- `vehicles/` 整个目录体积大、未入库，模型只保存在本地。

### 模型规格 (代码要求，务必满足)

| 项目 | 要求 |
|------|------|
| 格式 | **`.glb`** (glTF 二进制，内嵌网格与材质/颜色) |
| 尺寸 | **真实世界米制**。模型按其自身大小渲染，**不会**被缩放到 SUMO 车长 |
| 朝向 | **车头 = 局部 +Z**，**车顶 = +Y**，车宽 = X (与现有模型一致) |
| 材质 | 车身纯色、偏哑光 (粗糙度 ≈ 0.6，金属度 ≈ 0.3) |
| 面数 | low 套 ≈ 2000–2600 三角面；high 套可更多 |

现有模型参考尺寸 (长度在 **Z** 轴)：轿车长 `4.3–4.8 m`、宽 `~1.8–2.0 m`、高 `~1.5 m`；
消防车长 `6.6 m`。

> **保证朝向/尺寸的可靠做法**：在 Blender 里先导入一个现有模型
> (`vehicles_low_poly/background/a.glb`) 作参照，把新车对齐到相同朝向、调到相近大小，
> 删掉参照后再导出 `.glb`。这样可避免 Blender ↔ glTF 坐标轴换算出错。

### 去哪里下载

**低多边形 / 风格化** (与现有 low poly 套一致，推荐)：

- **Kenney** — <https://kenney.nl> → "Car Kit" / "City Kit"。CC0 (免署名)，风格统一，含 glb/gltf。最契合。
- **Quaternius** — <https://quaternius.com> → 车辆包。CC0，风格统一，免费。
- **Poly Pizza** — <https://poly.pizza> → 搜索 car/bus/truck。CC-BY，可直接下载 `.glb`。

**写实 / 高多边形** (用于 high poly 套)：

- **Sketchfab** — <https://sketchfab.com>，筛选 **Downloadable** + 许可 **CC0/CC-BY**，"Download → glTF"。写实车型最丰富。
- **CGTrader / TurboSquid** — 免费区 (逐个确认许可)，适合写实车型。
- **BlenderKit** (Blender 插件) — 内置免费模型，导入后导出 `.glb`。

> 非 `.glb` 的素材 (`.obj/.fbx/.gltf`) 先在 Blender 里导入，按上面的规格 (米制、+Z 车头、
> 哑光材质) 调整后导出为 `.glb`。

---

## 天空盒 (skybox/)

Panda3D 天空使用 `skybox/skybox.bam` 加程序化 city-builder 渐变 shader。
环境参数 `sky='day'|'dust'` 只选择预设渐变颜色，不再依赖 HDR 贴图。
