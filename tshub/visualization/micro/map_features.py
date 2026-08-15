'''
@Author: WANG Maonan
@Date: 2023-11-12 16:20:15
@Description: 对地图元素的可视化
路网的线段数很大 (香港九龙的路网有 3 万多条), 逐条创建 Line2D 会让一帧要十几秒,
因此这里把所有线段塞进一个 LineCollection 一次性交给 matplotlib (实测快 30 倍以上)。
@LastEditTime: 2026-08-12 10:00:00
'''
from typing import Any, Dict, List, Tuple

from matplotlib.collections import LineCollection


def build_map_segments(map_polygons: Dict[str, Any]) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """把若干多边形拆成 LineCollection 需要的线段列表.

    每个多边形首尾相连 (从 shape[-1] -> shape[0] 开始), 与原先逐段画线的效果一致。
    """
    segments = []
    for polygon_info in map_polygons.values():
        shape = polygon_info.get('shape')
        if not shape:
            continue
        for index in range(len(shape)):
            start, end = shape[index - 1], shape[index]
            segments.append(((start[0], start[1]), (end[0], end[1])))
    return segments


def make_map_collections(map_edges: Dict[str, Any],
                         map_nodes: Dict[str, Any]) -> List[LineCollection]:
    """构建路网的静态图层 (车道 + 路口), 返回可直接 add_collection 的对象.

    路网在仿真过程中不变, 所以调用方应该缓存这里的结果, 每帧只重画车辆。
    """
    collections = []
    edge_segments = build_map_segments(map_edges)
    if edge_segments:
        collections.append(LineCollection(edge_segments, linewidths=1, colors='grey', linestyles='-'))
    node_segments = build_map_segments(map_nodes)
    if node_segments:
        collections.append(LineCollection(node_segments, linewidths=3, colors='grey', linestyles='--'))
    return collections


def plot_map_feature(ax, map_edges, map_nodes) -> None:
    """把路网画到 ax 上 (保留原有接口; 每帧都调用会重复构建, 建议用 make_map_collections 缓存)"""
    for collection in make_map_collections(map_edges, map_nodes):
        ax.add_collection(collection)
