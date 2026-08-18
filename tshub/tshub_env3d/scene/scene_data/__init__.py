'''
@Author: WANG Maonan
@Date: 2026-08-17
@Description: 几何 + OSM + 道具摆放 -> scene.json 数据 (scene 的内部实现之一).

对外只暴露总装函数, 对应入口是 scene.scene_export:
    build_static_scene_data / write_static_scene_json

内部按「是否依赖 poly 输入」分成三类:
    road_surface.py   路面 / 路缘铺装带 的三角网格        ← 两种输入共用
    lane_markings.py  车道转向箭头                        ← 两种输入共用
    osm_poly.py       map.poly.xml -> 建筑轮廓+高度 / 绿地 ← **仅「带 poly」**
    scatter.py        树 / 小物件 (共用) + 沿街建筑        ← 建筑仅「不带 poly」
    static_scene.py   总装, 两种输入在这里分流
'''
from .static_scene import build_static_scene_data, write_static_scene_json

__all__ = ['build_static_scene_data', 'write_static_scene_json']
