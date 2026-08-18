'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 静态场景生成的**对外入口** (Stage 1, 在 tshub 环境里跑).

SUMO .net.xml -> scene.json. 本文件只做参数转发, 实现分别在
road_network/ (路网几何) 与 scene_data/ (数据组装).

输入分两种模式, 由 buildings_poly 决定:
- **带 poly**  : 额外给 map.poly.xml (tshub.sumo_tools.osm_build 产出),
                 建筑用真实 OSM 轮廓 + 真实高度挤出, 绿地里额外种树;
- **不带 poly**: 只有路网, 建筑改为沿街摆放装饰模型 (观感优先, 尺寸不求真).
两种模式的路面/车道线/转向箭头/路边小物件完全一致.
@LastEditTime: 2026-08-18
'''
from .road_network import SumoNet3D
from .scene_data import build_static_scene_data, write_static_scene_json


def export_scene_geometry(net_file: str, out_json: str,
                          buildings_poly: str = None,
                          building_level_height: float = 3.2,
                          apron_width: float = 5.0) -> str:
    """从 SUMO net 提取道路三角网格 + 路缘带 + 车道/边线 + 包围盒 (+ 可选建筑轮廓), 写出 JSON.

    Args:
        buildings_poly: 可选, SUMO map.poly.xml. 建筑轮廓和 height/levels
            参数都只从该文件读取.
        building_level_height: 每层楼对应的米数, 用于 poly param
            building:levels -> height.
        apron_width: 路缘灰色铺装带相对道路向外扩展的宽度 (米).
    Returns: out_json 路径.
    """
    net = SumoNet3D(net_file)
    data = build_static_scene_data(
        net,
        buildings_poly=buildings_poly,
        building_level_height=building_level_height,
        apron_width=apron_width,
    )
    return write_static_scene_json(data, out_json)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description="导出 SUMO net 静态几何为 JSON (供 Blender 构建)")
    ap.add_argument('net_file')
    ap.add_argument('out_json')
    ap.add_argument('--buildings', default=None, help="map.poly.xml (建筑轮廓 + height/levels params)")
    ap.add_argument('--building-level-height', type=float, default=3.2,
                    help="building:levels 每层对应米数")
    args = ap.parse_args()
    export_scene_geometry(
        args.net_file, args.out_json,
        buildings_poly=args.buildings,
        building_level_height=args.building_level_height,
    )
    print(f"scene geometry -> {args.out_json}")
