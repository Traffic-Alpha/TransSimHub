'''
@Author: WANG Maonan
@Date: 2023-08-25 17:09:18
@Description: Choose Next Phase
@LastEditTime: 2023-08-28 16:28:06
'''
from loguru import logger
from .base_tls import BaseTLS

class choose_next_phase(BaseTLS):
    def __init__(self, ts_id, sumo, 
                 delta_time:int=5, 
                 yellow_time:int=3, 
                ) -> None:
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
            self.next_action_time = self.sim_step + self.delta_time # 重置下一次执行 action 的时间
        else:
            self.sumo.trafficlight.setPhase(self.id, self.yellow_dict[(self.phase_index, new_phase)])  # turns yellow
            logger.debug('SIM: Time: {}; Yellow: Action: {}; State: {};'.format(
                                                    self.sim_step, 
                                                    new_phase, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            self.phase_index = new_phase # 切换 phase
            self.next_action_time = self.sim_step + self.delta_time + self.yellow_time # 这里需要加上黄灯的时间, 因为首先会切换为黄灯, 然后再经过 delta time 才会进行切换（之后的版本需要切换为这个）
            self.is_yellow = True # 目前是黄灯, 下一个切换为绿灯
            self.time_since_last_phase_change = 0

    def update(self):
        self.time_since_last_phase_change += 1
        if self.is_yellow and self.time_since_last_phase_change == self.yellow_time:
            self.sumo.trafficlight.setPhase(self.id, self.phase_index)
            logger.debug('SIM: Time {}; Yellow -> Green: Action: {}; State: {};'.format(
                                                    self.sim_step, 
                                                    self.phase_index, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            self.is_yellow = False