'''
@Author: WANG Maonan
@Date: 2023-11-12 21:56:57
@Description: 计算局部视角的视野窗口

原先这里会把全网的 lane/node/vehicle 逐个与追踪目标做多边形距离计算, 再把范围内的
对象过滤出来交给渲染。这么做有两个问题:
1. 每帧都是 O(全网对象数 x 各自的点数), 大路网上光过滤就要一秒以上;
2. 过滤本身是多余的 —— 渲染时坐标轴会裁剪, 而被保留的集合 (focus_distance 以内)
   本来就是可见集合 (视野只有 focus_distance/2) 的超集。
因此现在只负责算出视野窗口, 「取哪些路网元素」交给空间索引 (spatial_index.py)。
@LastEditTime: 2026-08-12 10:00:00
'''
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

# focus_type (对外的叫法) -> obs 中对应的 key.
# 车道的静态几何在 obs['lane_shape'], 与 obs['lane_state'] (车道的动态交通状态) 区分开
FOCUS_TYPE_TO_OBS_KEY = {
    'lane': 'lane_shape',
    'node': 'node',
    'vehicle': 'vehicle',
}
VALID_FOCUS_TYPES = tuple(FOCUS_TYPE_TO_OBS_KEY)


def calculate_center(points: List[Tuple[float]]) -> Tuple[float, float]:
    """计算 shape 的中心点

    Args:
        points (List[Tuple[float]]): 组成 shape 的坐标点，
            例如: [(x1,y1), (x2,y2), ..., (xn,yn)]

    Returns:
        Tuple[float, float]: shape 的中心点的坐标
    """
    x_coords = [point[0] for point in points]
    y_coords = [point[1] for point in points]
    center_x = sum(x_coords) / len(x_coords)
    center_y = sum(y_coords) / len(y_coords)
    return (center_x, center_y)


def compute_focus_window(
        obs: Dict[str, Any],
        focus_id: str,
        focus_type: str,
        focus_distance: float,
    ) -> Tuple[Optional[List[float]], Optional[List[float]]]:
    """计算追踪目标周围的视野窗口.

    Args:
        obs: 环境的观测, 需要包含 focus_type 对应的 key.
        focus_id (str): 追踪对象的 ID.
        focus_type (str): 追踪对象的类型, 'vehicle' / 'node' / 'lane'.
            其中 'node' (路口) 是固定的, 视野窗口整个 episode 都不会变;
            'vehicle' 则会逐帧移动。
        focus_distance (float): 视野的边长 (m).

    Returns:
        (x_range, y_range); 追踪对象不在场景中时返回 (None, None).
    """
    if focus_type not in FOCUS_TYPE_TO_OBS_KEY:
        raise ValueError(
            f'focus_type can only be {list(VALID_FOCUS_TYPES)}, now is {focus_type}.'
        )

    focus_object = obs[FOCUS_TYPE_TO_OBS_KEY[focus_type]].get(focus_id)
    if focus_object is None:
        logger.warning(f'SIM: 追踪的 {focus_type} {focus_id} 不在场景中.')
        return None, None

    if focus_type == 'vehicle':
        center_point = focus_object['position'][:2]
    else:
        center_point = calculate_center(focus_object['shape'])

    half = focus_distance / 2
    return (
        [center_point[0] - half, center_point[0] + half],
        [center_point[1] - half, center_point[1] + half],
    )
