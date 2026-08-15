'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 把 tshub 的 obs 打包成中观大屏需要的数据
- 静态部分 (build_static_payload): 路网几何, reset 之后传一次;
- 每帧部分 (build_frame_payload): 拥堵指数等, 量化成 uint8 再 base64,
  这样 2000 条边的路网每帧只有几 KB, 而不是几十 KB 的 JSON 浮点数。

量化误差: 值域 [0,1] 映射到 0~255, 往返误差不超过半个量化步长 (约 0.002),
对着色和排序都没有影响。
@LastEditTime: 2026-08-11 10:00:00
'''
import base64
from typing import Any, Dict, List, Optional


def quantize(values: List[float]) -> str:
    """把一组 [0,1] 的值量化成 uint8 并 base64 编码"""
    raw = bytes(max(0, min(255, round(value * 255))) for value in values)
    return base64.b64encode(raw).decode('ascii')


def build_static_payload(obs: Dict[str, Any], poly_limit: int = 8000) -> Dict[str, Any]:
    """构建静态数据 (路网几何), 在 reset 之后调用一次.

    Args:
        obs: TshubEnvironment.reset() 的返回值, 需要包含 obs['lane_shape'] (map builder)
            与 obs['edge_state'] (edge builder)。
        poly_limit: 底图多边形 (建筑等) 的数量上限, 超出就截断, 避免大路网前端卡顿。

    Returns:
        dict: 包含 lane 多边形、lane->edge 归属、edge 顺序、bbox、底图多边形。
    """
    lane_shapes = obs.get('lane_shape', {})
    edge_state = obs.get('edge_state', {})
    lane_state = obs.get('lane_state', {})

    # edge / lane 的顺序在这里固定下来, 之后每帧只传数值, 不再重复传 id
    edge_ids = sorted(edge_state)
    lane_ids = sorted(lane_state)
    edge_index = {edge_id: index for index, edge_id in enumerate(edge_ids)}

    lanes = []
    for lane_id in lane_ids:
        shape_info = lane_shapes.get(lane_id)
        if shape_info is None:
            continue  # 没有几何的车道 (如被跳过的内部车道) 不画
        center = shape_info.get('center_shape')
        width = shape_info.get('width')
        if not center or len(center) < 2 or not width:
            continue
        lanes.append({
            'id': lane_id,
            # 中心线 + 宽度, 而不是边界多边形: 前端要按 Google Maps 的方式画路
            # (灰色描边 + 白色路面 + 上面一条较窄的拥堵色带), 用描线比填多边形自然。
            # 这两个值由 MapBuilder 直接给出 —— 边界多边形是不可逆的, 反推会错。
            'center': [[round(x, 2), round(y, 2)] for x, y in center],
            'width': round(width, 2),
            # 车道所属 edge 在 edge_ids 中的下标, -1 表示该 edge 没有状态数据
            'edge': edge_index.get(shape_info.get('edge_id'), -1),
        })

    # 路口多边形. 不画的话交叉口会是一个个空洞, 路网看着是断的
    nodes = [
        [[round(x, 2), round(y, 2)] for x, y in node_info['shape']]
        for node_info in obs.get('node', {}).values()
        if node_info.get('shape') and len(node_info['shape']) >= 3
    ]

    # 底图: 建筑/绿地/水系的多边形, 让拥堵图有地理参照, 不是悬空的路网。
    # 带上归一化后的类别, 前端才能按 Google Maps 那样分层着色 (水蓝/绿地绿/建筑灰)
    # 分两类收集: 用地/水系/绿地这类「大面积地物」和「建筑物本体」。
    # 截断时优先保住前者 —— 一个城市的 poly 文件里建筑能占九成 (kowloon 是 4550/7304),
    # 若按原始顺序切片, 仅有的几十个水面和公园会被建筑挤掉, 底图就只剩一片灰。
    area_features, buildings = [], []
    for polygon in obs.get('building', {}).values():
        shape = polygon.get('shape')
        kind = _basemap_kind(polygon.get('polygon_type'))
        if not (kind and shape and len(shape) >= 3):
            continue
        item = {'kind': kind, 'shape': [[round(x, 2), round(y, 2)] for x, y in shape]}
        (buildings if kind == 'building' else area_features).append(item)

    basemap = area_features[:poly_limit]
    basemap.extend(buildings[:max(0, poly_limit - len(basemap))])

    # 速度量化用的上限 (全网最高限速), 前端据此把 uint8 还原成 m/s 再换算 km/h
    edge_limits = [edge_state[edge_id].get('max_speed') or 0.0 for edge_id in edge_ids]
    speed_scale = max(edge_limits) if edge_limits else 1.0

    bbox = _compute_bbox(lanes)
    return {
        'bbox': bbox,
        'lanes': lanes,
        'nodes': nodes,
        'edge_ids': edge_ids,
        'lane_ids': [lane['id'] for lane in lanes],
        'edge_names': [edge_state[edge_id].get('street_name', '') for edge_id in edge_ids],
        'edge_limits_kmh': [round(limit * 3.6, 1) for limit in edge_limits],
        'speed_scale': speed_scale or 1.0,
        'basemap': basemap,
    }


# poly 的 type -> 底图类别.
#
# 注意: polyconvert 写进 poly 文件的 type 是 typemap 里的 **name** 而不是 id, 所以这里
# 的取值是 tshub/sumo_tools/osm_build_type/poly.typ.xml 中那些 name。有几个很反直觉:
#   leisure.park       -> name 'tourism'  (公园叫 tourism)
#   natural            -> name 'natural'  (泛指绿地, 不是水; natural.water 才是 'water')
#   landuse.commercial -> name 'commercial', amenity.school -> name 'school'
# 所以不能按关键词猜, 必须照着这份词表来。
_KIND_BY_TYPE = {
    # 水系
    'water': 'water', 'bay': 'water', 'strait': 'water', 'harbour': 'water',
    # 公园 / 绿地 (Google 里是明显的绿色块)
    'park': 'park', 'tourism': 'park', 'leisure': 'park', 'sport': 'park',
    'village_green': 'park', 'historic': 'park', 'graveyard': 'park',
    # 树林 (比公园更深一点的绿)
    'forest': 'forest', 'natural': 'forest',
    # 农田 / 裸地 (浅黄)
    'farm': 'farm', 'land': 'farm',
    # 住宅用地 (几乎与陆地同色, 只是极轻微的区分)
    'residential': 'residential', 'landuse': 'residential',
    # 商业 / 工业用地 (淡淡的暖灰)
    'commercial': 'commercial', 'industrial': 'commercial',
    'shop': 'commercial', 'services': 'commercial',
    # 学校 / 医疗等公共设施 (Google 用淡褐色)
    'school': 'institution', 'kindergarten': 'institution', 'college': 'institution',
    'university': 'institution', 'clinic': 'institution',
    'research_institute': 'institution', 'amenity': 'institution',
    # 停车场 / 机场铺装
    'parking': 'parking', 'aeroway': 'parking',
    # 建筑物本体
    'building': 'building', 'man_made': 'building',
}

# 这些不是面状地物 (或不该画在底图上), 直接丢弃
_SKIP_TYPES = frozenset({
    'traffic_sign', 'barrier', 'power', 'highway', 'boundary', 'admin_level',
    'population', 'railway', 'railway.position', 'railway.position.exact',
    'aerialway', 'pipeline', 'inner', 'military',
})


def _basemap_kind(polygon_type: Optional[str]) -> Optional[str]:
    """把 poly 的 type 归一成底图类别; 返回 None 表示这个多边形不画"""
    if not polygon_type:
        return 'building'
    lowered = str(polygon_type).lower()
    if lowered in _SKIP_TYPES:
        return None
    if lowered in _KIND_BY_TYPE:
        return _KIND_BY_TYPE[lowered]
    # 词表之外的类型: 用 id 形式 ('landuse.xxx') 再试一次前后缀, 最后兜底成建筑
    for part in reversed(lowered.split('.')):
        if part in _KIND_BY_TYPE:
            return _KIND_BY_TYPE[part]
    return 'building'


def build_frame_payload(sim_time: float,
                        obs: Dict[str, Any],
                        static_payload: Dict[str, Any],
                        images: Optional[Dict[str, str]] = None,
                        nearby: Optional[Dict[str, Any]] = None,
                        ranking_size: int = 8) -> Dict[str, Any]:
    """构建一帧的数据.

    Args:
        sim_time: 当前仿真时间 (秒)。
        obs: 当前的观测, 需要 obs['edge_state'] / obs['lane_state']; obs['aircraft'] 可选。
        static_payload: build_static_payload 的返回值 (提供 edge/lane 的固定顺序)。
        images: {sensor_name: base64 png}, UAV 相机回传的图像。
        nearby: {aircraft_id: {'vehicle': [...], 'tls': [...]}}, UAV 附近的对象, 用于高亮。

    Returns:
        dict: 可直接 json 序列化的一帧。
    """
    edge_state = obs.get('edge_state', {})
    lane_state = obs.get('lane_state', {})

    edge_ids = static_payload['edge_ids']
    edge_congestion = [edge_state[edge_id]['speed_relative'] for edge_id in edge_ids]
    lane_congestion = [lane_state[lane_id]['speed_relative'] for lane_id in static_payload['lane_ids']]

    # 速度也一并送过去 (按全网限速上限归一化后量化), 这样大屏能显示 km/h 这种
    # 人能直接理解的量, 而不是只有一个 0~1 的归一化数字
    speed_scale = static_payload.get('speed_scale') or 1.0
    edge_speed = [edge_state[edge_id]['mean_speed'] / speed_scale for edge_id in edge_ids]

    # KPI: 全网层面的几个数, 让大屏一眼能看出整体状况
    total_vehicles = sum(state['vehicle_count'] for state in edge_state.values())
    total_halting = sum(state['halting_number'] for state in edge_state.values())
    mean_congestion = (sum(edge_congestion) / len(edge_congestion)) if edge_congestion else 1.0
    jam_ratio = (sum(1 for value in edge_congestion if value < 0.5) / len(edge_congestion)) if edge_congestion else 0.0

    # 车流加权的平均车速: 直接按 edge 取平均会被大量空路段拉平, 显示不出实际的拥堵
    moving = [(edge_state[e]['mean_speed'], edge_state[e]['vehicle_count']) for e in edge_ids]
    occupied = sum(count for _speed, count in moving)
    avg_speed = (sum(s * c for s, c in moving) / occupied) if occupied else 0.0

    # 四档路段计数 (与地图上的四种颜色一一对应), 一眼看出全网的构成
    levels = [
        sum(1 for v in edge_congestion if v < 0.25),
        sum(1 for v in edge_congestion if 0.25 <= v < 0.50),
        sum(1 for v in edge_congestion if 0.50 <= v < 0.75),
        sum(1 for v in edge_congestion if v >= 0.75),
    ]

    # 最堵的若干路段. 注意不能直接按 speed_relative 升序排 —— 那样榜首会全是
    # 「只有一辆车停在红灯前」的小路段 (整段车速 0, 但根本不是问题所在)。
    # 按「延误影响 = 拥堵程度 x 波及车辆数」排, 才能指向真正的堵点。
    def delay_impact(edge_id: str) -> float:
        state = edge_state[edge_id]
        return (1.0 - min(state['speed_relative'], 1.0)) * state['vehicle_count']

    worst = sorted(edge_ids, key=delay_impact, reverse=True)[:ranking_size]
    ranking = [
        {
            'id': edge_id,
            'name': edge_state[edge_id].get('street_name', ''),
            'rel': round(edge_state[edge_id]['speed_relative'], 3),
            'kmh': round(edge_state[edge_id]['mean_speed'] * 3.6, 1),
            'limit': round(edge_state[edge_id]['max_speed'] * 3.6, 1),
            'halt': edge_state[edge_id]['halting_number'],
            'veh': edge_state[edge_id]['vehicle_count'],
        }
        for edge_id in worst
        if delay_impact(edge_id) > 0  # 全都畅通时榜单就是空的, 前端会显示一句提示
    ]

    aircraft = [
        {
            'id': aircraft_id,
            'x': round(info['position'][0], 2),
            'y': round(info['position'][1], 2),
            'z': round(info['position'][2], 2),
        }
        for aircraft_id, info in obs.get('aircraft', {}).items()
    ]

    return {
        'time': round(sim_time, 1),
        'edge': quantize(edge_congestion),
        'lane': quantize(lane_congestion),
        'speed': quantize(edge_speed),
        'levels': levels,
        'ranking': ranking,
        'kpi': {
            # free_flow: 全网车速相当于限速的百分之多少. 用「畅通程度」而不是
            # 「拥堵指数」来表述, 因为 speed_relative 是 1=畅通/0=堵死,
            # 叫「拥堵指数 1.00」会被读反
            'free_flow': round(mean_congestion, 3),
            'avg_speed_kmh': round(avg_speed * 3.6, 1),
            'jam_ratio': round(jam_ratio, 3),
            'vehicles': total_vehicles,
            'halting': total_halting,
        },
        'aircraft': aircraft,
        'nearby': nearby or {},
        'images': images or {},
    }


def encode_image(image) -> str:
    """把 numpy 的 RGB 图像编码成 base64 PNG, 供大屏直接 <img src> 显示.

    需要 Pillow (3D 渲染的依赖里已经有)。
    """
    import io
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def _compute_bbox(lanes: List[Dict[str, Any]]) -> List[float]:
    """路网的包围盒 [xmin, ymin, xmax, ymax], 前端据此把世界坐标铺满画布"""
    xs, ys = [], []
    for lane in lanes:
        for x, y in lane['center']:
            xs.append(x)
            ys.append(y)
    if not xs:
        return [0.0, 0.0, 1.0, 1.0]
    return [min(xs), min(ys), max(xs), max(ys)]
