'''
@Author: WANG Maonan
@Date: 2023-09-22 14:09:07
@Description: 初始化 Map Info Object
@LastEditTime: 2024-05-29 16:37:23
'''
import sumolib
from typing import Dict

from .grid import GridInfo
from .polygon import PolygonInfo
from ..tshub_env.base_builder import BaseBuilder

class MapBuilder(BaseBuilder):
    def __init__(self, 
                 net_file:str, 
                 poly_file:str=None, 
                 osm_file:str=None,
                 radio_map_files:Dict[str, str]=None
        ) -> None:
        self.net_file = net_file # sumo net file
        self.poly_file = poly_file # 多边形的文件
        self.osm_file = osm_file # 原始 osm 文件
        self.radio_map_files = radio_map_files # 传入每一个坐标的信息

        self.map_info = {
            'lane': dict(), # 车道信息
            'node': dict(), # 节点信息
            'building': dict(), # 建筑物信息
            'grid': dict(), # 将 map 且分为 grid, 统计每个 grid 内部的信息
        } # building, lane, node
        self.create_objects() # 创建地图元素

    def create_objects(self) -> None:
        """初始化地图中所有的元素
        """
        # 得到 edge 和 node 的 shape
        net = sumolib.net.readNet(self.net_file)

        # 得到基础信息
        x_offset, y_offset = net.getLocationOffset()

        # 统计 edge 的信息
        for e in net._edges: # 获得所有的 edge
            edge_id = e.getID() # 获得 edge ID
            for _lane in e._lanes: # 获取每一个 edge 所有的 lane
                lane_id = _lane.getID()
                lane_length = _lane.getLength() # 获得 lane 的长度
                lane_shape = sumolib.geomhelper.line2boundary(
                    _lane.getShape(), _lane.getWidth()
                ) # 获得每一个 lane 的 shape
                self.map_info['lane'][lane_id] = PolygonInfo.create(
                    id=lane_id,
                    edge_id=edge_id,
                    length=lane_length,
                    polygon_type='lane',
                    shape=lane_shape,
                    building_levels=None,
                    node_type=None,
                    node_coord=None
                )

        # 遍历所有的 node 信息, 这些 node 是路口
        for _node in net.getNodes():
            if _node.getType() != 'dead_end':
                node_id = _node.getID()
                node_shape = _node.getShape()
                node_coord = _node.getCoord()
                node_type = _node.getType()
                self.map_info['node'][node_id] = PolygonInfo.create(
                    id=node_id,
                    edge_id=None,
                    length=0, # node 没有长度
                    polygon_type='node',
                    shape=node_shape+[node_shape[0]],
                    building_levels=None,
                    node_coord=node_coord,
                    node_type=node_type
                )

        # 遍历 poly 文件获得当前环境中所有的多边形
        if self.poly_file is not None:
            for poly in sumolib.xml.parse(self.poly_file, "poly"):
                self.map_info['building'][poly.id] = PolygonInfo.create(
                    id=poly.id,
                    edge_id=None,
                    length=0,
                    polygon_type=poly.type,
                    shape=poly.shape,
                    building_levels=1,
                    node_type=None,
                    node_coord=None
                )
        
        # 遍历 osm 文件更新 poly 的信息
        if self.osm_file is not None:
            for building in sumolib.xml.parse(self.osm_file, "way"):
                if building.id in self.map_info['building']:
                    if building.tag is not None:
                        tag_dict = {tag.k:tag.v for tag in building.tag}
                    else:
                        tag_dict = {}
                        
                    if "building:levels" in tag_dict:
                        self.map_info['building'][building.id].building_levels = tag_dict["building:levels"]
        
        # 处理 radio map 的信息, 获得每个点的信息
        if self.radio_map_files is not None:
            for file_type, file_path in self.radio_map_files.items():
                self.map_info['grid'][file_type] = GridInfo.from_radio_map_txt(file_path, x_offset, y_offset)

    def get_objects_infos(self) -> None:
        """获得 map 的信息
        """
        all_poly_data = {
            object_type: {poly_id: poly.get_features() for poly_id, poly in objects.items()} 
            for object_type, objects in self.map_info.items()
        }
        return all_poly_data
    
    def update_objects_state(self) -> None:
        """地图的信息是不需要进行更新的
        """
        return NotImplementedError
    
    def control_objects(self) -> None:
        raise NotImplementedError