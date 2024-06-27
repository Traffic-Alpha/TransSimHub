'''
@Author: WANG Maonan
@Date: 2024-06-27 17:49:38
@Description: 每次单独修改某一个 traffic phase 的持续时间
@LastEditTime: 2024-06-27 19:39:26
'''
import numpy as np
from typing import List
from loguru import logger
from .base_tls import BaseTLS

class set_phase_duration(BaseTLS):
    def __init__(self, ts_id, sumo, 
                 delta_time:int = None,
                 min_green:int=5, 
                 yellow_time:int=3,
                 init_green_duration:int=20,
        ) -> None:
        super().__init__(ts_id, sumo)
        
        self.delta_time = delta_time # 做动作的间隔
        self.min_green = min_green # 最小绿灯时间
        self.yellow_time = yellow_time # 黄灯时间, 用于初始化
        self.init_green_duration = init_green_duration # 初始绿灯时间

        self.green_loss = 0 # build phase 的时候初始化
        self._touch_min_green = False # 是否触碰到了最小绿灯

        self.phase_index = 0 # 记录当前的 phase id
        self.time_since_last_phase_change = 1 # 记录动作之间的间隔, 初始为 绿灯+黄灯
        self.num_green_phases = None # 绿灯相位的数量
        self.build_phases() # 初始化信号灯


    def build_phases(self):
        """主要完成下面三个步骤:
        1. 将所有的绿灯 phase 时间设置为 init_green_duration
        2. 将所有的黄灯 phase 时间设置为 yellow_time
        3. 去掉全红相位
        这里 build phase 和 choose next phase 是不同的, 因为需要保留原始的相位

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
        self.next_action_time = 0.0 # 下一步开始的时间
        self.green_loss = sum(self.get_complete_durations()) - sum(self.get_green_durations()) # 更新一下时间, 黄灯的时间
        self.num_green_phases = len(self.get_green_durations()) # 绿灯相位的数量

    def set_next_phases(self, new_phase_duration:int):
        """调整当前信号灯相位的持续时间
        例如, 当 traffic light 从 phase_i -> phase_j 的时候, 刚到 phase_j 时, 调整 phase_j 的持续时间
        """
        # 1. 判断是否违反最小绿灯的限制
        self._touch_min_green = False
        if new_phase_duration < self.min_green:
            logger.warning(f'SIM: {new_phase_duration} 违反了最小绿灯时间 {self.min_green}.')
            new_phase_duration = self.min_green # 违反最小率, 就设置为最短时间
            self._touch_min_green = True

        # 2. 修改当前相位的绿灯
        green_phase_durations = self.get_green_durations() # 获得绿灯相位的持续时间
        current_phase_duration = green_phase_durations[self.phase_index] # 当前相位时长
        green_phase_durations[self.phase_index] = current_phase_duration # 更新相位时间
        self.set_duration(green_phase_durations) # 将整个 tls program 进行修改, 确保后面可以按照修改之后的信号灯继续进行
        self.sumo.trafficlight.setPhaseDuration(
            tlsID=self.id,
            phaseDuration=new_phase_duration
        ) # 修改绿灯时长, 修改剩下的时间, 需要减去一秒; 且 setPhaseDuration 只会改变一次 (就是后面还是按照初始信号灯时间)
        logger.debug('SIM: Time: {}; Phase ID: [{}/{}]; Time Since Last Change: {}; Durations: {}; New Durations: {};'.format(
                                                    self.sim_step, # Time
                                                    self.phase_index, # phase id
                                                    self.sumo.trafficlight.getPhase(self.id), # 对于信号灯的 phase id, 算上黄灯
                                                    current_phase_duration, # 原始相位时长
                                                    new_phase_duration, # 新相位时长
                                                    self.time_since_last_phase_change
                    )
        )
        self.time_since_last_phase_change = 0 # 记录距离上次动作的时间
        
        # 3. 更新下一次动作时间和所在 phase id
        if self.delta_time == None:
            # 如果没有设置 delta time, 则会每个相位结束之后做动作
            self.phase_index = (self.phase_index + 1)%self.num_green_phases # 当前所在的 phase id, 这里是往后一个相位, 相当于是 next phase index
            self.next_action_time += (float(new_phase_duration) + self.yellow_time + 1) # 修改下一次动作执行时间, 需要把黄灯时间算进去
        else:
            # 设置了 delta time, 则需要计算 next_phase_index 和 next_action_time
            _cycle = sum(self.get_complete_durations()) # 计算总的信号灯时间长度
            _deltaTime = np.floor(self.delta_time/_cycle) * _cycle # 计算新的动作时间
            for _ in range(self.num_green_phases):
                _phase_duration = green_phase_durations[self.phase_index] # 当前相位的持续时间
                self.phase_index = (self.phase_index + 1)%self.num_green_phases # ! 这里不是每次从第一个相位开始的, 这里是记录下一个相位的索引
                if _deltaTime + (_phase_duration+self.yellow_time) < self.delta_time:
                    _deltaTime += _phase_duration+self.yellow_time
                else:
                    _deltaTime += _phase_duration+self.yellow_time
                    self.next_action_time += (float(_deltaTime) + 1)
                    break


    def set_duration(self, duration_list: List[float]) -> None:
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
        """每进行一步仿真, 更新当前时间
        """
        self.time_since_last_phase_change += 1