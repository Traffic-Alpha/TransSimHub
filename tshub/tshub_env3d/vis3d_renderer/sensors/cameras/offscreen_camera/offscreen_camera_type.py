'''
@Author: WANG Maonan
@Date: 2024-07-15 12:12:53
@Description: Offscreen Camera 的类型
@LastEditTime: 2024-07-15 21:27:25
'''
import enum

class OffscreenCameraType(enum.Enum):
    BEV = 'Off_BEV_Camera'
    Front = 'Off_Front_Camera'
    Chase = 'Off_Chase_Camera'
    Side = 'Off_Side_Camera'