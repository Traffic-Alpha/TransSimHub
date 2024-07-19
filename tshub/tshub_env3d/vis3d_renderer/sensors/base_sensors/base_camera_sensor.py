'''
@Author: WANG Maonan
@Date: 2024-07-07 22:32:07
@Description: Camera Sensor (For RGB Image)
@LastEditTime: 2024-07-15 21:07:13
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
    def step(self, element_pose) -> None:
        """更新 camera 的位置, 确保可以获得指定 element 的信息
        """
        raise NotImplementedError

    @abstractmethod
    def _follow_actor(self) -> None:
        """更新相机位置, 确保可以跟上 element (不同 camera 要求的参数是不同的)
        """
        raise NotImplementedError

    def teardown(self, **kwargs) -> None:
        self.camera.teardown()

    @property
    def serializable(self) -> bool:
        return False