'''
@Author: WANG Maonan
@Date: 2024-07-07 22:04:09
@Description: 创建 Off-Screen Camera, 在 Sensor 中会具体定义 Camera 的具体使用
@LastEditTime: 2024-07-15 12:22:21
'''
from typing import Tuple
from dataclasses import dataclass

from .base_offscreen_camera import _P3DCameraMixin, OffscreenCamera
from .....vis3d_utils.coordinates import Pose

@dataclass
class OffscreenBEVCamera(_P3DCameraMixin, OffscreenCamera):
    """A camera used for rendering images to a graphics buffer (这里是 BEV 的视角).
    """
    def update(self, pose: Pose, height: float, *args, **kwargs):
        """Update the location of the camera (这里 Update 可以使得 camera 跟踪车辆或是其他的 object).
        Args:
            pose:
                The pose of the camera target.
            height:
                The height of the camera above the camera target.
        """
        pos, heading = pose.as_panda3d()
        # 俯视的角度
        self.camera_np.setPos(pos[0], pos[1], height)
        self.camera_np.lookAt(*pos)
        self.camera_np.setH(heading) # 航向角

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()