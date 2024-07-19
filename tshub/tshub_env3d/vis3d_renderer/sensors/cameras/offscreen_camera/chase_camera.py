'''
@Author: WANG Maonan
@Date: 2024-07-15 12:05:43
@Description: This camera will follow the vehicle from behind at a certain distance and height.
@LastEditTime: 2024-07-15 12:05:44
'''
import numpy as np
from typing import Tuple
from dataclasses import dataclass

from .base_offscreen_camera import _P3DCameraMixin, OffscreenCamera
from .....vis3d_utils.coordinates import Pose

@dataclass
class OffscreenChaseCamera(_P3DCameraMixin, OffscreenCamera):
    def update(self, pose: Pose, distance_back: float, height_above: float, *args, **kwargs):
        pos, heading = pose.as_panda3d()
        # Calculate the chase position based on the vehicle's heading
        self.camera_np.setPos(
            pos[0] - np.sin(heading) * distance_back,
            pos[1] + np.cos(heading) * distance_back,
            pos[2] + height_above
        )
        self.camera_np.lookAt(*pos)

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()