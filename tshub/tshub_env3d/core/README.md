<!--
 * @Author: WANG Maonan
 * @Date: 2026-08-18 16:33:12
 * @Description: TSHub3D -- Core
 * @LastEditTime: 2026-08-18 17:09:50
 * @LastEditors: WANG Maonan
-->
# core —— 仿真与渲染之间的契约层

`core/` 里没有一行渲染代码，它定义的是**「渲染需要知道的一切」**：这一帧有哪些物体、在哪、朝哪、
用哪个模型、相机架在哪、每个像素属于哪一类。

一句话概括它存在的理由：**同一份定义同时喂给 Panda（在线）和 Blender（离线）。**
同一辆车在两边必然是同一个 glb，同一个 `front_rgb` 相机在两边必然是同一个位姿，seg 标签必然对得上。

---

## core 给渲染器提供了什么

按「渲染一帧需要回答的问题」组织：

| 渲染器要问 | core 给的答案 | 出处 |
|---|---|---|
| 这一帧场上有哪些物体？在哪？朝哪？ | `SceneFrame{vehicles, aircraft}`，每项是 `ObjectPose` | `state/` |
| 整局不变的信息是什么？ | `SceneStatic{scenario_glb_dir, sensor_config, tls_rigs}` | `state/` |
| 这辆车该用哪个 3D 模型？ | `select_vehicle_model_name(veh_type)` → glb 相对路径 | `models/` |
| 这个传感器的相机该架在哪、看向哪？ | `get_camera_rig(sensor_type)` + `compute_camera_pose(...)` → `(eye, target)` | `sensors/` |
| 这个像素是什么类别？该涂什么颜色？ | `SEG_CLASSES` / `SEG_RENDER_COLORS` / `seg_color_to_label` | `sensors/` |
| SUMO 的车头坐标/朝向怎么换算？ | `Pose.from_front_bumper` / `Heading.from_sumo` | `utils/` |
| 我这个后端要实现什么接口？ | `RendererBackend`：`reset / sync / destroy` | `renderer_backend.py` |

**实际的消费清单**（不是设想，是仓库里真实的 import）：

```
renderers/panda/tshub_render.py          ← SceneFrame, SceneStatic, RendererBackend
renderers/panda/rendering_components/    ← SceneFrame, SceneStatic, ObjectPose, validate_sensor_config
renderers/panda/traffic_elements/        ← get_camera_rig, select_vehicle_model_name,
                                            select_aircraft_model_name, Pose, Heading
renderers/panda/sensors/                 ← CameraRig, compute_camera_pose, seg_color_to_label, Pose
renderers/panda/segmentation.py          ← SEG_RENDER_COLORS
renderers/blender/render_passes.py       ← SEG_NAME_TO_COLOR（软依赖，见下）
renderers/__init__.py                    ← RendererBackend（工厂的返回类型）
tshub_env3d.py                           ← SceneStatic, build_frame, build_tls_rigs
scene/road_network/                      ← Point / Pose / BoundingBox / core_math（几何计算）
```

> **Blender 侧是「软依赖」**：`renderers/blender/*` 在 Blender 自带的 Python 里跑，装不了 tshub，
> 所以 `render_passes.py` 用 `try: from ...core.sensors.seg_classes import ...` 取调色板，
> 取不到就退回文件里内联的同一份。**改调色板要同时改两处**（内联那份有注释标明）。

---

## 一步仿真里的调用顺序

```
reset()
  obs ──► build_tls_rigs(obs, sensor_config)      ← 算出每个路口相机的载体位姿
       ──► SceneStatic(...)  ──► RendererBackend.reset(static)

step()
  obs ──► build_frame(obs)                        ← 车辆保留 SUMO heading;
       │                                            飞行器速度向量 → 角度
       └─► SceneFrame ──► RendererBackend.sync(frame)
                              │
                              ├─ select_vehicle_model_name(veh_type)   选 glb
                              ├─ Pose.from_front_bumper(...)           车头 → 车辆中心
                              ├─ get_camera_rig + compute_camera_pose  相机 (eye, target)
                              └─ SEG_RENDER_COLORS / seg_color_to_label  语义分割
```

