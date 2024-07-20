'''
@Author: WANG Maonan
@Date: 2023-10-30 14:22:45
@Description: 计算 tsc env 中的 state 和 reward
@LastEditTime: 2024-04-24 22:06:50
'''
import time
import numpy as np
import gymnasium as gym
from itertools import chain
from loguru import logger
from gymnasium.core import Env
from collections import deque
from typing import Any, SupportsFloat, Tuple, Dict, List
from stable_baselines3.common.monitor import ResultsWriter

class VehicleIDList:
    def __init__(self) -> None:
        self.elements = []
    
    def add_element(self, element) -> None:
        """合并不同时刻的 vehicle_ids
        -> a = [[1,2], [3,4]]
        -> b = [[5,6], [7,8]]
        -> a+b = [[1, 2], [3, 4], [5, 6], [7, 8]]
        """
        self.elements += element
    
    def clear_elements(self) -> None:
        self.elements = []
    
    def flatten_remove_duplicates_elements(self):
        flattened_list = list(chain(*self.elements))  # 展开列表
        unique_list = list(set(flattened_list)) # 去除重复的元素
        self.clear_elements()
        return unique_list
        

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
        """计算一段时间的平均 occupancy
        """
        arr = np.array(self.elements)
        averages = np.mean(arr, axis=0, dtype=np.float32)/100
        self.clear_elements() # 清空列表
        return averages


class TSCEnvWrapper(gym.Wrapper):
    """TSC Env Wrapper for single junction with tls_id
    """
    def __init__(self, env: Env, max_states:int=5, filepath:str=None) -> None:
        super().__init__(env)
        self.tls_ids = self.env.tls_ids # 多路口的 ids
        self.states = {
            _tls_id: deque([self._get_initial_state()] * max_states, maxlen=max_states) 
            for _tls_id in self.tls_ids
        } # 队列, 记录每个 junction 的 state

        self.occupancy = {
            _tls_id:OccupancyList() 
            for _tls_id in self.tls_ids
        } # 计算每个路口的 occupancy
        self.veh_ids = {
            _tls_id: VehicleIDList()
            for _tls_id in self.tls_ids
        }
        # (movement_ids & phase2movements) are used for rule-based method
        self.movement_ids = dict()
        self.phase2movements = dict()

        # #######
        # Writer
        # #######
        logger.info(f'RL: Log Path, {filepath}')
        self.t_start = time.time()
        self.results_writer = ResultsWriter(
                filepath,
                header={"t_start": self.t_start},
        )
        self.rewards_writer = list()
        
    def _get_initial_state(self) -> List[int]:
        # 返回初始状态，这里假设所有状态都为 0
        return [0]*12
    
    def get_state(self):
        """将 state 从二维 (5, 12) 转换为一维 (1, 60)
        """
        new_state = dict()
        for _tls_id in self.tls_ids:
            new_state[_tls_id] = np.array(
                self.states[_tls_id], 
                dtype=np.float32
            ).reshape(-1)
        return new_state
    
    # ENV Spaces
    @property
    def action_space(self):
        return {_tls_id:gym.spaces.Discrete(2) for _tls_id in self.tls_ids}
    
    @property
    def observation_space(self):
        obs_space = gym.spaces.Box(
            low=np.zeros(5*12),
            high=np.ones(5*12),
            shape=(5*12,)
        ) # self.states 是一个时间序列
        return {_tls_id:obs_space for _tls_id in self.tls_ids}
    
    # Wrapper
    def state_wrapper(self, state):
        """返回当前 tls 每个 movement 的 occupancy
        """
        occupancy = state['last_step_occupancy']
        can_perform_action = state['can_perform_action']
        vehicle_ids = state['last_step_vehicle_id_list']
        
        return occupancy, vehicle_ids, can_perform_action
    
    def reward_wrapper(self, vehicle_info, tls_vehicle_ids) -> float:
        """返回路口对应的车辆的等待时间, 有可能车辆离开路口, 此时等待时间是 0 (所有车辆的平均等待时间)
        """
        waiting_times = [min(vehicle_info.get(_veh_id, {}).get('waiting_time', 0), 80) for _veh_id in tls_vehicle_ids]

        return -np.mean(waiting_times) if waiting_times else 0
    
    def info_wrapper(self, infos, occupancy, can_perform_action, tls_id):
        """在 info 中加入每个 phase 的占有率
        """
        movement_occ = {key: value for key, value in zip(self.movement_ids[tls_id], occupancy)}
        phase_occ = {}
        for phase_index, phase_movements in self.phase2movements[tls_id].items():
            phase_occ[f'{phase_index}'] = sum([movement_occ[phase] for phase in phase_movements])
        
        infos[tls_id] = phase_occ
        infos[tls_id]['can_perform_action'] = can_perform_action
        return infos

    def reset(self, seed=1) -> Tuple[Any, Dict[str, Any]]:
        """reset 时初始化 (1) 静态信息; (2) 动态信息
        """
        state =  self.env.reset()
        # 初始化路口静态信息
        for _tls_id in self.tls_ids:
            self.movement_ids[_tls_id] = state['tls'][_tls_id]['movement_ids']
            self.phase2movements[_tls_id] = state['tls'][_tls_id]['phase2movements']

            # 处理路口动态信息
            occupancy, _, _ = self.state_wrapper(state=state['tls'][_tls_id])
            self.states[_tls_id].append(occupancy)

        state = self.get_state()
        return state, {'step_time':0}

    def step(self, action: Dict[str, int]) -> Tuple[Any, SupportsFloat, bool, bool, Dict[str, Any]]:
        can_perform_action = False
        can_perform_action_int = {} # 每个路口是否可以做动作
        while not can_perform_action:
            states, rewards, truncated, done, infos = super().step(action) # 与环境交互
            for _tls_id in self.tls_ids:
                occupancy, vehicle_ids, can_perform_action = self.state_wrapper(state=states['tls'][_tls_id]) # 处理每一帧的数据
                self.occupancy[_tls_id].add_element(occupancy)
                self.veh_ids[_tls_id].add_element(vehicle_ids)
                can_perform_action_int[_tls_id] =  can_perform_action
        
        # 当可以执行动作的时候, 开始处理时序的 state
        rewards = dict()
        truncateds = dict()
        dones = dict()
        for _tls_id in self.tls_ids:
            avg_occupancy = self.occupancy[_tls_id].calculate_average() # 计算 tls 的 state
            rewards[_tls_id] = self.reward_wrapper(
                vehicle_info=states['vehicle'],
                tls_vehicle_ids=self.veh_ids[_tls_id].flatten_remove_duplicates_elements()
            ) # 计算每个 tls 的 vehicle waiting time
            infos = self.info_wrapper(
                infos, occupancy=avg_occupancy, 
                can_perform_action=can_perform_action_int[_tls_id],
                tls_id=_tls_id
            ) # info 里面包含每个 phase 的排队
            self.states[_tls_id].append(avg_occupancy) # 这里 state 是一个时间序列
            truncateds[_tls_id] = truncated
            dones[_tls_id] = done
        state = self.get_state() # 得到 state
        
        # Writer
        self.rewards_writer.append(float(sum(rewards.values())))
        if all(dones.values()):
            ep_rew = sum(self.rewards_writer)
            ep_len = len(self.rewards_writer)
            ep_info = {"r": round(ep_rew, 6), "l": ep_len, "t": round(time.time() - self.t_start, 6)}
            self.results_writer.write_row(ep_info)
            self.rewards_writer = list()

        return state, rewards, truncateds, dones, infos
    
    def close(self) -> None:
        self.results_writer.close()
        return super().close()