'''
@Author: WANG Maonan
@Date: 2023-08-24 16:21:40
@Description: 定义一些生成探测器的基础功能
LastEditTime: 2024-09-16 15:36:05
'''
import sumolib
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List

from ...utils.nested_dict_conversion import defaultdict2dict

class detector_base(ABC):
    def __init__(self, tls_connections:Dict[str, List[List]]) -> None:
        """初始化时, 给定交叉路口 lane 的信息

        Args:
            tls_connections (Dict[str, List[List]]): tls 的信息, 格式如下:
                {
                    'tlsID_1':[
                        [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                        [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                        ...
                    ],
                    'tlsID_2':[
                        [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                        [fromEdge, toEdge, fromLane, toLane, internalLane, direction, fromLane_length],
                        ...
                    ],
                    ...
                }
        """
        self.tls_connections = tls_connections # getTLSConnection.tls_connection:get_tls_connections 的返回值
    
    @abstractmethod
    def generate_detector(self):
        """生成探测器
        """
        pass
    
    def adjust_detector_length(self, 
                            requested_detector_length:float, 
                            requested_distance_to_tls:float, 
                            lane_length:float):
        """调整探测器的长度, 例如现在道路长度为 100:
        - 情况一, 此时想要探测器长度是 20, 开始位置是 30, min(100-30, 20)=20, 那么返回探测器长度为 20;
        - 情况二, 此时想要探测器长度是 20, 开始位置是 90, min(100-90, 20)=10, 那么返回探测器长度为 10;

        Args:
            requested_detector_length (float): 想要的探测器的长度
            requested_distance_to_tls (float): 探测器距离信号灯的位置
            lane_length (float): lane 的长度
        """

        return min(lane_length - requested_distance_to_tls,
                requested_detector_length)        

    def adjust_detector_position(self, 
                                detector_length:float, 
                                requested_distance_to_tls:float, 
                                lane_length:float):
        """调整探测器的位置（lane 进入的位置 pos=0, 也就是距离信号灯近的地方是出口 pos=-0.1）
        例如当前道路长度是 100:
        - 情况一, 探测器（探测器长度为 0）想要距离信号灯 90, 此时返回探测器位置 10
        - 情况二, 探测器（探测器长度为 0）想要距离信号灯 130 (超出道路长度), 此时位置为 0
        - 情况三, 探测器（探测器长度为 10）想要距离信号灯 70, 此时返回探测器位置 100-70-10=20

        Args:
            detector_length (float): 探测器的长度
            requested_distance_to_tls (float): 想要的距离信号灯的距离
            lane_length (float): 车道的长度

        Returns:
            (float): 实际探测器的位置
        """
        return max(0,
               lane_length - detector_length - requested_distance_to_tls)
    
    def _get_lane_direction(self):
        """返回每个车道对应的方向（一个车道可以有多个方向） 
        最终返回的值为每个车道对应的方向, 如下所示:
            {
                'fromLane_1': 's',
                'fromLane_2': 'sr',
                ...
            }
        """
        lane2direction = defaultdict(str)
        for _, tls_connection in self.tls_connections.items():
            for lane_info in tls_connection:
                direction = lane_info[5] # 转向
                fromLane_id = lane_info[2]
                if direction not in lane2direction[fromLane_id]: # 避免出现 sss, 及一个车道连接多个车道的情况
                    lane2direction[fromLane_id] += direction
        return lane2direction

    
    def _get_edge_connections(self):
        """返回 edge->edge 包含哪一些 lane->lane, 
        例如从 edgeID1 到 edgeID2 由两个车道组成, 则返回如下数据:
            fromedgeID1--toedgeID1--direction:[
                (fromLane1, toLane1), 
                (fromLane2, toLane2),
                ],
            此功能用于 E3 探测器
       
        最终输出的结果的例子为, 
        {
            '0':{
                'gneE27--hrj_n4--r':[('gneE27_0', 'hrj_n4_0')],
                'gneE27--29257863#2--s':[('gneE27_1', '29257863#2_2'), ('gneE27_2', '29257863#2_3')],
                ...
            },
            '1':{
                'hrj_n5--29257863#2--l':[('hrj_n5_2', '29257863#2_4')],
                ...
            }
            ...
        }
        """
        tls_edge_connections = dict()
        for tls_id, tls_connection in self.tls_connections.items():
            tls_edge_connections[tls_id] = defaultdict(list) # 每个路口统计
            for lane_info in tls_connection:
                fromEdge_id = lane_info[0]
                toEdge_id = lane_info[1]
                fromLane_id = lane_info[2]
                toLane_id = lane_info[3]
                direction = lane_info[5] # 转向
                key = '{}--{}--{}'.format(fromEdge_id, toEdge_id, direction) # 作为 key
                tls_edge_connections[tls_id][key].append((fromLane_id, toLane_id))
        return defaultdict2dict(tls_edge_connections)
        

    
    def _output_Parse(self, element_names):
        return sumolib.output.parse(xmlfile=self.xml_file, 
                                    element_names=element_names)