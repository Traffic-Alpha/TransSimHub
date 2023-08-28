'''
@Author: WANG Maonan
@Date: 2023-08-23 17:03:19
@Description: Vehicle Action Type
- 这两种动作都是设置变道和速度，在底层就是直接调用 SUMO 来进行控制的
@LastEditTime: 2023-08-28 19:49:01
'''
import enum

class vehicle_action_type(enum.Enum):
    Lane = 'lane'
    """
    Action= ``str``. Discrete lane action from one of
    
    + "keep_lane",
    + "slow_down", 
    + "change_lane_left", and 
    + "change_lane_right".
    """

    LaneWithContinuousSpeed = 'lane_continuous_speed'
    """
    Action=(target_speed, lane_change).

    + target_speed: Baseline target speed (controller may give more or less regardless). Type=float.
    + lane_change: Discrete lane change value. Can be one of 
        + -1 : change to right lane
        + 0 : keep to current lane
        + 1 : change to left lane
    """