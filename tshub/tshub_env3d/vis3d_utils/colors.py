'''
@Author: WANG Maonan
@Date: 2024-07-05 22:18:36
@Description: 3D 渲染过程中需要使用的颜色
@LastEditTime: 2024-07-05 22:18:36
'''
from enum import Enum

# Color channel order: RGBA
class Colors(Enum):
    """Common simulation colors as RGBA values.
    """
    Red = (210 / 255, 30 / 255, 30 / 255, 1)
    Rose = (196 / 255, 0, 84 / 255, 1)
    Maroon = (128 / 255, 0, 0, 1)
    Orange = (237 / 255, 109 / 255, 0, 1)
    Yellow = (255 / 255, 190 / 255, 40 / 255, 1)
    GreenTransparent = (98 / 255, 178 / 255, 48 / 255, 0.3)
    Silver = (192 / 255, 192 / 255, 192 / 255, 1)
    Black = (0, 0, 0, 1)
    Green = (30 / 255, 210 / 255, 30 / 255, 1)

    DarkBlue = (5 / 255, 5 / 255, 70 / 255, 1)
    Blue = (0, 153 / 255, 1, 1)
    LightBlue = (173 / 255, 216 / 255, 230 / 255, 1)
    BlueTransparent = (60 / 255, 170 / 255, 200 / 255, 0.6)

    DarkCyan = (47 / 255, 79 / 255, 79 / 255, 1)
    CyanTransparent = (48 / 255, 181 / 255, 197 / 255, 0.5)

    DarkPurple = (50 / 255, 30 / 255, 50 / 255, 1)
    Purple = (127 / 255, 0, 127 / 255, 1)

    DarkGrey = (80 / 255, 80 / 255, 80 / 255, 1)
    Grey = (119 / 255, 136 / 255, 153 / 255, 1)
    LightGreyTransparent = (221 / 255, 221 / 255, 221 / 255, 0.1)

    OffWhite = (200 / 255, 200 / 255, 200 / 255, 1)
    White = (1, 1, 1, 1)


class SceneColors(Enum):
    """Simulation feature colors as RGBA values
    """
    Agent = Colors.Red.value
    SocialAgent = Colors.Blue.value
    SocialVehicle = Colors.Silver.value

    Road = Colors.DarkGrey.value
    EgoWaypoint = Colors.CyanTransparent.value
    EgoDrivenPath = Colors.CyanTransparent.value
    BubbleLine = Colors.LightGreyTransparent.value
    MissionRoute = Colors.GreenTransparent.value
    LaneDivider = Colors.OffWhite.value
    EdgeDivider = Colors.Yellow.value

    SignalUnknown = Colors.Grey.value
    SignalStop = Colors.Maroon.value
    SignalCaution = Colors.Yellow.value
    SignalGo = Colors.Green.value