'''
@Author: WANG Maonan
@Date: 2023-08-25 17:09:18
@Description: Choose Next Phase (Synchronize)
@LastEditTime: 2024-04-24 20:43:54
'''
from loguru import logger
from .base_tls import BaseTLS

class choose_next_phase_syn(BaseTLS):
    def __init__(self, ts_id, sumo, 
                 delta_time:int=5, 
                 yellow_time:int=3, 
                ) -> None:
        """Choose Next Phase 的同步版本。在多个信号灯一起控制的时候，由于黄灯的存在，会导致信号灯无法同步作出动作。

        下面我们来看一个具体的例子，假设现在有两个信号灯，分别是 Int-1 和 Int-2，那么：
        -> Choose Next Phase 多路口情况：
            1. 如果 Int-1 切换相位，Int-2 保持当前相位
            2. 那么 Int-1 需要首先经历黄灯时间，然后再变为绿灯
            3. 而 Int-2 由于是保持绿灯，所以只有绿灯时间，那么 Int-2 就会优先进行动作
            4. 下面是两个信号灯做动作的时间分布，可以看到两个 INT 做动作的时刻是不一样的
            Int-1: |-----5s-----|---3s---|-----5s-----|，作出了切换，下一次动作时间是在 13s
                   |---Phase1---|--------Phase2-------|
            
            Int-2: |-----5s-----|-----5s-----|，没有作出切换，下一次动作时间是在 10s
                   |---Phase1---|---Phase1---|

        -> Choose Next Phase (Synchronize)
            1. 同样，I1 切换相位，I2 保持当前相位；
            2. 与 ``Choose Next Phase'' 不同，``Choose Next Phase (Synchronize)'' 的绿灯时间会包含黄灯的时间
            3. 下面是两个信号灯做动作的时间分布，我们加长了绿灯的时间，使得信号灯可以同步：

            Int-1: |-----5s-----|---3s---|-----5s-----|，作出了切换，下一次动作时间是在 13s
                   |---Phase1---|--------Phase2-------|
            
            Int-2: |-----5s-----|---------8s----------|，没有作出切换，我们使得第二次绿灯时间持续是 8s，使得下一次动作也在 13s
                   |---Phase1---|-------Phase1--------|

        Args:
            ts_id (str): 信号灯的 ID
            sumo (traci): 获得仿真数据
            delta_time (int, optional): 两次动作的间隔时间. Defaults to 5.
            yellow_time (int, optional): 黄灯时间. Defaults to 3.
        """
        super().__init__(ts_id, sumo)
        
        self.delta_time = delta_time # 每隔 delta_time 做一次动作
        self.yellow_time = yellow_time # 黄灯+红灯时间

        assert delta_time > yellow_time, "Time between actions must be at least greater than yellow time."
        assert delta_time < 3600, "Time between actions must be smaller than 3600s (否则信号灯会自动跳转到下一个相位)."
        
        self.phase_index = 0 # 初始的 green phase 为 0, 所在的 phase id
        self.time_since_last_phase_change = 0
        self.is_yellow = False
        self.next_action_time = 0
        
    
    def set_next_phases(self, new_phase:int) -> None:
        """设置下一阶段的信号灯方案, 需要将方案转换为绿灯的时间长度
        """
        new_phase = int(new_phase) # 切换到 new_phase_id
        if self.phase_index == new_phase: # 当相位不改变
            self.sumo.trafficlight.setPhase(self.id, self.phase_index)
            logger.debug('SIM: Time: {}; Keep: Action: {}; State: {};'.format(
                                                    self.sim_step,
                                                    self.phase_index, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            # 重置下一次执行 action 的时间, 为了确保动作可以同步, 这里也需要加上黄灯时间
            self.next_action_time = self.sim_step + self.delta_time + self.yellow_time
        else: # 相位改变, 首先切换为黄灯, 接着使用 update 切换为绿灯
            self.sumo.trafficlight.setPhase(self.id, self.yellow_dict[(self.phase_index, new_phase)])  # turns yellow
            logger.debug('SIM: Time: {}; Yellow: Action: {}; State: {};'.format(
                                                    self.sim_step, 
                                                    new_phase, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            self.phase_index = new_phase # 切换 phase
            # 这里需要加上黄灯的时间, 因为首先会切换为黄灯, 然后再经过 delta time 才会进行切换（之后的版本需要切换为这个）
            self.next_action_time = self.sim_step + self.delta_time + self.yellow_time
            self.is_yellow = True # 目前是黄灯, 下一个切换为绿灯
            self.time_since_last_phase_change = 0

    def update(self):
        self.time_since_last_phase_change += 1
        if self.is_yellow and self.time_since_last_phase_change == self.yellow_time:
            self.sumo.trafficlight.setPhase(self.id, self.phase_index) # 黄灯时间到, 切换为绿灯
            logger.debug('SIM: Time {}; Yellow -> Green: Action: {}; State: {};'.format(
                                                    self.sim_step, 
                                                    self.phase_index, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            self.is_yellow = False