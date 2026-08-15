'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: Static scene geometry export (Stage 1, run in tshub env).

This is the thin CLI/API entry for SUMO net -> JSON.  Geometry extraction lives
in static_scene.py so the direct legacy GLB path and the Blender build path do
not keep growing separate implementations.
@LastEditTime: 2026-07-10
'''
from .sumonet_to_tshub3d import SumoNet3D
from .static_scene import build_static_scene_data, write_static_scene_json


def export_scene_geometry(net_file: str, out_json: str,
                          buildings_poly: str = None, heights_csv: str = None,
                          apron_width: float = 5.0) -> str:
    """从 SUMO net 提取道路三角网格 + 路缘带 + 车道/边线 + 包围盒 (+ 可选建筑轮廓), 写出 JSON.

    Args:
        buildings_poly: 可选, SUMO buildings.poly.xml (建筑轮廓), 用于 env 场景.
        heights_csv: 可选, buildings_*.csv (提供每栋楼高度 sz, 按 id 匹配).
        apron_width: 路缘灰色铺装带相对道路向外扩展的宽度 (米).
    Returns: out_json 路径.
    """
    net = SumoNet3D(net_file)
    data = build_static_scene_data(
        net,
        buildings_poly=buildings_poly,
        heights_csv=heights_csv,
        apron_width=apron_width,
    )
    return write_static_scene_json(data, out_json)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description="导出 SUMO net 静态几何为 JSON (供 Blender 构建)")
    ap.add_argument('net_file')
    ap.add_argument('out_json')
    ap.add_argument('--buildings', default=None, help="建筑轮廓 poly.xml (env 场景)")
    ap.add_argument('--heights', default=None, help="建筑高度 csv (列 name,cx,cy,sx,sy,sz,yaw)")
    args = ap.parse_args()
    export_scene_geometry(args.net_file, args.out_json, args.buildings, args.heights)
    print(f"scene geometry -> {args.out_json}")
