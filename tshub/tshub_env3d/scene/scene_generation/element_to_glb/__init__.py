'''
@Author: WANG Maonan
@Date: 2024-07-13 07:25:27
@Description: 分别将地图元素转换为 glb
@LastEditTime: 2024-07-13 07:43:21
'''
import trimesh
from typing import Final

OLD_TRIMESH: Final[bool] = tuple(int(d) for d in trimesh.__version__.split(".")) <= (
    3,
    9,
    29,
)