'''
@Author: WANG Maonan
@Date: 2024-07-08 19:43:50
@Description: RGB Sensor, 绑定在场景的 obejct 上
@LastEditTime: 2024-07-09 01:20:18
'''
import numpy as np
from typing import Tuple
from ..base_render import BaseRender
from .camera_sensor import CameraSensor

class RGBSensor(CameraSensor):
    """A sensor that renders color values from around its target actor.
    """
    def __init__(
        self,
        camera_name:str,
        element_pose,
        element_dimensions:Tuple[float, float, float],
        renderer: BaseRender,
    ) -> None:
        super().__init__(camera_name,element_pose,element_dimensions,renderer)

    def __call__(self):
        camera = self.renderer.camera_for_id(self.camera_name)
        assert camera is not None, "RGB has not been initialized"

        ram_image = camera.wait_for_ram_image(img_format="RGB")
        mem_view = memoryview(ram_image)
        image: np.ndarray = np.frombuffer(mem_view, np.uint8)
        width, height = camera.image_dimensions # 输出图像的分辨率
        image.shape = (height, width, 3)
        image = np.flipud(image)
        return image