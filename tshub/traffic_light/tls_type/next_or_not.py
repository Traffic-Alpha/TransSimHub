'''
@Author: WANG Maonan
@Date: 2023-08-25 17:09:32
@Description: Next or Not
@LastEditTime: 2023-08-28 16:16:53
'''
from loguru import logger
from .base_tls import BaseTLS

class next_or_not(BaseTLS):
    def __init__(self, ts_id, sumo,
                delta_time:int=5, 
                yellow_time:int=3,
            ):
        super().__init__(ts_id, sumo)
        
        self.delta_time = delta_time # 每隔 5s 做一次动作
        self.yellow_time = yellow_time # 黄灯

        assert delta_time > yellow_time, "Time between actions must be at least greater than yellow time."
        assert delta_time < 3600, "Time between actions must be smaller than 3600s (否则信号灯会自动跳转到下一个相位)."
        
        self.phase_index = 0 # 目前在第几个绿灯相位
        self.time_since_last_phase_change = 0
        self.is_yellow = False
        self.next_action_time = 0
        
    
    def set_next_phases(self, keep_change:int) -> None:
        """是否切换信号灯, keep_change 只可以选择 0 或是 1
        """
        assert keep_change in [0, 1], f'Next or Not 动作只可以是 0 或是 1, 现在是 {keep_change}'
        keep_change_signal = bool(keep_change) # 是否切换, keep->True, bool(1), change->False, bool(0)
        if keep_change_signal: # 当相位不改变
            self.sumo.trafficlight.setPhase(self.id, self.phase_index) # setPhase 会立即进行切换, 不会等待当前的 state 结束
            logger.debug('SIM: Time: {}; Keep: Action: {}; Phase Index: {}; State: {};'.format(
                                                    self.sim_step, 
                                                    keep_change,
                                                    self.phase_index, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            self.next_action_time = self.sim_step + self.delta_time
        else: # 切换到下一个绿灯相位
            self.next_phase_index = (self.phase_index + 1)%self.num_green_phases
            self.sumo.trafficlight.setPhase(self.id, self.yellow_dict[(self.phase_index, self.next_phase_index)])  # turns yellow
            logger.debug('SIM: Time: {}; Yellow: Action: {}; State: {};'.format(
                                                    self.sim_step, 
                                                    keep_change, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            self.phase_index = self.next_phase_index # 切换 phase
            self.is_yellow = True # 目前是黄灯, 下一个切换为绿灯
            self.time_since_last_phase_change = 0
            self.next_action_time = self.sim_step + self.delta_time + self.yellow_time

    def update(self) -> None:
        """每进行一步仿真, 更新当前时间
        """
        self.time_since_last_phase_change += 1
        if self.is_yellow and self.time_since_last_phase_change == self.yellow_time:
            self.sumo.trafficlight.setPhase(self.id, self.phase_index)
            logger.debug('SIM: Time {}; Yellow -> Green: Phase Index: {}; State: {};'.format(
                                                    self.sim_step, 
                                                    self.phase_index, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            self.is_yellow = False