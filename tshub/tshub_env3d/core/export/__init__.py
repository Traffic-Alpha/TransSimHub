'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: 把仿真导出成离线渲染 (Blender/Cycles) 可消费的纯数据.

在线后端每步直接出图, 离线后端则先导出「剧集 (episode)」再后台批量渲染 ——
这样离线渲染不依赖 tshub/SUMO/Panda3D, 也不需要手工准备 .blend 文件.
@LastEditTime: 2026-08-15
'''
from .blender_export import (
    BlenderEpisodeExporter, build_camera_specs,
    sumo_heading_to_ccw_deg, heading_to_vec, front_bumper_to_center,
    MANIFEST_NAME, FRAMES_DIRNAME,
)

__all__ = [
    'BlenderEpisodeExporter', 'build_camera_specs',
    'sumo_heading_to_ccw_deg', 'heading_to_vec', 'front_bumper_to_center',
    'MANIFEST_NAME', 'FRAMES_DIRNAME',
]
