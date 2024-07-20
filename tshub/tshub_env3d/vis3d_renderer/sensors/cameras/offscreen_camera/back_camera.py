'''
@Author: WANG Maonan
@Date: 2024-07-15 12:05:43
@Description: 将 Camera 防止在车的后方
@LastEditTime: 2024-07-21 01:23:42
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
class OffscreenBackCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    def init_pos(self, pose:Pose, height:float=2, distance_back:float=10, *args, **kwargs) -> None:
        """初始化 camera 的位置
        """
        self.update(pose, height, distance_back, *args, **kwargs)
        
    def update(self, pose: Pose, height:float=2, distance_back:float=10, *args, **kwargs):
        pos, heading = pose.as_panda3d()
        # Reverse the heading by 180 degrees to face the rear
        heading += 180

        # Calculate the rear position based on the vehicle's heading
        self.camera_np.setPos(pos[0], pos[1], pos[2] + height)
        self.camera_np.lookAt(
            pos[0] + distance_back * np.cos(np.radians(heading)),
            pos[1] + distance_back * np.sin(np.radians(heading)),
            pos[2] + 1
        )
        self.camera_np.setH(heading) # Adjusted heading to face rear
        

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()


@dataclass
class OffscreenBackLeftCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    def init_pos(self, pose:Pose, height:float=2, distance_back:float=10, *args, **kwargs) -> None:
        """初始化 camera 的位置
        """
        self.update(pose, height, distance_back, *args, **kwargs)

    def update(self, pose: Pose, height:float=2, distance_back:float=10, *args, **kwargs):
        pos, heading = pose.as_panda3d()
        # Reverse the heading by 180 degrees and adjust for left orientation
        adjusted_heading = heading + 150  # 180 - 30

        # Calculate the rear-left position based on the vehicle's heading
        self.camera_np.setPos(pos[0], pos[1], pos[2] + height)
        self.camera_np.lookAt(
            pos[0] + distance_back * np.cos(np.radians(adjusted_heading)),
            pos[1] + distance_back * np.sin(np.radians(adjusted_heading)),
            pos[2] + 1
        )
        self.camera_np.setH(adjusted_heading)  # Adjusted heading to face rear-left


    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()
    

@dataclass
class OffscreenBackRightCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    def init_pos(self, pose:Pose, height:float=2, distance_back:float=10, *args, **kwargs) -> None:
        """初始化 camera 的位置
        """
        self.update(pose, height, distance_back, *args, **kwargs)

    def update(self, pose: Pose, height:float=2, distance_back:float=10, *args, **kwargs):
        pos, heading = pose.as_panda3d()
        # Reverse the heading by 180 degrees and adjust for right orientation
        adjusted_heading = heading - 150  # 180 + 30

        # Calculate the rear-right position based on the vehicle's heading
        self.camera_np.setPos(pos[0], pos[1], pos[2] + height)
        self.camera_np.lookAt(
            pos[0] + distance_back * np.cos(np.radians(adjusted_heading)),
            pos[1] + distance_back * np.sin(np.radians(adjusted_heading)),
            pos[2] + 1
        )
        self.camera_np.setH(adjusted_heading)  # Adjusted heading to face rear-right

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()