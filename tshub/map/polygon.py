'''
@Author: WANG Maonan
@Date: 2023-09-22 14:16:02
@Description: 地图中 Polygon 的属性. Edge, Node and Buildings are all Polygon
+ building:levels: https://wiki.openstreetmap.org/wiki/Key:building:levels
@LastEditTime: 2024-04-09 23:00:21
'''
from dataclasses import dataclass, fields
from typing import Tuple, Dict, Any

@dataclass
class PolygonInfo:
    id: str
    edge_id: str # 如果是 lane, 则包含所属的 edge
    length: float # 如果是 lane, 则包含 lane 的长度
    polygon_type: str # 多边形的类型
    shape: Tuple[Tuple[float, float]] # 多边形的形状
    building_levels: int # 建筑物是几层

    @classmethod
    def create(cls,
               id: str,
               edge_id: str,
               length: float,
               polygon_type: str,
               shape: str,
               building_levels: int):
        if isinstance(shape, str):
            shape_tuple = tuple([tuple(map(float, point.split(","))) for point in shape.split()])
        else:
            shape_tuple = shape
        polygon = cls(
            id, edge_id, length,
            polygon_type,
            shape_tuple, building_levels
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