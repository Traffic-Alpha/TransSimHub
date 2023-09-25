'''
@Author: WANG Maonan
@Date: 2023-09-22 14:16:02
@Description: 地图中 Polygon 的属性
@LastEditTime: 2023-09-22 14:29:54
'''
from dataclasses import dataclass, fields
from typing import List, Dict, Any

@dataclass
class PolygonInfo:
    id: str
    polygon_type: str # 多边形的类型
    shape: List[float] # 多边形的形状
    building_levels: int # 建筑物是几层

    @classmethod
    def create(cls,
               id:str,
               polygon_type: str,
               shape: List[float],
               building_levels: int):
        polygon = cls(
            id, polygon_type,
            shape, building_levels
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