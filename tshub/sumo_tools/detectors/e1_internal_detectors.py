'''
@Author: WANG Maonan
@Date: 2021-11-03 15:08:30
@Description: 在指定交叉路口上的 internal lane 放置探测器; 信号灯 id: (e1det_internal, _tls_id, fromEdge_id, fromLane_id, direction)
@LastEditTime: 2023-08-24 17:03:11
'''
from loguru import logger
from typing import Dict, List
import sumolib
from .base_detectors import detector_base

class e1_internal_detector(detector_base):
    """生成 E1 Internal 探测器, 在交叉路口里面的 lane 设置探测器, 获得转向数据
    """

    def __init__(self, 
                tls_connections:Dict[str, List[List]], 
                output_file:str='e1_internal.add.xml', 
                results_file:str='e1_internal.output.xml',
                freq:int=60) -> None:
                
        """初始化 E1 Internal 探测器的参数

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
            output_file (str. optional): The name of the file to write the detector, Defaults to e1_internal.add.xml
            results_file (str, optional): The name of the file the detectors write, Defaults to e1_internal.output.xml
            distance_to_TLS (float, optional): 探测器距离信号灯的位置, 默认 0.1 表示距离信号灯 0.1 m. Defaults to 0.1.
            freq (int, optional): 探测器的输出频率. Defaults to 60.
        """
        self.tls_connections = tls_connections # getTLSConnection.tls_connection:get_tls_connections 的返回值
        self.output_file = output_file # 例如 e1.add.xml
        self.results_file = results_file # 例如 e1output.xml
        self.freq = freq  # 指定探测器的探测周期长度

        self.lane2direction = self._get_lane_direction() # 每个车道对应的方向

    def generate_detector(self) -> None:
        """生成 e1 internal 探测器的文件
        """
        detectors_xml = sumolib.xml.create_document("additional")
        for _tls_id, _tls_connection in self.tls_connections.items():
            for lane_info in _tls_connection:
                fromEdge_id = lane_info[0] # edge 的 id
                fromLane_id = lane_info[2] # from lane 的 id
                toLane_id = lane_info[3] # to lane 的 id, 可能会出现 一个 fromLane -> 多个 toLane, 所以需要包含 toLaneID
                internalLane_id = lane_info[4] # internal lane
                direction = lane_info[5] # connection 的方向
                final_detector_position = 3 # 探测器实际位置

                e1_id = 'e1det_internal--{}--{}--{}--{}--{}'.format(_tls_id, fromEdge_id, fromLane_id, toLane_id, direction)

                # xml 的信息
                detector_xml = detectors_xml.addChild("e1Detector")
                detector_xml.setAttribute("file", self.results_file)
                detector_xml.setAttribute("freq", str(self.freq))
                detector_xml.setAttribute("friendlyPos", "x")
                detector_xml.setAttribute("id", e1_id)
                detector_xml.setAttribute("lane", str(internalLane_id))
                detector_xml.setAttribute("pos", str(final_detector_position))

        detector_file = open(self.output_file, 'w') # 将 e1 internal 探测器写入文件
        detector_file.write(detectors_xml.toXML())
        detector_file.close()

        logger.info('SIM: '+'='*10)
        logger.info('SIM: E1 Internal 探测器文件 {} 生成生成!'.format(self.output_file))
        logger.info('SIM: '+'='*10)