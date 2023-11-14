'''
@Author: WANG Maonan
@Date: 2023-09-22 14:09:07
@Description: 初始化 Map Info Object
@LastEditTime: 2023-11-12 14:50:07
'''
import sumolib

from .polygon import PolygonInfo
from ..tshub_env.base_builder import BaseBuilder

class MapBuilder(BaseBuilder):
    def __init__(self, 
                 net_file:str, 
                 poly_file:str=None, 
                 osm_file:str=None
                ) -> None:
        self.net_file = net_file # sumo net file
        self.poly_file = poly_file # 多边形的文件
        self.osm_file = osm_file # 原始 osm 文件

        self.map_info = {
            'edge': dict(),
            'node': dict(),
            'building': dict()
        } # building, edge, node
        self.create_objects() # 创建地图元素

    def create_objects(self) -> None:
        """初始化地图中所有的元素
        """
        # 得到 edge 和 node 的 shape
        net = sumolib.net.readNet(self.net_file)
        for e in net._edges: # 获得所有的 edge
            for _lane in e._lanes: # 获取每一个 edge 所有的 lane
                lane_id = _lane.getID()
                lane_shape = sumolib.geomhelper.line2boundary(
                    _lane.getShape(), _lane.getWidth()
                ) # 获得每一个 lane 的 shape
                self.map_info['edge'][lane_id] = PolygonInfo.create(
                    id=lane_id,
                    polygon_type='edge',
                    shape=lane_shape,
                    building_levels=None
                )

        for _node in net.getNodes():
            if _node.getType() != 'dead_end':
                node_id = _node.getID()
                node_shape = _node.getShape()
                self.map_info['node'][node_id] = PolygonInfo.create(
                    id=node_id,
                    polygon_type='node',
                    shape=node_shape+[node_shape[0]],
                    building_levels=None
                )

        # 遍历 poly 文件获得当前环境中所有的多边形
        if self.poly_file is not None:
            for poly in sumolib.xml.parse(self.poly_file, "poly"):
                self.map_info['building'][poly.id] = PolygonInfo.create(
                    id=poly.id,
                    polygon_type=poly.type,
                    shape=poly.shape,
                    building_levels=1
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

    
    def get_objects_infos(self) -> None:
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