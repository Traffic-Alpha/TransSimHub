'''
@Author: WANG Maonan
@Date: 2024-07-15 12:12:53
@Description: Offscreen Camera 的类型
@LastEditTime: 2024-07-21 03:13:42
'''
import enum

class OffscreenCameraType(enum.Enum):
    # 十字路口摄像头
    Junction_Front = "Off_Junction_Front_Camera"
    Junction_Back = "Off_Junction_Back_Camera"
    # 摄像头在前方
    Front = 'Off_Front_Camera'
    Front_LEFT = 'Off_FrontLeft_Camera'
    Front_RIGHT = 'Off_FrontRight_Camera'    
    # 摄像头在后方
    Back = 'Off_Back_Camera'
    Back_LEFT = 'Off_BackLeft_Camera'
    Back_RIGHT = 'Off_BackRight_Camera'
    # 跟随车辆的视角
    BEV = 'Off_BEV_Camera'
    # 无人机的视角
    Aircraft = 'Off_Aircraft_Camera'