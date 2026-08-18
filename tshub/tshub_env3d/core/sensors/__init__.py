'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: 传感器的渲染器无关定义.

- sensor_rig  : 相机挂载规格 (挂在谁身上、相对位姿、fov、模态) 与位姿计算;
- seg_classes : 语义分割的类别 id / 名称 / 调色板.
两者都是「各渲染后端共用的单一真相源」.
@LastEditTime: 2026-08-15
'''
from .sensor_rig import (
    CameraRig, CAMERA_RIGS, BASE_CAMERA_RIGS, get_camera_rig, compute_camera_pose,
)
from .seg_classes import (
    SEG_CLASSES, SEG_NAME_TO_ID, SEG_ID_TO_NAME, SEG_ID_TO_COLOR,
    SEG_NAME_TO_COLOR, SEG_RENDER_COLORS, seg_color_to_label, seg_label_to_color,
)

__all__ = [
    'CameraRig', 'CAMERA_RIGS', 'BASE_CAMERA_RIGS', 'get_camera_rig', 'compute_camera_pose',
    'SEG_CLASSES', 'SEG_NAME_TO_ID', 'SEG_ID_TO_NAME', 'SEG_ID_TO_COLOR',
    'SEG_NAME_TO_COLOR', 'SEG_RENDER_COLORS', 'seg_color_to_label', 'seg_label_to_color',
]
