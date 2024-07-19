'''
@Author: WANG Maonan
@Date: 2024-07-14 01:31:00
@Description: 只能看到 vehicle, 看不到其他内容
@LastEditTime: 2024-07-14 20:20:35
'''
import numpy as np
from typing import Tuple

from ...vis3d_utils.masks import CamMask
from .base_sensors.base_camera_sensor import CameraSensor

class VehicleSensor(CameraSensor):
    """只包含车辆和地面
    """
    def __init__(
        self,
        camera,
        element_pose,
        element_dimensions:Tuple[float, float, float],
    ) -> None:
        super().__init__(camera,element_pose,element_dimensions)

    def __call__(self):
        assert self.camera is not None, "Sensor has not been initialized"

        ram_image = self.camera.wait_for_ram_image(img_format="RGBA")
        mem_view = memoryview(ram_image)
        image: np.ndarray = np.frombuffer(mem_view, np.uint8)
        width, height = self.camera.image_dimensions # 输出图像的分辨率
        image.shape = (height, width, 4)  # 注意我们现在使用 RGBA，所以这里是 4 而不是 3
        image = np.flipud(image)
        return image
