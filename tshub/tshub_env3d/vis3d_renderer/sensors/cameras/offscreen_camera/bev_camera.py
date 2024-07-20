'''
@Author: WANG Maonan
@Date: 2024-07-07 22:04:09
@Description: BEV Camera (俯视摄像头)
@LastEditTime: 2024-07-21 03:11:56
'''
from typing import Tuple
from dataclasses import dataclass

from .base_offscreen_camera import (
    BaseOffscreenCamera,
    _BaseOffCameraMixin
)
from .....vis3d_utils.coordinates import Pose

@dataclass
class OffscreenBEVCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    """A camera used for rendering images to a graphics buffer (这里是 BEV 的视角).
    """
    def init_pos(self, pose:Pose, height:float=30, *args, **kwargs) -> None:
        """初始化 camera 的位置
        """
        self.update(pose, height, *args, **kwargs)

    def update(self, pose: Pose, height:float=30, *args, **kwargs) -> None:
        """Update the location of the camera (这里 Update 可以使得 camera 跟踪车辆或是其他的 object).
        Args:
            pose:
                The pose of the camera target.
            height:
                The height of the camera above the camera target.
        """
        pos, heading = pose.as_panda3d()
        # 俯视的角度
        self.camera_np.setPos(pos[0], pos[1], pos[2]+height)
        self.camera_np.lookAt(pos[0], pos[1], 2) # 查看 UAV/UAM 正下方
        self.camera_np.setH(heading) # 航向角, 这样让车道正前方

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()