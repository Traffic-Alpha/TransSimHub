'''
@Author: WANG Maonan
@Date: 2024-07-15 12:12:53
@Description: Offscreen Camera 的类型
@LastEditTime: 2024-07-20 22:41:19
'''
import enum

class OffscreenCameraType(enum.Enum):
    BEV = 'Off_BEV_Camera'
    FIX = "Off_FIX_Camera"
    # 摄像头在前方
    Front = 'Off_Front_Camera'
    Front_LEFT = 'Off_FrontLeft_Camera'
    Front_RIGHT = 'Off_FrontRight_Camera'    
    # 摄像头在后方
    Back = 'Off_Back_Camera'
    Back_LEFT = 'Off_BackLeft_Camera'
    Back_RIGHT = 'Off_BackRight_Camera'      