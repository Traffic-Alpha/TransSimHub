'''
@Author: WANG Maonan
@Date: 2026-07-10
@Description: 统一的 offscreen 相机 —— 由 CameraRig 驱动, 取代原先 11 个几乎重复的相机子类
(front/back/side/bev/junction/aircraft). 相机几何 (eye/target) 来自渲染器无关的
scene.sensor_rig.compute_camera_pose; 本类只负责 Panda 侧的 setPos/lookAt/setH.
'''
from typing import Tuple
from dataclasses import dataclass

from .base_offscreen_camera import BaseOffscreenCamera, _BaseOffCameraMixin
from tshub.tshub_env3d.core.utils.coordinates import Pose
from tshub.tshub_env3d.core import CameraRig, compute_camera_pose


@dataclass
class OffscreenCamera(_BaseOffCameraMixin, BaseOffscreenCamera):
    """由 CameraRig 驱动的通用 offscreen 相机.

    - 路口相机 (carrier='tls'): 架在地面绝对高度 (carrier_z=0, 高度由传入的 height 给出);
    - 其余相机 (vehicle/aircraft): 高度相对载体 (carrier_z=载体自身高度, height 缺省用 rig.height);
    - set_heading=True 的相机在 lookAt 后再 setH 对齐到载体航向 + yaw_offset;
      当前主要用于车载 BEV 的画面朝向稳定。
    """
    rig: CameraRig = None
    carrier_dimensions: Tuple[float, float, float] = None

    def init_pos(self, pose: Pose, height: float = None, *args, **kwargs) -> None:
        self.update(pose, height, *args, **kwargs)

    def update(self, pose: Pose, height: float = None, *args, **kwargs) -> None:
        pos, heading = pose.as_panda3d()
        carrier_z = 0.0 if self.rig.carrier == 'tls' else pos[2]
        eye, target = compute_camera_pose(
            self.rig, (pos[0], pos[1]), heading,
            height_override=height, carrier_z=carrier_z,
            carrier_dimensions=self.carrier_dimensions,
        )
        self.camera_np.setPos(*eye)
        self.camera_np.lookAt(*target)
        if self.rig.set_heading:
            self.camera_np.setH(heading + self.rig.yaw_offset_deg)

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()
