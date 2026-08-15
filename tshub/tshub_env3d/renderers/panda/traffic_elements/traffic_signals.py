'''
@Author: WANG Maonan
@Date: 2024-07-07 10:01:04
@Description: 
LastEditTime: 2025-03-25 16:01:17
'''
from typing import Tuple

from .base_element import BaseElement

class TLS3DElement(BaseElement):
    def __init__(
            self, 
            fig_width: float, fig_height: float, 
            fig_resolution:float,
            element_id: str, 
            element_position: Tuple[float, float], 
            element_heading: float = None, 
            element_length: float = None, 
            root_np=None, 
            showbase_instance=None,
            tls_camera_height:int=10,
        ) -> None:
        """模拟路口摄像头

        Args:
            fig_width (float): 传感器输出的图片的宽度
            fig_height (float): 传感器输出的图片的高度
            element_id (str): 信号灯 ID
            element_position (Tuple[float, float]): 信号灯的位置
            element_heading (float, optional): 路口摄像头朝向. Defaults to None.
            element_length (float, optional): 长度, 这里没有用到. 汽车部分需要计算位置使用. Defaults to None.
            root_np (_type_, optional): panda3d root path. Defaults to None.
            showbase_instance (_type_, optional): panda3d showbase instance. Defaults to None.
        """
        super().__init__(
            fig_width, fig_height, fig_resolution, 
            element_id, element_position, element_heading, element_length, root_np, showbase_instance
        )
        self.tls_camera_height = tls_camera_height # 路口摄像头的高度
    
    _carrier = 'tls'

    def _sensor_extra_kwargs(self) -> dict:
        """路口相机架在传入的绝对高度 (tls_camera_height / junction_bev_height)."""
        return {'height': self.tls_camera_height}

    def create_node(self) -> None:
        pass

    def update_node(self) -> None:
        pass

    def begin_rendering_node(self) -> None:
        pass

        
    def update_sensor(self) -> None:
        """更新 sensor 的位置, 这里信号灯的摄像机是不需要移动的
        """
        pass
    
    def get_sensor(self):
        sensor_data = {}
        for _sensor_id, _sensor in self.sensors.items():
            ego_rgb = _sensor()
            sensor_data[_sensor_id] = ego_rgb
        return sensor_data
