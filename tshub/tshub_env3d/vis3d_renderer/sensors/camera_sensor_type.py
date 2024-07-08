'''
@Author: WANG Maonan
@Date: 2024-07-07 22:15:41
@Description: 定义不同的 Camera Sensor (Sensro 依赖于不同的 Camera)
@LastEditTime: 2024-07-07 22:15:42
'''
from enum import Enum

class CameraSensorID(Enum):
    """Describes default names for camera configuration.
    """
    DRIVABLE_AREA_GRID_MAP = "drivable_area_grid_map"
    TOP_DOWN_RGB = "top_down_rgb"
    OCCUPANCY_GRID_MAP = "ogm"
    OCCLUSION = "occlusion_map"