'''
@Author: WANG Maonan
@Date: 2024-07-15 12:04:36
@Description: This camera will be positioned at the side of the vehicle.
@LastEditTime: 2024-07-15 12:06:52
'''
import numpy as np
from typing import Tuple
from dataclasses import dataclass

from .base_offscreen_camera import _P3DCameraMixin, OffscreenCamera
from .....vis3d_utils.coordinates import Pose


@dataclass
class OffscreenSideCamera(_P3DCameraMixin, OffscreenCamera):
    def update(self, pose: Pose, distance_side: float, *args, **kwargs):
        pos, heading = pose.as_panda3d()
        # Calculate the side position based on the vehicle's heading
        self.camera_np.setPos(
            pos[0] - np.cos(heading) * distance_side,
            pos[1] - np.sin(heading) * distance_side,
            pos[2]
        )
        self.camera_np.lookAt(*pos)

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()