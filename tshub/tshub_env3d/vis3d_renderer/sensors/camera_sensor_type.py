'''
@Author: WANG Maonan
@Date: 2024-07-07 22:15:41
@Description: 定义不同的 Camera Sensor
不同的视角
是否有 mask
@LastEditTime: 2024-07-15 22:48:45
'''
from enum import Enum

class CameraSensorID(Enum):
    """Describes default names for camera configuration.
    """
    BEV_ALL = "bev_all"
    BEV_VEHICLE = "bev_vehicle"
    FRONT_ALL = "front_all"
    FRONT_VEHICLE = "front_vehicle"
    
    DRIVABLE_AREA_GRID_MAP = "drivable_area_grid_map"
    TOP_DOWN_RGB = "top_down_rgb"
    OCCUPANCY_GRID_MAP = "ogm"
    OCCLUSION = "occlusion_map"