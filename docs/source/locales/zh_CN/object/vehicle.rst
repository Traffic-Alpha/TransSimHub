机动车
=========
Vehicle（机动车）可用于在 `SUMO` 中仿真机动车，例如：自动驾驶汽车、卡车、小轿车等。
关于 Vehicle 的代码例子 `TransSimHub Vehicle Example <https://github.com/Traffic-Alpha/TransSimHub/tree/main/examples/vehicles>`_
下面介绍 Vehicle 的 状态（`state`）， 动作类型（ `action type`）和使用例子:

状态定义
-----------
- **机动车 id** (str):场景中每一个 vehicle 的唯一 ID，用于区分不同的 vehicle
- **动作类型 action_type** (str): vehicle的动作控制类型, 目前支持 `keep_lane`, `slow_down`, `change_lane_left`, `change_lane_right`
- **位置 position** (Tuple[float]):vehicle所在的位置
- **速度 speed** (float): vehicle当前车速
- **路 road_id** (str): vehicle 行驶道路的 ID, 场景中每条道路有唯一 ID
- **车道 lane_id** (str): vehicle 所在车道的 ID, 
- **边 edges** (list[str]): vehicle 已经经过的边
- **下一个相位 next_tls** (List[str]): vehicle 将通过的交通信号灯的 ID
- **等待时间 waiting_time** (float): vehicle 在交通路口的等待时间

探测器
---------------
- last_step_mean_speed：上一次观测中，这个探测器位置的车的平均速度，-1表示没有车
- jam_length_vehicle：排队车的数量
- jam_length_meters：排队车的长度
- last_step_occupancy：车道的平均占有率

动作定义
-----------
1. **keep_lane**： vehicle保持当前车道，速度增加3，但小于最高限速（15）
2. **slow_down**：vehicle速度减少3，但要高于最低限速（2）
3. **change_lane_left**：vehicle向左侧变道，且速度减少2，但高于最低限速（2）
4. **change_lane_right**：vehicle向右侧变道，且速度减少2，但高于最低限速（2）


Action=(target_speed, lane_change)
    - target_speed: Baseline target speed (controller may give more or less regardless). Type=float.
    - lane_change: Discrete lane change value. Can be one of 
        + -1 : change to right lane
        + 0 : keep to current lane
        + 1 : change to left lane


Vehicle 控制例子
-----------------------