'''
@Author: WANG Maonan
@Date: 2024-07-03 23:28:34
@Description: 静态场景的「生成」—— 跑仿真之前做一次, 产出可复用的场景产物.

┌─ 对外接口 ────────────────────────────────────────────────────────────┐
│  scene_export.export_scene_geometry(net_file, out_json, ...)         │
│      SUMO .net.xml -> scene.json                                     │
│      也可当 CLI: python -m tshub.tshub_env3d.scene.scene_export ...  │
│                                                                      │
│  两种输入模式 (给不给 buildings_poly):                                │
│    带 poly   -> 真实 OSM 建筑轮廓+高度, 绿地内种树 (osm_poly.py)      │
│    不带 poly -> 沿街摆放装饰建筑模型 (scene_data/scatter.py)          │
└──────────────────────────────────────────────────────────────────────┘

后两步在 Blender 内跑 (Blender 的 python 装不了 sumolib/shapely, 所以必须分开),
由 CLI 直接执行脚本, 不通过 import:
    blender --background --python scene/blender/build_scene.py -- scene.json out_dir
        -> map / ground / road_lines / lane_lines / buildings / vegetation / props .glb
    blender --background --python scene/blender/build_blend.py -- glb_dir out.blend
        -> scene.blend (导入场景 + 打光 + 渲染设置, 可复用、可手工微调)

内部实现 (按用途分层, 一般不需要直接 import):
    road_network/   SUMO 路网 -> 道路几何 (SumoNet3D + map_elements/ + geometry 工具)
    scene_data/     几何 + OSM + 道具摆放 -> scene.json 数据 (static_scene + scatter)
    blender/        上面两个 bpy 脚本 + 共享装配库 scene_assembly.py

产出的 glb 目录喂给 `Tshub3DEnvironment(scenario_glb_dir=...)` (Panda 在线渲染);
scene.blend 喂给 renderers/blender 的离线渲染.
@LastEditTime: 2026-08-17
'''
from .scene_export import export_scene_geometry

__all__ = ['export_scene_geometry']
