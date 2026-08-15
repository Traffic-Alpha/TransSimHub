'''
@Author: WANG Maonan
@Date: 2024-07-06 20:56:50
@Description: 定义 Masks, 决定哪些对象会被渲染
@LastEditTime: 2024-07-14 20:26:47
'''
from panda3d.core import BitMask32

class CamMask():
    AllOn = BitMask32.allOn() # 全部是 1
    AllOff = BitMask32.allOff() # 全部是 0
    VehMask = BitMask32.bit(1) # 车辆的 mask
    MapMask = BitMask32.bit(2) # 环境 mask, 包括 map, road, line
    GroundMask = BitMask32.bit(3) # 环境的 ground
    SkyBoxMask = BitMask32.bit(4) # skybox
    AircraftMask = BitMask32.bit(5) # 飞行器


# rgb 与 seg 相机都渲染整个场景 (seg 靠 shader 区分类别, 不靠 mask 剔除), 故统一用全场景 mask.
FULL_CAM_MASK = (
    CamMask.VehMask | CamMask.MapMask | CamMask.GroundMask |
    CamMask.SkyBoxMask | CamMask.AircraftMask
)
