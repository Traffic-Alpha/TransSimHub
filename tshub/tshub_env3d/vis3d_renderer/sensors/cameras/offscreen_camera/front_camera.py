'''
@Author: WANG Maonan
@Date: 2024-07-15 12:03:08
@Description: This camera will be positioned at the front of the vehicle.
@LastEditTime: 2024-07-15 22:04:32
'''
import math
import numpy as np
from typing import Tuple
from dataclasses import dataclass

from .base_offscreen_camera import _P3DCameraMixin, OffscreenCamera
from .....vis3d_utils.coordinates import Pose


@dataclass
class OffscreenFrontCamera(_P3DCameraMixin, OffscreenCamera):
    def update(self, pose: Pose, distance_front: float=2, height_offset: float=3,  *args, **kwargs):
        pos, heading = pose.as_panda3d()

        # Calculate the front position based on the vehicle's heading
        # 俯视的角度
        self.camera_np.setPos(pos[0], pos[1], height_offset)
        self.camera_np.lookAt(
            pos[0] + distance_front * math.cos(math.radians(heading)),
            pos[1] + distance_front * math.sin(math.radians(heading)),
            2
        )
        self.camera_np.setH(heading) # 航向角
        

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()