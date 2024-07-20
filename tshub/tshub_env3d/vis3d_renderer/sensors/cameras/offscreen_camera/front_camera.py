'''
@Author: WANG Maonan
@Date: 2024-07-15 12:03:08
@Description: 摄像头放在车辆的前方, 
@LastEditTime: 2024-07-21 00:40:46
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
class OffscreenFrontCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    def init_pos(self, pose:Pose, height:float=2, distance_front:float=10, *args, **kwargs) -> None:
        """初始化 camera 的位置
        """
        self.update(pose, height, distance_front, *args, **kwargs)
    
    def update(self, pose:Pose, height:float=2, distance_front:float=10, *args, **kwargs) -> None:
        pos, heading = pose.as_panda3d()

        # Calculate the front position based on the vehicle's heading
        self.camera_np.setPos(pos[0], pos[1], pos[2] + height)
        self.camera_np.lookAt(
            pos[0] + distance_front * np.cos(np.radians(heading)),
            pos[1] + distance_front * np.sin(np.radians(heading)),
            pos[2] + 1
        )
        self.camera_np.setH(heading) # 航向角
    
    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()


@dataclass
class OffscreenFrontLeftCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    def init_pos(self, pose: Pose, height: float=2, distance_front:float=10, *args, **kwargs) -> None:
        """Initialize the position of the front-left camera."""
        self.update(pose, height, distance_front, *args, **kwargs)
    
    def update(self, pose: Pose, height: float=2, distance_front:float=10, *args, **kwargs) -> None:
        """Update the position and orientation of the front-left camera."""
        pos, heading = pose.as_panda3d()

        # Adjust heading for the left camera
        adjusted_heading = heading - 30  # Subtract 30 degrees for left orientation

        # Calculate the front-left position based on the vehicle's heading
        self.camera_np.setPos(pos[0], pos[1], pos[2] + height)
        self.camera_np.lookAt(
            pos[0] + distance_front * np.cos(np.radians(adjusted_heading)),
            pos[1] + distance_front * np.sin(np.radians(adjusted_heading)),
            pos[2] + 1
        )
        self.camera_np.setH(adjusted_heading)  # Maintain original heading for the vehicle
    
    @property
    def position(self) -> Tuple[float, float, float]:
        """Get the current position of the camera."""
        return self.camera_np.getPos()


@dataclass
class OffscreenFrontRightCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    def init_pos(self, pose: Pose, height:float=2, distance_front:float=10, *args, **kwargs) -> None:
        """Initialize the position of the front-right camera."""
        self.update(pose, height, distance_front, *args, **kwargs)
    
    def update(self, pose: Pose, height:float=2, distance_front:float=10, *args, **kwargs) -> None:
        """Update the position and orientation of the front-right camera."""
        pos, heading = pose.as_panda3d()

        # Adjust heading for the right camera
        adjusted_heading = heading + 30  # Add 30 degrees for right orientation

        # Calculate the front-right position based on the vehicle's heading
        self.camera_np.setPos(pos[0], pos[1], pos[2] + height)
        self.camera_np.lookAt(
            pos[0] + distance_front * np.cos(np.radians(adjusted_heading)),
            pos[1] + distance_front * np.sin(np.radians(adjusted_heading)),
            pos[2] + 1
        )
        self.camera_np.setH(adjusted_heading)  # Maintain original heading for the vehicle
    
    @property
    def position(self) -> Tuple[float, float, float]:
        """Get the current position of the camera."""
        return self.camera_np.getPos()