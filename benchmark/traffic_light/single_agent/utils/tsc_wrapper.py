'''
@Author: WANG Maonan
@Date: 2023-09-08 15:49:30
@Description: 处理 TSCHub ENV 中的 state, reward
@LastEditTime: 2023-09-08 20:08:34
'''
import numpy as np
import gymnasium as gym
from gymnasium.core import Env
from typing import Any, SupportsFloat, Tuple, Dict

class OccupancyList:
    def __init__(self) -> None:
        self.elements = []

    def add_element(self, element) -> None:
        if isinstance(element, list):
            if all(isinstance(e, float) for e in element):
                self.elements.append(element)
            else:
                raise ValueError("列表中的元素必须是浮点数类型")
        else:
            raise TypeError("添加的元素必须是列表类型")

    def clear_elements(self) -> None:
        self.elements = []

    def calculate_average(self) -> float:
        arr = np.array(self.elements)
        averages = np.mean(arr, axis=0, dtype=np.float32)/100
        self.clear_elements() # 清空列表
        return averages


class TSCEnvWrapper(gym.Wrapper):
    """TSC Env Wrapper for single junction with tls_id
    """
    def __init__(self, env: Env, tls_id:str) -> None:
        super().__init__(env)
        self.tls_id = tls_id # 单路口的 id
        self.state = None # 当前的 state
        self.movement_ids = None
        self.phase2movements = None
        self.occupancy = OccupancyList()

    @property
    def action_space(self):
        return gym.spaces.Discrete(4)
    
    @property
    def observation_space(self):
        obs_space = gym.spaces.Box(
            low=np.zeros(12),
            high=np.ones(12),
            shape=(12,)
        )
        return obs_space
    
    def state_wrapper(self, state):
        """返回当前每个 movement 的 occupancy
        """
        occupancy = state['tls'][self.tls_id]['last_step_occupancy']
        can_perform_action = state['tls'][self.tls_id]['can_perform_action']
        return occupancy, can_perform_action
    
    def reward_wrapper(self) -> float:
        """返回整个路口的排队长度的平均值
        """
        return -sum(self.state)/len(self.state)
    
    def info_wrapper(self, infos):
        movement_occ = {key: value for key, value in zip(self.movement_ids, self.state)}
        phase_occ = {}
        for phase_index, phase_movements in self.phase2movements.items():
            phase_occ[phase_index] = sum([movement_occ['_'.join(phase.split('--'))] for phase in phase_movements])
        
        infos['phase_occ'] = phase_occ
        return infos


    def reset(self, seed=1) -> Tuple[Any, Dict[str, Any]]:
        state =  self.env.reset()
        # 初始化路口静态信息
        self.movement_ids = state['tls'][self.tls_id]['movement_ids']
        self.phase2movements = state['tls'][self.tls_id]['phase2movements']
        # 处理路口动态信息
        occupancy, _ = self.state_wrapper(state=state)
        self.state = np.array(occupancy, dtype=np.float32)
        return self.state, {'step_time':0}
    

    def step(self, action: int) -> Tuple[Any, SupportsFloat, bool, bool, Dict[str, Any]]:
        can_perform_action = False
        while not can_perform_action:
            action = {self.tls_id: action} # 构建单路口 action 的动作
            states, rewards, truncated, dones, infos = super().step(action) # 与环境交互
            occupancy, can_perform_action = self.state_wrapper(state=states) # 处理每一帧的数据
            # 记录每一时刻的数据
            self.occupancy.add_element(occupancy)
        
        # 处理好的时序的 state
        self.state = self.occupancy.calculate_average()
        rewards = self.reward_wrapper()
        infos = self.info_wrapper(infos) # info 里面包含每个 phase 的排队

        return self.state, rewards, truncated, dones, infos
    
    def close(self) -> None:
        return super().close()