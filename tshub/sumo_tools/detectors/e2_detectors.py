'''
@Author: WANG Maonan
@Date: 2021-11-03 15:08:30
@Description: 在指定的 lane 上生成 E2 探测器
@LastEditTime: 2023-08-24 17:03:57
'''
from loguru import logger
from typing import Dict, List
import sumolib
from .base_detectors import detector_base

class e2_detector(detector_base):
    """生成 E2 探测器, 每一个路口每一个 lane 都有一个探测器
    """

    def __init__(self, 
                tls_connections:Dict[str, List[List]], 
                output_file:str='e2.add.xml', 
                results_file:str='e2.output.xml', 
                detector_length:float=100,
                distance_to_TLS:float=0.1, 
                freq:int=60) -> None:
        """初始化 E2 探测器的参数

        Args:
            tls_connection (Dict[str, List[List]]): tls 的信息, 格式如下:
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
            output_file (str, optional): The name of the file to write the detector, Defaults to e2.add.xml
            results_file (str, optional): The name of the file the detectors write, Defaults to e2.output.xml
            detector_length (float, optional): E2 探测器的长度
            pos (float, optional): 探测器的位置, 默认 -0.1 是在道路的出口处. Defaults to -0.1.
            freq (int, optional): 探测器的输出频率. Defaults to 60.
        """
        self.tls_connections = tls_connections # getTLSConnection.tls_connection:get_tls_connections 的返回值
        self.output_file = output_file # 例如 e2.add.xml
        self.results_file = results_file # 例如 e2output.xml
        self.detector_length = detector_length # 设置的探测器的长度
        self.distance_to_TLS = distance_to_TLS  # E2 探测器探测的位置 (开始位置)
        self.freq = freq  # 指定探测器的探测周期长度

        self.lane2direction = self._get_lane_direction() # 每个车道对应的方向

    def generate_detector(self):
        """生成 e2 探测器的文件
        """
        lanes_with_detectors = set() # 已经布置了探测器的 Lane
        detectors_xml = sumolib.xml.create_document("additional")
        for _tls_id, _tls_connection in self.tls_connections.items():
            for lane_info in _tls_connection:
                fromEdge_id = lane_info[0] # edge 的 id
                fromLane_id = lane_info[2] # lane 的 id

                if fromLane_id in lanes_with_detectors: # 判断某个 lane 是否有探测器
                    continue
                lanes_with_detectors.add(fromLane_id)

                direction = self.lane2direction[fromLane_id] # lane 对应的方向
                fromLane_length = lane_info[6] # fromLane 的道路长度
                e2_id = 'e2det--{}--{}--{}--{}'.format(_tls_id, fromEdge_id, fromLane_id, direction)
                
                final_detector_length = self.adjust_detector_length(self.detector_length, 
                                                                    self.distance_to_TLS, 
                                                                    fromLane_length) # 探测器长度

                final_detector_position = self.adjust_detector_position(final_detector_length,
                                                                        self.distance_to_TLS, 
                                                                        fromLane_length) # 探测器的位置

                # xml 的信息
                detector_xml = detectors_xml.addChild("laneAreaDetector")
                detector_xml.setAttribute("file", self.results_file)
                detector_xml.setAttribute("freq", str(self.freq))
                detector_xml.setAttribute("friendlyPos", "x")
                detector_xml.setAttribute("id", e2_id)
                detector_xml.setAttribute("lane", str(fromLane_id))
                detector_xml.setAttribute("pos", str(final_detector_position))
                detector_xml.setAttribute("length", str(final_detector_length))

        detector_file = open(self.output_file, 'w') # 将 e2 探测器写入文件
        detector_file.write(detectors_xml.toXML())
        detector_file.close()

        logger.info('SIM: '+'='*10)
        logger.info('SIM: E2 探测器文件 {} 生成生成!'.format(self.output_file))
        logger.info('SIM: '+'='*10)