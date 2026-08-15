'''
@Author: WANG Maonan
@Date: 2023-09-22 14:16:02
@Description: 地图中 Polygon 的属性. Edge, Node and Buildings are all Polygon
+ building:levels: https://wiki.openstreetmap.org/wiki/Key:building:levels
@LastEditTime: 2024-05-06 23:46:21
'''
from dataclasses import dataclass, fields
from typing import Tuple, Dict, Any

@dataclass
class PolygonInfo:
    id: str
    edge_id: str # 如果是 lane, 则包含所属的 edge
    length: float # 如果是 lane, 则包含 lane 的长度
    polygon_type: str # 多边形的类型, 例如 lane, node
    shape: Tuple[Tuple[float, float]] # 多边形的形状
    # For Map
    building_levels: int # 建筑物是几层
    # For Node
    node_coord: Tuple[float] # 如果是 node, 则记录 node 的坐标
    node_type: str # 如果是 node, 则记录 node 的类型, 例如是否是 traffic_light
    # For Lane
    # shape 是把中心线按车道宽度外扩得到的「边界多边形」, 这个过程是不可逆的
    # (共线的点会被合并, 边界点数不一定是中心线的两倍), 因此中心线和宽度必须
    # 在这里一并存下来, 不能事后从 shape 反推。
    center_shape: Tuple[Tuple[float, float]] = None # 如果是 lane, 则记录中心线
    width: float = None # 如果是 lane, 则记录车道宽度 (m)

    @classmethod
    def create(cls,
               id: str,
               edge_id: str,
               length: float,
               polygon_type: str,
               shape: str,
               building_levels: int,
               node_coord: Tuple[float],
               node_type: str,
               center_shape: Tuple[Tuple[float, float]] = None,
               width: float = None
        ):
        if isinstance(shape, str):
            shape_tuple = tuple([tuple(map(float, point.split(","))) for point in shape.split()])
        else:
            shape_tuple = shape
        polygon = cls(
            id, edge_id, length,
            polygon_type,
            shape_tuple, building_levels,
            node_coord, node_type,
            center_shape, width
        )
        return polygon
    
    def get_features(self) -> Dict[str, Any]:
        output_dict = {}
        for field in fields(self):
            field_name = field.name
            field_value = getattr(self, field_name)
            if field_name != 'sumo':
                output_dict[field_name] = field_value
        return output_dict