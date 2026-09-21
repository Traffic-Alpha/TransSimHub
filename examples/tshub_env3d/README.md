<!--
 * @Author: WANG Maonan
 * @Date: 2026-08-17 19:59:57
 * @Description: TSHub Env3D 示例
 * @LastEditTime: 2026-08-19 21:57:41
 * @LastEditors: WANG Maonan
-->
# TSHub Env3D 示例

## 查看生成的 Blender 场景

生成的 `.blend` 文件可以直接用 Blender 打开。静态场景对象会被导入到
`map`、`ground`、`road_lines`、`lane_lines`、`buildings`、`vegetation`
和 `props` 等 collection 中。

如果打开 `.blend` 后没有看到模型，通常不是模型缺失，而是场景不在默认视图范围内。
可以按下面的方式查看：

1. 用 Blender 打开生成的 `.blend` 文件。
2. 按 `A` 选择全部对象。
3. 按 `Home` 将完整场景框入当前视图。
4. 也可以在 Outliner 中选中 `buildings` 或 `map` 等 collection，然后按小键盘
   `.` 聚焦到该 collection。
5. 如果场景仍然被裁剪，可以调大 viewport 的 `Clip End`，例如设置为 `5000`
   或 `10000`。

当前示例生成的场景文件：

- `single_junction/3d_assets/scene.blend`
- `ymt_area/3d_assets/scene.blend`

两者都由各自目录下的 `build_static_scene.py` 生成，**只需生成一次**；
`render_blender.py` 直接复用它渲染，不会重新建场景。

部分生成的 `.blend` 文件可能没有设置 camera。这种情况下请使用上面的 viewport
聚焦方式查看，而不是直接从 camera view 查看。

## Blender 离线渲染的输出通道 (rgb / seg / depth)

三个通道互相独立，可以单独渲，也可以一次要多个：

```bash
python examples/tshub_env3d/single_junction/render_blender.py --passes rgb     # 只出 RGB (默认)
python examples/tshub_env3d/single_junction/render_blender.py --passes seg     # 只出语义分割
python examples/tshub_env3d/single_junction/render_blender.py --passes depth   # 只出深度 (EXR, 米)
python examples/tshub_env3d/single_junction/render_blender.py --passes rgb,seg,depth
```

`--passes seg` 就**只**渲 seg，不会顺带渲一遍 rgb。要多个通道时，脚本默认**每个通道各起一次
Blender**（一次只渲一个通道），因为这样明显更快；`--fused-passes` 可以退回「一次跑完所有通道」
的旧行为（用于对照）。剧集只导出一次，`.blend` 也是同一个，多起几次 Blender 不会重跑仿真。

### 为什么要拆开渲

测试对象：Beijing_Beihuan，复用已有的 0–100s blender json（101 帧，1 个 junction BEV 相机，
1022×1022，samples=8，Cycles GPU / RTX 4090）。

| passes    | 出图 | 渲染循环 | s/帧  | s/图  |
|-----------|------|----------|-------|-------|
| `rgb`     | 101  | 143.1s   | 1.417 | 1.417 |
| `seg`     | 101  | 47.7s    | 0.472 | 0.472 |
| `rgb,seg` | 202  | 302.9s   | 2.999 | 1.500 |

Blender 启动 + 加载 scene.blend 约 1.5s，可忽略。

主要发现：`rgb,seg` 一次跑（302.9s）比分成两次跑（143.1 + 47.7 = 190.8s）贵 59% —— 拆开渲能省掉
37% 的时间。

补做了一个对照来定位原因：只渲 rgb，但每帧照常 `assign_seg_colors()` + 进出一次 `seg_mode()`，
结果 145.9s，只比纯 rgb 多 2.0%（约 28ms/帧）。所以贵的不是切换本身，而是 rgb 与 seg 两次渲染交替
进行 —— 每次渲染看到的 `material_override` 状态都不同，Cycles 的 `use_persistent_data` 缓存每渲一次
就失效一次，两个 pass 都要付全量场景重导出。

这一点和上游 `render_episode.py` docstring 里"整段分组只快 2.5%"的结论不冲突：它是 5 相机 × 3 通道
测的，每次状态切换摊到 5 次渲染；这里 N=1，每一次渲染都会让缓存失效。

据此 `render_episode.py` 里还做了一步：**一次只渲一个非 rgb 通道时，把通道状态切换提到整段循环
之外**（`[render] passes: seg (整段单通道)`），全程 `material_override` 不再变动。输出与逐帧切换
完全一致（seg / depth 逐字节相同，rgb 因 Cycles 采样抖动最多差 1/255）。