'''
Author: WANG Maonan
Date: 2025-06-18 13:02:17
LastEditTime: 2026-08-17
LastEditors: WANG Maonan
Description: Blender/Cycles 离线高精度渲染后端 (只负责「渲染」).

这里的所有模块都 `import bpy`, 只能在 Blender 内运行 (blender --background --python ...),
不会被 tshub 主进程导入 —— 因此本包不做任何顶层 import (装不了 bpy 的环境下也能被扫到).

  render_episode.py  在场景 .blend 内渲染剧集 (每帧摆车 + 布相机 + 出图)
  weather.py         天气 (雾 / 雨): 光照修正 + 湿路面材质 + 合成器
  render_passes.py   RGB 之外的通道: 语义分割 (seg) 与深度 (depth)

前置产物由「生成」那一侧提供 (`tshub_env3d/scene/blender/`):
  build_scene.py     scene.json -> 分类 glb
  build_blend.py     glb -> 可复用的场景 .blend (导入场景 + 打光 + 渲染设置)
  scene_assembly.py  装配库 —— render_episode.py 也复用它 (通过 sys.path 引入)

剧集数据由 tshub 侧的 core.export.BlenderEpisodeExporter 导出; 三步串起来见
examples/tshub_env3d/single_junction/render_blender.py.
'''