离线路径把同样的东西换个出口：`export/BlenderEpisodeExporter` 把逐帧的 `SceneFrame` 和相机位姿
落成 JSON，Blender 后台再读。

---

## 目录

```
core/
├── renderer_backend.py   RendererBackend ABC：reset / sync / destroy
├── state/                仿真状态 → 场景数据
│   ├── scene_elements.py     ObjectPose / SceneFrame / SceneStatic
│   └── scene_builder.py      build_frame / build_tls_rigs / validate_sensor_config
├── sensors/              传感器定义
│   ├── sensor_rig.py         CameraRig + CAMERA_RIGS + compute_camera_pose
│   └── seg_classes.py        10 个语义类别 + CARLA 调色板 + 颜色↔label 互转
├── models/               物体类型 → glb
│   ├── vehicle_models.py     特殊车型查表 + 背景车按权重随机
│   └── aircraft_models.py
├── export/               离线渲染的剧集导出
│   └── blender_export.py     每帧一个 JSON（物体位姿 + 相机位姿）
└── utils/                坐标与数学（SMARTS 派生）
    ├── coordinates.py        Point / Pose / Heading / BoundingBox / RefLinePoint
    └── core_math.py          只保留实际用到的 10 个函数
```

`core/__init__.py` 是**扁平门面**：`from tshub.tshub_env3d.core import X` 就能拿到上面所有公开符号，
上层不需要知道内部分包。

---

## 几个必须记住的约定

**坐标系**：全程 tshub/SUMO 平面坐标，米。x/y 是地面，z 是高度。

**朝向有两套，别搞混**：

| | 0° 指向 | 旋转方向 | 出现在哪 |
|---|---|---|---|
| SUMO | 正北 (+Y) | **顺时针** | `obs` 里的原始 heading、`ObjectPose.heading`（车辆） |
| tshub/SMARTS | +Y | **逆时针** | `Heading` 类型、`compute_camera_pose` 的入参、Panda 的 `setH` |

换算入口只有一个：`Heading.from_sumo(sumo_deg)`。`ObjectPose.heading` 的格式**按 category 而定**——
车辆是 SUMO 原值，飞行器已经在 `build_frame` 里转成了角度，这是历史遗留的不对称，用之前看清楚。

**SUMO 给的车辆位置是车头（front bumper），不是中心。** 摆模型前必须用
`Pose.from_front_bumper(pos, heading, length)` 退回车辆中心，否则整车会前移半个车长。

**相机 rig 是声明式的**：`CameraRig` 描述「挂在谁身上、相对位姿、fov、模态」，
`compute_camera_pose` 把它 + 载体世界位姿算成 `(eye, target)`。13 个基础 rig × {rgb, seg} = 26 个
`sensor_type`（vehicle 14 / tls 6 / aircraft 6）。**`VALID_SENSORS` 是从 `CAMERA_RIGS` 派生的**，
加一个相机只需要改一个地方。

**语义分割的类别表是唯一真相源**（`sensors/seg_classes.py`，10 类，CARLA/Cityscapes 配色）。
Panda 用 `SEG_RENDER_COLORS` 给 flat shader 上色，Blender 用同一份色板给 object.color；
两边渲出来的 seg 图都能用 `seg_color_to_label` 反查成 label-id。

---

## 已知的一处刻意重复

`export/blender_export.py` 里的 `sumo_heading_to_ccw_deg` / `heading_to_vec` /
`front_bumper_to_center` 与 `utils/coordinates.py` 的 `Heading.from_sumo` / `radians_to_vec` /
`Pose.from_front_bumper` **语义等价，是有意的重复实现**：导出这条路径只需要两个几何公式，
不值得为此把 numpy + shapely 拖进来。

代价是改朝向约定时两边都要动。兜底是 `test/test_export_geometry_equivalence.py`——
它逐值比对两份实现，一旦漂移立刻失败。
