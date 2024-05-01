'''
@Author: WANG Maonan
@Date: 2024-05-01 14:57:18
@Description: 每个周期调整一次, 每次对所有 phase duration 进行微调.
1. 覆盖父类中的 build_phases, 此时需要让相位时间按照指定时间初始化
2. 完成功能函数 set_duration, 可以直接修改相位的时间长度
3. 覆盖父类中的 update, 不需要进行黄灯的切换
@LastEditTime: 2024-05-01 16:14:33
'''
import numpy as np
from typing import List
from loguru import logger
from .base_tls import BaseTLS

class adjust_cycle_duration(BaseTLS):
    def __init__(self, ts_id, sumo, 
                 delta_time:int=5,
                 min_green:int=5,
                 yellow_time:int=3,
                 init_green_duration:int=20, 
        ) -> None:
        super().__init__(ts_id, sumo)
        
        self.delta_time = delta_time # 动作的间隔时间
        self.min_green = min_green # 最小的绿灯时间, 不要把绿灯时间调整的太小了
        self.yellow_time = yellow_time
        self.init_green_duration = init_green_duration # 每个相位初始的绿灯时间
        self.green_loss = 0 # 所有黄灯时间的求和

        self.phase_index = -1 # 用于和其他 action type 对齐


    def build_phases(self):
        """将所有的绿灯 phase 时间设置为 init_green_duration

        Args:
            init_green_duration (int): 初始绿灯的时间
        """
        logics = self.sumo.trafficlight.getAllProgramLogics(self.id) # 获得当前信号灯的情况
        logic_index = [logic.programID for logic in logics].index(self.program_id)
        logic = logics[logic_index]

        # 设置初始绿灯和黄灯时长, 删除全红
        new_phase_list = []
        for phase in logic.phases:
            if 'G' in phase.state: # 修改绿灯的时长
                phase.duration = self.init_green_duration
                phase.minDur = self.init_green_duration
                phase.maxDur = self.init_green_duration
                new_phase_list.append(phase)
            elif 'y' in phase.state: # 修改黄灯时长
                phase.duration = self.yellow_time
                phase.minDur = self.yellow_time
                phase.maxDur = self.yellow_time
                new_phase_list.append(phase)
            else: # 例如全红等相位就不会包含在内
                pass
        logic.type = 0
        logic.phases = tuple(new_phase_list)
        self.sumo.trafficlight.setProgramLogic(self.id, logic)
        # setProgramLogic 对当前相位不生效, 因此需要单独设置第一相位的时间
        self.sumo.trafficlight.setPhaseDuration(tlsID=self.id, phaseDuration=self.init_green_duration)
        # 把 next_action_time 修改为初始
        self.next_action_time = 0 # 下一步开始的时间
        self.green_loss = sum(self.get_complete_durations()) - sum(self.get_green_durations()) # 更新一下时间, 黄灯的时间


    def set_next_phases(self, adjust_phase:List[float]):
        """设置下一阶段的信号灯方案, 需要将方案转换为绿灯的时间长度

        Args:
            adjust_phase (List[float]): 对一个周期内每一个相位时间进行调整.
            例如现在是四相位: 
            --> 相位持续时间为 [30, 30, 30, 30]; 
            --> 然后 action 是 [5, 0, -5, 5];
            --> 最终的相位持续时间变为 [35, 30, 25, 35]
        """
        self._touch_min_green = False
        green_durations = self.get_green_durations() # get green phase duration
        new_green_durations = [i+j for i,j in zip(green_durations, adjust_phase)] # 微调后的时间
        for phase_index, green_duration in enumerate(new_green_durations): # 确保不会小于 min_green
            if green_duration < self.min_green:
                logger.warning(f'SIM: {new_green_durations} 违反了最小绿灯时间 {self.min_green}')
                new_green_durations[phase_index] = self.min_green # 违反最小率, 就设置为最短时间
                self._touch_min_green = True
        
        # 如果没有设置 delta time, 就是一个周期调整一次
        if self.delta_time == None:
            self.set_duration(new_green_durations) # 设置动作
            self.next_action_time = self.sim_step + sum(new_green_durations) + self.green_loss # 计算下一次
            logger.debug('SIM: Time: {}; Adjust Phase: {}; Durations: {}; New Durations: {}; Cycle: {};'.format(
                                                        self.sim_step, 
                                                        adjust_phase,
                                                        green_durations, 
                                                        new_green_durations,
                                                        sum(new_green_durations)+self.green_loss
                )
            )
        # 设置了 delta time, 需要重新计算下一次的动作时间
        else:
            self.set_duration(new_green_durations)
            _cycle = sum(self.get_complete_durations()) # 计算总的信号灯时间长度
            _deltaTime = int(np.ceil(self.delta_time/_cycle) * _cycle) # 计算新的动作时间
            assert self.next_action_time == self.sim_step, f'确认时间是否同步.'
            self.next_action_time += _deltaTime
            logger.debug('SIM: Time: {}; Adjust Phase: {}; Durations: {}; New Durations: {}; Cycle: {}; Delta Time: {}; Next Action Time: {};'.format(
                                            self.sim_step, 
                                            adjust_phase,
                                            green_durations, 
                                            new_green_durations,
                                            sum(new_green_durations)+self.green_loss,
                                            _deltaTime,
                                            self.next_action_time,
                )
            )

    def set_duration(self, duration_list: List[float]):
        """设置下一个阶段的绿灯时长

        Args:
            duration_list (List[float]): 绿灯相位的时长, 例如为 [20, 10, 20, 10]
        """
        logics = self.sumo.trafficlight.getAllProgramLogics(self.id) # 获得当前信号灯的情况
        logic_index = [logic.programID for logic in logics].index(self.program_id)
        logic = logics[logic_index]

        # 确保 duration_list 的长度和绿灯相位数量相同
        all_green_phase = [phase for phase in logic.phases if ('G' in phase.state)] # 绿灯相位
        if len(all_green_phase) != len(duration_list):
            raise ValueError(f'duration set error, length not match: {len(all_green_phase)}, {len(duration_list)}')

        # 设置信号灯时长
        duration_index = 0 # 绿灯相位的索引
        for phase in logic.phases:
            if 'G' in phase.state: # 只修改绿灯的时长
                duration = duration_list[duration_index] # 选择绿灯相位时长
                phase.duration = duration
                phase.minDur = duration
                phase.maxDur = duration
                duration_index += 1
        self.sumo.trafficlight.setProgramLogic(self.id, logic)

        # 如果仿真时间为 0, 第一个动作, 则使用 setPhaseDuration 对第一个相位调整
        if self.sim_step == 0:
            self.sumo.trafficlight.setPhaseDuration(tlsID=self.id, phaseDuration=duration_list[0])
    
    def update(self) -> None:
        pass