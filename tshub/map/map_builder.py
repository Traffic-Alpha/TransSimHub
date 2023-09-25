'''
@Author: WANG Maonan
@Date: 2023-09-22 14:09:07
@Description: 初始化 Map Info Object
@LastEditTime: 2023-09-22 14:42:10
'''
import sumolib

from .polygon import PolygonInfo
from ..tshub_env.base_builder import BaseBuilder

class MapBuilder(BaseBuilder):
    def __init__(self, poly_file, osm_file) -> None:
        self.poly_file = poly_file # 多边形的文件
        self.osm_file = osm_file # 原始 osm 文件

        self.map_info = {}
        self.create_objects() # 创建地图元素

    def create_objects(self) -> None:
        # 遍历 poly 文件获得当前环境中所有的多边形
        for poly in sumolib.xml.parse(self.poly_file, "poly"):
            self.map_info[poly.id] = PolygonInfo.create(
                id=poly.id,
                polygon_type=poly.type,
                shape=poly.shape,
                building_levels=1
            )
        
        # 遍历 osm 文件更新 poly 的信息
        for building in sumolib.xml.parse(self.osm_file, "way"):
            if building.id in self.map_info:
                if building.tag is not None:
                    tag_dict = {tag.k:tag.v for tag in building.tag}
                else:
                    tag_dict = {}
                    
                if "building:levels" in tag_dict:
                    self.map_info[building.id].building_levels = tag_dict["building:levels"]

    
    def get_objects_infos(self) -> None:
        all_poly_data = {
            poly_id: poly.get_features()
            for poly_id, poly in self.map_info.items()
        }
        return all_poly_data
    
    def update_objects_state(self) -> None:
        return NotImplementedError
    
    def control_objects(self) -> None:
        raise NotImplementedError