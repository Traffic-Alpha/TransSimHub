'''
@Author: WANG Maonan
@Date: 2024-07-08 19:43:50
@Description: RGB Sensor, 绑定在场景的 obejct 上
@LastEditTime: 2024-07-15 23:21:36
'''
import numpy as np
from typing import Tuple
from .base_sensors.base_camera_sensor import CameraSensor
from .cameras.build_offscreen_camera import build_offscreen_camera


class RGBSensor(CameraSensor):
    """A sensor that renders color values from around its target actor.
    """
    def __init__(
        self,
        camera_name:str,
        camera_mask,
        showbase_instance,
        root_np,
        init_element_pose,
        element_dimensions:Tuple[float, float, float],
        fig_width:int=800,
        fig_height:int=600,
        fig_resolution:float=0.1,
        camera_height:float=100,
        camera_type:str='Off_BEV_Camera',
    ) -> None:
        super().__init__()
        self.init_element_pose = init_element_pose
        self.element_dimensions = element_dimensions
        self.camera_height = camera_height
        self.camera = build_offscreen_camera(
            name=camera_name,
            mask=camera_mask,
            width=fig_width,
            height=fig_height,
            resolution=fig_resolution,
            showbase_instance=showbase_instance,
            root_np=root_np,
            camera_type=camera_type
        ) # 创建相机, 这个相机是绑定在 sensor 上面的
        self._follow_actor(self.init_element_pose) # 初始化相机镜头
    

    def step(self, element_pose) -> None:
        """更新 camera 的位置, 确保可以获得指定 element 的信息
        """
        self._follow_actor(element_pose=element_pose)

    def _follow_actor(self, element_pose) -> None:
        self.camera.update(element_pose, self.element_dimensions[-1]+self.camera_height) # 高度
    
    def __call__(self):
        assert self.camera is not None, "RGB has not been initialized"

        ram_image = self.camera.wait_for_ram_image(img_format="RGB")
        mem_view = memoryview(ram_image)
        image: np.ndarray = np.frombuffer(mem_view, np.uint8)
        width, height = self.camera.image_dimensions # 输出图像的分辨率
        image.shape = (height, width, 3)
        image = np.flipud(image)
        return image