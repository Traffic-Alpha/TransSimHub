'''
@Author: WANG Maonan
@Date: 2024-07-19 23:20:18
@Description: 这里的相机位置是固定不动的, 也就是摄像头
@LastEditTime: 2024-07-21 02:18:29
'''
import numpy as np
from typing import Tuple
from dataclasses import dataclass

from .base_offscreen_camera import (
    BaseOffscreenCamera,
    _BaseOffCameraMixin
)
from .....vis3d_utils.coordinates import Pose

@dataclass
class OffscreenJunctionFrontCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    """路口摄像头, 拍摄车头, 也就是正对着 in road
    """
    def init_pos(self, pose: Pose, height:float=10, *args, **kwargs) -> None:
        pos, heading = pose.as_panda3d()
        heading += 180 # 这里的朝向需要相反, 相当于看向路的出口

        # Calculate the front position based on the vehicle's heading
        self.camera_np.setPos(
            pos[0],
            pos[1],
            height
        ) # 設置攝像頭的位置, 這裏有高度

        self.camera_np.lookAt(
            pos[0] + 20 * np.cos(np.radians(heading)),
            pos[1] + 20 * np.sin(np.radians(heading)),
            0
        )
        self.camera_np.setH(heading) # 航向角
    
    def update(self, *args, **kwargs) -> None:
        """这里是一个固定的摄像头, 不需要更新位置
        """
        pass
        
    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()


@dataclass
class OffscreenJunctionBackCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    """路口摄像头, 拍摄车尾, 也就是对着 in road 的出口
    """
    def init_pos(self, pose: Pose, height:float=10, *args, **kwargs) -> None:
        pos, heading = pose.as_panda3d()

        # Calculate the front position based on the vehicle's heading
        self.camera_np.setPos(pos[0],pos[1],height)

        self.camera_np.lookAt(
            pos[0] + 10 * np.cos(np.radians(heading)),
            pos[1] + 10 * np.sin(np.radians(heading)),
            1
        )
        self.camera_np.setH(heading) # 航向角
    
    def update(self, *args, **kwargs) -> None:
        """这里是一个固定的摄像头, 不需要更新位置
        """
        pass
        
    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()