'''
@Author: WANG Maonan
@Date: 2023-08-29 17:59:13
@Description: Aircraft Action Type. Aircraft 共有四种动作类型，分别是：
1. 在固定的位置保持不动
2. 在固定的高度，只能水平面移动
3. 只能改变高度，水平方向无法移动
4. 可以同时改变高度和在水平方向移动，但是动作空间是离散的
@LastEditTime: 2023-08-29 20:30:59
'''
import enum

class aircraft_action_type(enum.Enum):
    Stationary = 'stationary'
    """
    Aircraft remains stationary at a fixed position.
    """

    HorizontalMovement = 'horizontal_movement'
    """
    Aircraft can only move in the horizontal plane while maintaining a fixed altitude.
    + Speed: float, 连续控制
    + Heading: int, 这里输入是 heading index, 平面内被分为 8 个 heading 角度
    """

    VerticalMovement = 'vertical_movement'
    """
    Aircraft can only change altitude while remaining in the same horizontal position.
    + Speed: float, 连续控制
    + Heading: int, 这里输入是 heading index, 共有三种情况, (1) 向上; (2) 向下; (3) 平稳
    """

    CombinedMovement = 'combined_movement'
    """
    Aircraft can simultaneously change altitude and move in the horizontal direction. The motion space is discrete.
    """
