Vehicle
============

状态定义
-----------
- id:车辆的编号
- action_type:车辆的动作控制类型
- position:车辆的位置
- speed: 当前车速
- road_id: 车辆行驶道路的 ID
- lane_id: 车辆所在车道的 ID
- edges: 车辆经过的边
- next_tls: 车辆将遇到的下一个交通信号灯的 ID
- waiting_time: 车辆的等待时间

动作定义
-----------
- keep_lane：
- slow_down：
- change_lane_left：
- change_lane_right：


Action=(target_speed, lane_change)
    - target_speed: Baseline target speed (controller may give more or less regardless). Type=float.
    - lane_change: Discrete lane change value. Can be one of 
        + -1 : change to right lane
        + 0 : keep to current lane
        + 1 : change to left lane