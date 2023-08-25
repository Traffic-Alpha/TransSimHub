'''
@Author: WANG Maonan
@Date: 2023-08-25 17:09:18
@Description: Choose Next Phase
@LastEditTime: 2023-08-25 17:55:45
'''
from .base_tls import BaseTLS

class choose_next_phase(BaseTLS):
    def __init__(self, ts_id, sumo, 
                 delta_time:int=5, 
                 min_green:int=5, 
                 yellow_time:int=3, 
                ):
        super().__init__(ts_id, sumo)
        
        self.delta_time = delta_time # 每隔 delta_time 做一次动作
        self.min_green = min_green # 最小绿灯时间
        self.yellow_time = yellow_time # 黄灯+红灯时间

        assert delta_time > yellow_time, "Time between actions must be at least greater than yellow time."
        assert delta_time < 3600, "Time between actions must be smaller than 3600s (否则信号灯会自动跳转到下一个相位)."
        
        self.green_phase = 0 # 初始的 green phase 为 0, 所在的 phase id
        self.time_since_last_phase_change = 0
        self.is_yellow = False
        
    
    def set_next_phases(self, new_phase:int):
        """设置下一阶段的信号灯方案, 需要将方案转换为绿灯的时间长度
        """
        new_phase = int(new_phase) # 切换到 new_phase_id
        if (self.green_phase == new_phase) or \
            (self.time_since_last_phase_change < self.yellow_time + self.min_green): # 当相位不改变, 或是相位持续时间没到 min_green
            self.sumo.trafficlight.setPhase(self.id, self.green_phase)
            self.logger.debug('Time: {}; Keep: Action: {}; State: {};'.format(
                                                    self.env.sim_step, 
                                                    self.green_phase, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            # self.sumo.trafficlight.setRedYellowGreenState(self.id, self.all_phases[self.green_phase].state)
            self.next_action_time = self.env.sim_step + self.delta_time # 重置下一次执行 action 的时间
        else:
            self.sumo.trafficlight.setPhase(self.id, self.yellow_dict[(self.green_phase, new_phase)])  # turns yellow
            self.logger.debug('Time: {}; Yellow: Action: {}; State: {};'.format(
                                                    self.env.sim_step, 
                                                    new_phase, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            # self.sumo.trafficlight.setRedYellowGreenState(self.id, self.all_phases[self.yellow_dict[(self.green_phase, new_phase)]].state)
            self.green_phase = new_phase # 切换 phase
            self.next_action_time = self.env.sim_step + self.delta_time + self.yellow_time # 这里需要加上黄灯的时间, 因为首先会切换为黄灯, 然后再经过 delta time 才会进行切换（之后的版本需要切换为这个）
            # self.next_action_time = self.env.sim_step + self.delta_time # 目前的版本使用的 next time 的计算方式, 没有加上黄灯的时间
            self.is_yellow = True # 目前是黄灯, 下一个切换为绿灯
            self.time_since_last_phase_change = 0

    def update(self):
        self.time_since_last_phase_change += 1
        if self.is_yellow and self.time_since_last_phase_change == self.yellow_time:
            self.sumo.trafficlight.setPhase(self.id, self.green_phase)
            self.logger.debug('Time {}; Yellow -> Green: Action: {}; State: {};'.format(
                                                    self.env.sim_step, 
                                                    self.green_phase, 
                                                    self.sumo.trafficlight.getRedYellowGreenState(self.id)))
            # self.sumo.trafficlight.setRedYellowGreenState(self.id, self.all_phases[self.green_phase].state)
            self.is_yellow = False