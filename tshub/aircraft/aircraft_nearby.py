'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 查询 UAV 附近有哪些地面对象 (空地协同的关联查询)
- 纯函数, 只吃 obs, 不依赖 SUMO / panda3d, 因此中观大屏和 3D 渲染都能用;
- UAV 自己挂载的相机是常驻渲染的 (见 sensor_config['aircraft']),
  这里回答的是「这一帧 UAV 拍到的大概是哪些对象」, 用于大屏高亮与图像关联。

距离一律在 XY 平面上算 (忽略飞行高度): UAV 在 100m 高空俯拍时, 正下方的车辆
在三维空间里就有 100m 距离, 用三维距离会把它判成「不在附近」, 与直觉相反。
@LastEditTime: 2026-08-11 10:00:00
'''
import math
from typing import Any, Dict, List, Optional


def find_objects_near_aircraft(
        tshub_obs: Dict[str, Any],
        radius: float = 100.0,
        targets: Optional[List[str]] = None,
        aircraft_ids: Optional[List[str]] = None,
        max_per_type: Optional[int] = None,
    ) -> Dict[str, Dict[str, List[str]]]:
    """找出每架 UAV 附近 (XY 平面半径内) 的地面对象.

    Args:
        tshub_obs: TshubEnvironment 的观测, 需要 obs['aircraft']; 按 targets 需要
            obs['vehicle'] / obs['tls'].
        radius (float, optional): 判定半径 (m). Defaults to 100.0.
        targets (List[str], optional): 要找的对象类型, 支持 'vehicle' / 'tls'。
            为 None 时两者都找。Defaults to None.
        aircraft_ids (List[str], optional): 只考虑这些 UAV, 为 None 表示全部。Defaults to None.
        max_per_type (int, optional): 每类最多返回几个 (按距离从近到远)。
            为 None 表示不限制。Defaults to None.

    Returns:
        Dict[str, Dict[str, List[str]]]: {aircraft_id: {'vehicle': [...], 'tls': [...]}},
            每类的 id 按距离从近到远排序。没有 aircraft 时返回空 dict。
    """
    if targets is None:
        targets = ['vehicle', 'tls']

    aircraft_obs = tshub_obs.get('aircraft', {})
    if aircraft_ids is not None:
        aircraft_obs = {
            aircraft_id: info
            for aircraft_id, info in aircraft_obs.items() if aircraft_id in aircraft_ids
        }
    if not aircraft_obs:
        return {}

    # 先把候选对象的平面坐标取出来, 避免对每架 UAV 重复解析
    candidates = {
        target_type: _collect_positions(tshub_obs, target_type)
        for target_type in targets
    }

    nearby = {}
    for aircraft_id, aircraft_info in aircraft_obs.items():
        position = aircraft_info.get('position')
        if position is None:
            continue
        aircraft_x, aircraft_y = float(position[0]), float(position[1])

        result = {}
        for target_type, positions in candidates.items():
            hits = []
            for object_id, (x, y) in positions.items():
                distance = math.hypot(x - aircraft_x, y - aircraft_y)
                if distance <= radius:
                    hits.append((distance, object_id))
            hits.sort()  # 由近及远
            if max_per_type is not None:
                hits = hits[:max_per_type]
            result[target_type] = [object_id for _distance, object_id in hits]
        nearby[aircraft_id] = result

    return nearby


def _collect_positions(tshub_obs: Dict[str, Any], target_type: str) -> Dict[str, tuple]:
    """取出某类对象的平面坐标 {object_id: (x, y)}"""
    positions = {}

    if target_type == 'vehicle':
        for vehicle_id, info in tshub_obs.get('vehicle', {}).items():
            position = info.get('position')
            if position is not None:
                positions[vehicle_id] = (float(position[0]), float(position[1]))

    elif target_type == 'tls':
        # 信号灯没有直接的坐标, 用各进口道停车线中点的质心作为路口中心
        for tls_id, info in tshub_obs.get('tls', {}).items():
            stop_lines = info.get('in_road_stop_line') or {}
            centers = [
                _center(points) for points in stop_lines.values() if points
            ]
            centers = [center for center in centers if center is not None]
            if centers:
                positions[tls_id] = _center(centers)

    return positions


def _center(points) -> Optional[tuple]:
    """一组坐标点的中心"""
    points = [p for p in points if p is not None]
    if not points:
        return None
    return (
        sum(float(p[0]) for p in points) / len(points),
        sum(float(p[1]) for p in points) / len(points),
    )
