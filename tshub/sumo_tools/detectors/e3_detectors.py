'''
@Author: WANG Maonan
@Date: 2021-11-03 15:08:30
@Description: 在指定的区域生成 E3 探测器
@LastEditTime: 2023-08-24 17:51:04
'''
from loguru import logger
from typing import Dict, List
import sumolib
from .base_detectors import detector_base


class e3_detector(detector_base):
    """生成 E3 探测器, 每一个 connection 会有 E3 探测器
    """

    def __init__(self, 
                tls_connections:Dict[str, List[List]], 
                output_file:str='e3.add.xml', 
                results_file:str='e3.output.xml', 
                distance_to_TLS:float=0.1, 
                freq:int=60) -> None:
        """初始化 E3 探测器的参数

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
            output_file (str, optional): The name of the file to write the detector, Defaults to e3.add.xml
            results_file (str, optional): The name of the file the detectors write, Defaults to e3.output.xml
            detector_length (float, optional): E2 探测器的长度
            pos (float, optional): 探测器的位置, 默认 -0.1 是在道路的出口处. Defaults to -0.1.
            freq (int, optional): 探测器的输出频率. Defaults to 60.
        """
        self.tls_connections = tls_connections # getTLSConnection.tls_connection:get_tls_connections 的返回值
        self.output_file = output_file # 例如 e3.add.xml
        self.results_file = results_file # 例如 e3output.xml
        self.distance_to_TLS = distance_to_TLS  # E2 探测器探测的位置 (开始位置)
        self.freq = freq  # 指定探测器的探测周期长度

        self.tls_edge_connections = self._get_edge_connections()

    def _writeEntryExit(self, edge_connection, detector_xml):
        for (fromLane_id, toLane_id) in edge_connection:
            # 设置入口探测器
            detector_entry_xml = detector_xml.addChild("detEntry")
            detector_entry_xml.setAttribute("lane", fromLane_id)
            detector_entry_xml.setAttribute("pos", str(-1))

            # 设置出口探测器
            detector_exit_xml = detector_xml.addChild("detExit")
            detector_exit_xml.setAttribute("lane", toLane_id)
            detector_exit_xml.setAttribute("pos", str(1))


    def generate_detector(self) -> None:
        """生成 e3 探测器的文件
        """
        detectors_xml = sumolib.xml.create_document("additional")
        for _tls_id, _edge_connections in self.tls_edge_connections.items():
            for fromEdge_toEdge_direction, _edge_connection in _edge_connections.items(): # 每一个转向设置 e3 探测器
                detID = 'e3det--{}--{}'.format(_tls_id, fromEdge_toEdge_direction) # 探测器的 ID
                detector_xml = detectors_xml.addChild("e3Detector")
                detector_xml.setAttribute("id", str(detID)) # 设置探测器的 id
                detector_xml.setAttribute("freq", str(self.freq)) # 探测器的频率
                detector_xml.setAttribute("file", self.results_file)
                detector_xml.setAttribute("openEntry", "true") # 这样减少 warning
                self._writeEntryExit(_edge_connection, detector_xml)


        detector_file = open(self.output_file, 'w') # 将 e3 探测器写入文件
        detector_file.write(detectors_xml.toXML())
        detector_file.close()

        logger.info('SIM: '+'='*10)
        logger.info('SIM: E3 探测器文件 {} 生成生成!'.format(self.output_file))
        logger.info('SIM: '+'='*10)