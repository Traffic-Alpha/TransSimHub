'''
@Author: WANG Maonan
@Date: 2024-07-21 03:08:43
@Description: 飞行器上面的飞行器
@LastEditTime: 2024-07-21 03:58:09
'''
from typing import Tuple
from dataclasses import dataclass

from .base_offscreen_camera import (
    BaseOffscreenCamera,
    _BaseOffCameraMixin
)
from .....vis3d_utils.coordinates import Pose

@dataclass
class OffscreenAircraftCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    """无人机上面的相机, 从无人机往下拍
    """
    def init_pos(self, pose:Pose, *args, **kwargs) -> None:
        """初始化 camera 的位置
        """
        self.update(pose, *args, **kwargs)

    def update(self, pose: Pose, *args, **kwargs) -> None:
        """Update the location of the camera (这里 Update 可以使得 camera 跟踪车辆或是其他的 object).
        Args:
            pose:
                The pose of the camera target.
            height:
                The height of the camera above the camera target.
        """
        pos, heading = pose.as_panda3d()
        # 俯视的角度
        self.camera_np.setPos(pos[0], pos[1], pos[2])
        self.camera_np.lookAt(pos[0], pos[1], 2) # 查看 UAV/UAM 正下方
        # self.camera_np.setH(heading) # 航向角

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()