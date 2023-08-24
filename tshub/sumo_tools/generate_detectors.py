'''
@Author: WANG Maonan
@Date: 2023-08-24 16:35:24
@Description: 自动生成不同类型的探测器
@LastEditTime: 2023-08-24 17:40:09
'''
import os
import logging
from typing import Dict, List

from .detectors.e1_detectors import e1_detector
from .detectors.e1_internal_detectors import e1_internal_detector
from .detectors.e2_detectors import e2_detector
from .detectors.e3_detectors import e3_detector
from .sumo_infos.tls_connections import tls_connection
from ..utils.check_folder import check_folder


def generate_init_detector(file_name):
    """初始化探测器文件, 这里file_name需要和sumocfg中的探测器名称相同
    """
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, 'w+') as file:
        file.write('<additional> \n')
        file.write('</additional> \n')

class generate_detector(object):
    def __init__(self, sumo) -> None:
        self.sumo = sumo
        self.logger = logging.getLogger(__name__)
        self.logger.info('准备生成探测器.')

    def generate_multiple_detectors(self, 
                                    result_folder:str, 
                                    tls_list:List, 
                                    detectors_dict:Dict[str, Dict[str, float]]={'e1':dict(), 'e1_internal':dict(), 'e2':{'detector_length':100}, 'e3':dict()}):
        """生成多种探测器

        Args:
            result_folder (str): 探测器要保存的文件夹
            tls_list (List): 要摆放探测器的路口
            detectors_list (List, optional): 生成的探测器类型. Defaults to ['e1', 'e1_internal', 'e2', 'e3'].
        """
        check_folder(result_folder) # 检查文件夹是否存在
            
        tls_info = tls_connection(self.sumo)
        tls_connections = tls_info.get_tls_connections(tls_list) # 获得每个路口的连接情况
        for detector_name, detector_params in detectors_dict.items():
            output_file = os.path.join(result_folder, '{}.add.xml'.format(detector_name))
            detector = self._generate_single_detector(detector_name)(**detector_params, tls_connections=tls_connections, output_file=output_file)
            detector.generate_detector() # 生成探测器文件

    def _generate_single_detector(self, detector_name:str):
        """输入探测器类型, 返回对应的类

        Args:
            detector_name (str): 探测器的名称, 需要在 detector_types 里面
        """
        detector_types = ['e1', 'e1_internal', 'e2', 'e3'] # 支持探测器类型
        assert detector_name in detector_types, '{} should be in {}'.format(detector_name, detector_types)
        if detector_name == 'e1':
            return e1_detector
        elif detector_name == 'e1_internal':
            return e1_internal_detector
        elif detector_name == 'e2':
            return e2_detector
        elif detector_name == 'e3':
            return e3_detector
        else:
            raise ValueError('{} should be in {}'.format(detector_name, detector_types))