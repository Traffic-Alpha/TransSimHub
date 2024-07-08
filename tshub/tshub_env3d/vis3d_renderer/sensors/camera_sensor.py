'''
@Author: WANG Maonan
@Date: 2024-07-07 22:32:07
@Description: Camera Sensor (For RGB Image)
@LastEditTime: 2024-07-09 01:20:49
'''
from typing import Optional, Tuple

from .base_sensor import BaseSensor
from ..base_render import BaseRender

class CameraSensor(BaseSensor):
    """The base for a sensor that renders images.
    """
    def __init__(
        self,
        camera_name:str,
        element_pose,
        element_dimensions:Tuple[float, float, float],
        renderer: BaseRender,
    ) -> None:
        assert renderer
        self.renderer = renderer # 整个场景的渲染器
        self.element_dimensions = element_dimensions # 模型的大小
        self.camera_name = camera_name # camera name, 为了在 node path 中找到 camera

        self._follow_actor(element_pose) # 确保可以跟上

    def step(self, element_pose) -> None:
        """更新 camera 的位置, 确保可以获得指定 element 的信息
        """
        self._follow_actor(element_pose=element_pose)

    def _follow_actor(self, element_pose) -> None:
        if not self.renderer:
            return
        camera = self.renderer.camera_for_id(self.camera_name) # 获得对应的 camera, 从而可以修改 camera 的位置
        camera.update(element_pose, self.element_dimensions[-1]+10)

    def teardown(self, **kwargs) -> None:
        renderer: Optional[BaseRender] = kwargs.get("renderer")
        if not renderer:
            return
        camera = renderer.camera_for_id(self.camera_name)
        camera.teardown()

    @property
    def serializable(self) -> bool:
        return False