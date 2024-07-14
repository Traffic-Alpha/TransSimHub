'''
@Author: WANG Maonan
@Date: 2024-07-07 22:32:07
@Description: Camera Sensor (For RGB Image)
@LastEditTime: 2024-07-14 00:35:25
'''
from typing import Tuple

from .base_sensor import BaseSensor

class CameraSensor(BaseSensor):
    """The base for a sensor that renders images.
    """
    def __init__(
        self,
        camera,
        element_pose,
        element_dimensions:Tuple[float, float, float],
    ) -> None:
        self.camera = camera # camera node path
        self.element_dimensions = element_dimensions # 模型的大小

        self._follow_actor(element_pose) # 确保可以跟上

    def step(self, element_pose) -> None:
        """更新 camera 的位置, 确保可以获得指定 element 的信息
        """
        self._follow_actor(element_pose=element_pose)

    def _follow_actor(self, element_pose) -> None:
        self.camera.update(element_pose, self.element_dimensions[-1]+10)

    def teardown(self, **kwargs) -> None:
        self.camera.teardown()

    @property
    def serializable(self) -> bool:
        return False