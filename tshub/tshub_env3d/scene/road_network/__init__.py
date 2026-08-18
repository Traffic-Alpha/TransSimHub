'''
@Author: WANG Maonan
@Date: 2026-08-17
@Description: SUMO 路网 -> 道路几何 (scene 的内部实现之一).

`SumoNet3D` 把 .net.xml 解析成可查询的路网对象, 并给出建场景要用的两样几何:
- `_compute_road_polygons()`  每条车道 buffer 成路面多边形 (含三处 snap 补缝)
- `_compute_traffic_dividers()` 车道分隔线 / 道路边线折线

内部再分一层:
- map_elements/ : SMARTS 派生的 RoadMap/Lane/Road/Surface/Feature 抽象与 SUMO 实现
- geometry.py   : 折线 -> 带宽度多边形 的 shapely 工具

对外请走 scene.scene_export; 只有需要直接查路网 (最近车道/路段等) 时才用到这里.
'''
from .sumo_net import SumoNet3D

__all__ = ['SumoNet3D']
