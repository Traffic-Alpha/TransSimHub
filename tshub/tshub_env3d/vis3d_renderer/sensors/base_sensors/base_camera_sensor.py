'''
@Author: WANG Maonan
@Date: 2024-07-07 22:32:07
@Description: Camera Sensor (For RGB Image)
@LastEditTime: 2024-07-20 15:48:06
'''
from typing import Tuple
from abc import abstractmethod

from .base_sensor import BaseSensor

class CameraSensor(BaseSensor):
    """The base for a sensor that renders images.
    """
    def __init__(self) -> None:
        """初始化的时候需要使用 self._follow_actor 初始化 sensor 的位置
        """
        pass
    
    @abstractmethod
    def init_actor(self, element_pose) -> None:
        """初始化相机的位置
        """
        raise NotImplementedError
    
    @abstractmethod
    def step(self, element_pose) -> None:
        """更新 camera 的位置, 确保可以获得指定 element 的信息
        """
        raise NotImplementedError

    def teardown(self, **kwargs) -> None:
        self.camera.teardown()

    @property
    def serializable(self) -> bool:
        return False