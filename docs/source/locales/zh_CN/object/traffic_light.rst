Traffic Signal Lights
===========================

状态定义
-----------
- tls_ids： 信号灯ID列表
- action_type：信号灯支持的动作类型
- traffic_lights: 包含场景中所有的交通信号灯
- movement_directions： 每一个 movement 的方向
- movement_lane_numbers：每一个 movement 包含的车道数
- phase2movements： 记录每个 phase 控制的 connection
- can_perform_action：是否可以执行动作
- delta_time：每隔delta_time做一次动作
- yellow_time：黄灯时间，两次相位的切换中，要加入黄灯

动作定义
-----------

- next_or_not: 是否保持当前相位
    Action= int
    + 0 选择下一个相位
    + 1 保持当前相位

- choose next phase: 选择下一个相位   

