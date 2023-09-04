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
- last_step_mean_speed：上一次观测中，这个探测器位置的车的平均速度，-1表示没有车
- jam_length_vehicle：排队车的数量
- jam_length_meters：排队车的长度
- last_step_occupancy：车道的平均占有率

动作定义
-----------
- keep_lane： 保持当前车道，速度增加3，但小于最高限速（15）
- slow_down：速度减少3，但要高于最低限速（2）
- change_lane_left：向左侧变道，且速度减少2，但高于最低限速（2）
- change_lane_right：向右侧变道，且速度减少2，但高于最低限速（2）


Action=(target_speed, lane_change)
    - target_speed: Baseline target speed (controller may give more or less regardless). Type=float.
    - lane_change: Discrete lane change value. Can be one of 
        + -1 : change to right lane
        + 0 : keep to current lane
        + 1 : change to left lane