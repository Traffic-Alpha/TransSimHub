'''
@Author: WANG Maonan
@Date: 2026-08-18
@Description: 车道转向箭头 (两种输入模式共用).

方向码 (s/l/r/t) 直接取自 SUMO 的 connection direction —— 与 tshub 信号灯那边用的是
同一套语义, 这里只负责把它摆到进口车道末端附近, 供 Blender 画成地面箭头。
'''
import math


def _point_back_from_end(shape, distance_back: float):
    """Return a point and heading on a lane shape, measured backward from the end."""
    remaining = distance_back
    for idx in range(len(shape) - 1, 0, -1):
        x1, y1 = shape[idx]
        x0, y0 = shape[idx - 1]
        dx, dy = x1 - x0, y1 - y0
        seg_len = math.hypot(dx, dy)
        if seg_len < 1e-6:
            continue
        if remaining <= seg_len:
            t = (seg_len - remaining) / seg_len
            return (
                [float(x0 + dx * t), float(y0 + dy * t)],
                float(math.atan2(dy, dx)),
            )
        remaining -= seg_len

    x0, y0 = shape[0]
    x1, y1 = shape[1]
    return [float(x0), float(y0)], float(math.atan2(y1 - y0, x1 - x0))


def _movement_direction_to_turn(direction: str) -> str:
    """Map SUMO/tshub movement direction codes to renderer-facing names."""
    return {
        "s": "straight",
        "l": "left",
        "L": "left",
        "r": "right",
        "R": "right",
        "t": "uturn",
        "T": "uturn",
    }.get(direction, "unknown")


def extract_lane_turn_markings(sumo_net, base_distance: float = 9.0) -> list:
    """Extract lane-level turn arrows from SUMO/tshub movement directions.

    Direction codes are the same movement codes used by tshub traffic-light
    helpers (s/l/r/t).  This function only places those existing semantics near
    the end of the incoming lane for visualization.
    """
    turn_order = {"right": 0, "straight": 1, "left": 2, "uturn": 3, "unknown": 4}
    markings = []

    for edge in sumo_net._graph.getEdges():
        if edge.getFunction() == "internal":
            continue

        for lane in edge.getLanes():
            shape = lane.getShape()
            if len(shape) < 2:
                continue

            movement_pairs = [
                (direction, _movement_direction_to_turn(direction))
                for direction in {conn.getDirection() for conn in lane.getOutgoing()}
            ]
            movement_pairs = [
                (direction, turn)
                for direction, turn in movement_pairs
                if turn != "unknown"
            ]
            movement_pairs = sorted(
                movement_pairs,
                key=lambda item: turn_order.get(item[1], turn_order["unknown"]),
            )
            if not movement_pairs:
                continue

            center, heading = _point_back_from_end(shape, base_distance)
            directions = [direction for direction, _turn in movement_pairs]
            turns = [turn for _direction, turn in movement_pairs]
            markings.append(
                {
                    "lane_id": lane.getID(),
                    "movement_direction": "+".join(directions),
                    "movement_directions": directions,
                    "turn": "+".join(turns),
                    "turns": turns,
                    "center": center,
                    "heading": heading,
                    "lane_width": float(lane.getWidth()),
                }
            )
    return markings
