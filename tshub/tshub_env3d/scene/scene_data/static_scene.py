'''
@Author: WANG Maonan
@Date: 2026-07-10
@Description: 把各部分组装成 scene.json (scene_data 的总装环节).

这一层只做两件事: 调用各模块拿到纯数据, 以及**按输入模式分流**.
Blender (Stage 2) 只消费这里输出的 dict, 不关心它是怎么来的.

两种输入模式 (由 buildings_poly 是否给出决定):

  ┌ 带 poly (OSM) ──────────────────────────────────────────────┐
  │  data['buildings']    = 真实建筑轮廓 + 高度 (osm_poly)        │
  │                         -> Blender 按轮廓挤出灰模, 尺寸真实   │
  │  scatter['trees']     = 沿街树 + 绿地内的树                   │
  │  scatter['buildings'] = 空 (已有真实建筑, 不再摆装饰模型)     │
  └─────────────────────────────────────────────────────────────┘
  ┌ 不带 poly ──────────────────────────────────────────────────┐
  │  data['buildings']    = 空                                   │
  │  scatter['buildings'] = 沿街摆放的建筑资产 (scatter)          │
  │                         -> Blender 实例化模型, 只求观感       │
  │  scatter['trees']     = 只有沿街树 (没有绿地信息)             │
  └─────────────────────────────────────────────────────────────┘

其余部分 (路面/路缘/车道线/边线/转向箭头/路边小物件) 两种模式完全一样.
@LastEditTime: 2026-08-18
'''
import json
from pathlib import Path

from .road_surface import build_road_meshes, polylines_to_json
from .lane_markings import extract_lane_turn_markings
from .osm_poly import parse_buildings, parse_green_areas
from .scatter import build_scatter


def build_static_scene_data(
    sumo_net,
    buildings_poly: str = None,
    building_level_height: float = 3.2,
    apron_width: float = 5.0,
) -> dict:
    """组装 Blender build_scene.py 消费的静态场景纯数据.

    Args:
        sumo_net: SumoNet3D 实例.
        buildings_poly: 可选, SUMO map.poly.xml. 给了就是「带 poly」模式,
            建筑轮廓与高度 (height / building:levels) 都只从该文件读.
        building_level_height: 每层楼对应的米数 (OSM building:levels 换算用).
        apron_width: 路缘硬质铺装带相对道路向外扩展的宽度 (米).
    """
    # --- 与输入模式无关的部分: 路面 / 路缘 / 车道线 / 转向箭头 ---
    road_polys = sumo_net._compute_road_polygons()
    lane_dividers, edge_borders = sumo_net._compute_traffic_dividers()
    bbox = sumo_net.bounding_box
    bbox_list = [bbox.min_pt.x, bbox.min_pt.y, bbox.max_pt.x, bbox.max_pt.y]

    roads, apron = build_road_meshes(road_polys, apron_width)
    data = {
        'bbox': bbox_list,
        'roads': roads,
        'apron': apron,
        'lane_dividers': polylines_to_json(lane_dividers),
        'edge_borders': polylines_to_json(edge_borders),
        'turn_markings': extract_lane_turn_markings(sumo_net),
        'buildings': [],
    }

    # --- 分流: 带 poly 时才有真实建筑轮廓与绿地 ---
    greens = []
    if buildings_poly:
        data['buildings'] = parse_buildings(
            buildings_poly,
            building_level_height=building_level_height,
        )
        greens = parse_green_areas(buildings_poly)

    # --- 道具摆放: 树/小物件两种模式都有; 建筑仅在「不带 poly」时由这里摆 ---
    data['scatter'] = build_scatter(road_polys, data['buildings'], greens, bbox_list)
    return data


def write_static_scene_json(data: dict, out_json: str) -> str:
    """把静态场景数据写成紧凑 JSON, 返回输出路径."""
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(data))
    return out_json
