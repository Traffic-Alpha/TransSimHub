'''
@Author: WANG Maonan
@Date: 2024-07-06 20:56:50
@Description: 定义 Masks, 决定哪些对象会被渲染
@LastEditTime: 2024-07-14 20:26:47
'''
from panda3d.core import BitMask32

class RenderMasks:
    """Rendering mask flags
    """
    NONE = 0x00 # 没有任何对象被隐藏，所有对象都会被渲染
    OCCUPANCY_HIDE = 0x01 # 隐藏那些被标记为 "occupancy" 的对象
    RGB_HIDE = 0x02 # 用于隐藏那些被标记为 "RGB" 的对象
    DRIVABLE_AREA_HIDE = 0x04 # 用于隐藏那些被标记为 "drivable area" 的对象

class CamMask():
    AllOn = BitMask32.allOn() # 全部是 1
    AllOff = BitMask32.allOff() # 全部是 0
    VehMask = BitMask32.bit(1) # 车辆的 mask
    MapMask = BitMask32.bit(2) # 环境 mask, 包括 map, road, line
    GroundMask = BitMask32.bit(3) # 环境的 ground
    SkyBoxMask = BitMask32.bit(4) # skybox