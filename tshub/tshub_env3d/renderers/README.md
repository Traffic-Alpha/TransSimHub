# renderers —— 把场景画出来

两个后端，定位完全不同：

| | **panda/** | **blender/** |
|---|---|---|
| 用途 | 在线：每个仿真步返回传感器图像，喂给 RL/感知 | 离线：批量出写实图，做展示/数据集 |
| 引擎 | Panda3D + simplepbr（光栅） | Blender Cycles（路径追踪，GPU） |
| 速度 | ~17 ms / 相机（720P） | ~3.5 s / 相机（720P, 32 spp, RTX 4090） |
| 画风 | 快、够用，不追写实 | 写实：物理天空、真实阴影、AgX |
| 怎么被调用 | `create_renderer('panda')`，实现 `core.RendererBackend` | `blender --background --python …`，**不**实现该接口 |
| 能否 import | 可以 | **不能**（`import bpy`，只在 Blender 里跑） |

两边共用 `core/` 的同一份定义（相机 rig、语义类别、车模映射），所以两条路径的画面可比、标签可比。
core 提供了什么，见 [`core/README.md`](../core/README.md)。

---

## panda/ —— 在线后端

### 一步做了什么

```
TSHubRenderer.sync(frame)                       tshub_render.py
   └─ SceneSync._sync(frame)                    rendering_components/scene_sync.py
        ├─ update_elements(frame)               增/改车辆与飞行器 element
        ├─ remove_missing_elements(...)         删掉本帧不在场的
        ├─ taskMgr.step()                       让相机跟着载体走
        ├─ graphicsEngine.renderFrame()         ← 全场景只渲这一次
        └─ collect_sensors(tls / vehicle / aircraft)
                 └─ RGBSensor.__call__() → 从显存读回像素
```

`reset(static)` 时另做一次性的事：按 `static.tls_rigs` 建路口相机、清空动态节点。
静态场景（glb / 天空 / 灯光 / IBL）在**构造时**由 `SceneLoader` 一次装好，之后不再碰。

### 目录

```
panda/
├── tshub_render.py            TSHubRenderer：实现 core.RendererBackend
├── _showbase_instance.py      Panda ShowBase 单例（进程内全局唯一）+ prc 配置
├── rendering_components/
│   ├── scene_loader.py        一次性加载 7 类静态 glb + skybox + 灯光 + IBL，逐类打 seg 标签
│   └── scene_sync.py          每步对账：增删改 element → 渲染 → 读回
├── traffic_elements/          三类载体
│   ├── base_element.py            位姿换算 + 挂载/读取传感器（共用逻辑都在这）
│   ├── vehicle.py / aircraft.py   有 3D 实体
│   └── traffic_signals.py         只是相机挂载点（三个 node 方法是空的，保持接口统一）
├── sensors/
│   ├── rgb_sensor.py                    传感器：持有相机 + 读回像素（seg 时转 label-id）
│   └── cameras/build_offscreen_camera.py 按 rig 建离屏 buffer + 相机（透视/正交、MSAA）
└── segmentation.py            seg 的 tag-state：给带标签的节点套 flat shader
```

### 天空风格 `sky='day' | 'dust'`

`Tshub3DEnvironment(sky=...)` 选一档，**同时**决定天空渐变与打光（`scene_loader.SKY_STYLES`）：
day 中性偏冷，dust 天空沙黄 + 主光变暖变弱 + 太阳压低。

> 早先 `sky` 只换天空渐变，地面受光完全不变（实测 day/dust 地面**逐字节相同**），
> 因为灯光颜色是写死的、且 simplepbr 的 IBL 被 `setShaderAuto()` 压掉了（详见 `load_sky_box` 注释）。
> 现在灯光并进了同一档，dust 才真的像沙尘天（地面 MAD 0.00 → 13.3）。

### 分辨率

`preset` 选画幅：`320P / 480P / 720P / 720P_SQUARE / 1080P`；`resolution` 是透视相机的 film 缩放。
BEV / 路口俯视这类正交相机建议用 `720P_SQUARE`。

### 两个性能上的坑（已修，改的时候别踩回去）

1. **读回像素前不要无条件补渲。** `_sync` 已经对整个场景 `renderFrame()` 过一次，
   `wait_for_ram_image` 应当**先查 `mightHaveRamImage()`**，只在缺失时才补渲。
   无条件补渲 = 每个相机白渲一整帧（实测 720P 6 相机 116ms → 54ms，约 2.2×）。
2. **必须单线程。** prc 里 `threading-model = ""`（原为 `"Cull/Draw"`）。
   这条和上一条**是耦合的**：多线程下 `renderFrame` 是异步的，「先查后取」会拿到**上一帧**的残留图，
   差一帧且极难发现。单线程下 renderFrame 阻塞到读回完成，才既正确又快。

3. **车辆模型走实例池，别每辆车 loadModel。** `panda/model_pool.py` 每个 glb 只加载一次，
   之后 `instanceTo` 共享几何：每辆新车从 ~6.5 ms 降到 **0.03 ms**，显存里也只有一份网格。
   包围盒尺寸同样按模型缓存（`model_dimensions`，原来每辆车 `getBounds()` 要 ~6 ms）。
   代价：几何共享，**不要对单辆车改材质/颜色**（会影响同款所有车）。
   注意首次加载某车型仍要 ~86 ms（读盘+解析），会在剧集前段造成几次卡顿——
   真要平滑可以在 setup 阶段预热全部车模（约 20 个模型 ≈ 1.7 s）。

> 另外两个试过没用的方向（别重复踩）：离屏 buffer 的 AuxRgba/Stencil 去掉**零收益**（simplepbr 会用到）；
> 调低 MSAA 也**零收益**——离屏 sensor buffer 本来就没开全局 MSAA。剩下的开销主要是 GPU→CPU 同步读回。

---

## blender/ —— 离线后端

它只负责**渲染**。场景 `.blend` 的生成属于「生成」那一侧，在
[`scene/blender/`](../scene/README.md)（`build_scene.py` → glb，`build_blend.py` → scene.blend）。

```
blender/
├── render_episode.py   在 scene.blend 里渲一段剧集：每帧摆车 + 布相机 + 出图
├── weather.py          天气：clear / fog / rain（光照修正 + 湿路面材质 + 合成器）
└── render_passes.py    RGB 之外的通道：seg（语义分割）与 depth（米制 EXR）
```

### 怎么跑

```bash
# 1) tshub 侧导出剧集（纯 SUMO，不需要任何渲染后端）
#    core.export.BlenderEpisodeExporter → manifest.json + frames/NNNN.json
# 2) 在场景 .blend 里渲染
blender --background scene.blend --python tshub/tshub_env3d/renderers/blender/render_episode.py -- \
        <episode_dir> <out_dir> --frames 0:40:5 --samples 64 \
        --style day --weather rain --passes rgb
```

`--passes` 的每个通道都是**独立**的：`--passes seg` 就只出 seg，不会顺带渲一遍 rgb。
多个通道时**优先每个通道各起一次 Blender**（一次只给一个通道），比 `--passes rgb,seg`
挤在同一次里快得多——见下面「性能」第 2 条。

驱动示例：`examples/tshub_env3d/single_junction/render_blender.py` —— 它只做两件事：
导出剧集（一次）+ 逐个 `--style × --weather` 组合渲染（每个通道各起一次 Blender，
`--fused-passes` 可退回旧的「一次跑多通道」）。**场景 `.blend` 不在这里生成**，
由 `build_static_scene.py` 一次性产出到 `3d_assets/`，所有组合共用。

输出 `<out>/<element>/<sensor 基名>_{rgb,seg,depth}/NNNN.{png,png,exr}`。

### 三个通道的代价结构不一样

- **rgb**：正常 Cycles 渲染，最贵（~3.5 s @32 spp）。
- **seg**：单独渲一遍，但**只要 1 个样本**——用 `material_override` 把全场景换成「自发光 = 物体颜色」，
  每个物体的 `object.color` 设成类别色，一趟就得到每像素严格等于类别色的图（~1.9 s）。
- **depth**：也是单独一遍 1 样本（深度是「第一次命中」的几何量，与光照无关），输出 32 位单层 EXR，
  单位**米**、不归一化（~1.8 s）。

seg 渲染时必须关掉的东西（漏一个就会污染标签）：抗锯齿滤波、**dither**、降噪、间接光、AgX、天气合成器。
其中 dither 最阴——8 位输出的 ±1 抖动会让 16% 的像素反查不到类别。

### 两个 Blender 5 的坑

- **File Output 节点只能写多层 EXR**（`format.file_format` 运行时枚举被锁死），cv2/imageio 都读不了，
  所以 depth 没能做成「随 rgb 白送」，只能单独渲一遍。
- EXR 用 `color_mode='BW'` 写出的通道名是 `V`，**OpenCV 只认 R/G/B/Y**，会读成 `None`；
  所以用 `RGB`（三通道同值）。

### 性能（这条流水线最容易踩的坑）

1. **必须开 `use_persistent_data`。** 静态场景整段不变，但 Cycles 默认**每次 `render()` 都重新导出
   场景 + 重建 BVH**，而我们每帧要 render「相机数 × 通道数」次。
   实测：single_junction（255 物体）1932 ms → 276 ms；ymt（4690 物体）**5072 ms → 246 ms（20.6×）**。
   代价是常驻内存变高，对「静态场景 + 少量动态物体」完全划算。
2. **一次只渲一个通道，多通道分多次进程跑。** 实测（101 帧 × 1 相机，1022×1022，8 spp，4090）：

   | passes | 出图 | 渲染循环 | s/帧 | s/图 |
   |---|---|---|---|---|
   | `rgb` | 101 | 143.1 s | 1.417 | 1.417 |
   | `seg` | 101 | 47.7 s | 0.472 | 0.472 |
   | `rgb,seg` | 202 | 302.9 s | 2.999 | 1.500 |

   分开跑合计 190.8 s，挤在一次里 302.9 s——**贵 59%**（Blender 启动 + 加载 `.blend` 约 1.5 s，
   可忽略）。贵的不是切换本身：只渲 rgb 但每帧照常 `assign_seg_colors()` + 进出一次 `seg_mode()`
   的对照组是 145.9 s，只慢 2%。真正的原因是 **rgb 与 seg 交替渲染时每次渲染看到的
   `material_override` 都不同，`use_persistent_data` 的缓存每渲一次就失效一次**，两个通道都要付
   全量场景重导出。
   所以：**同一次进程里只给一个通道**（`render_episode.py` 检测到这种情况会把通道状态提到整段
   循环之外，全程不再动场景），多通道由驱动脚本分次调用 Blender。
   一次里确实要渲多个通道时（`--fused-passes`），仍然**按通道分组、别按相机**：按相机循环每帧要切
   `2 × 相机数` 次状态，按通道分组只切 2 次，实测 5 相机 × 3 通道 17.0 → **12.1 s/帧**。
   （早先「整段先渲完 rgb 再整段 seg 只快 2.5%」的结论不冲突：那是 5 相机 × 3 通道测的，
   每次状态切换摊到 5 次渲染；上表 N=1 时每一次渲染都会让缓存失效。）
3. **seg 着色要增量。** `assign_seg_colors` 只在首帧给静态物体上色（大图上几千个），
   之后每帧只处理车辆/飞行器与新导入的车模模板。
4. **要更快就开多进程按帧段切分**（不是按通道）。同一块 4090 上实测 6 帧 × 3 通道：
   1 进程 50.3 s → 2 进程 40.4 s → 3 进程 34.6 s（扣掉每进程 ~7 s 启动后约 1.6×）。
   收益来自「一个进程在 CPU 侧同步场景时，另一个进程正在用 GPU 渲染」；再多进程受限于 GPU 本身。

### 跨包引用

`render_episode.py` 需要 `scene/blender/scene_assembly.py`（相机布置、模型实例化）。
这些脚本是被 `blender --python` **直接执行**的，不是包导入，所以用一行带注释的
`sys.path.insert(…, '../../scene/blender')` 引进来。

---

## 加一个新后端

1. 实现 `core.RendererBackend` 的 `reset(static) / sync(frame) / destroy()`；
2. 在 `renderers/__init__.py` 的 `create_renderer` 里加一个分支（**懒加载**：只在选中时才 import 它的依赖），
   并把名字加进 `AVAILABLE_RENDERERS`。

`sync()` 返回的结构由后端自己定（Panda 返回 `{element_id: {sensor_type: image}}`），上层不解释。

---

## 关于可见性 mask

以前 Panda 侧有一套 `CamMask`（车辆/环境/地面/天空/飞行器各一个 bit），
用来支持 `_all` / `_vehicle` 两种可见性——后者渲染「黑底上只有车」的前景掩码图。

**这套机制已整体删除**：seg 改用 per-class shader 之后，每台相机都渲染整个场景，
rgb 给外观、seg 给标注，「谁能看见谁」这个维度不再有意义。删除时验证过 116 张图逐像素一致（MAD=0）。

将来若真需要按相机控制可见性，**加在相机侧**（`setCameraMask`）即可，不要恢复「每个节点 hide/show」的骨架。
