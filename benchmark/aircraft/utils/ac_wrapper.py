'''
@Author: WANG Maonan
@Date: 2023-09-08 15:49:30
@Description: 处理 ACEnvironment
+ state wrapper: 获得每个 aircraft 在覆盖范围内车辆的信息, 只有 drone 与车辆进行通信
+ reward wrapper: aircraft 覆盖车辆个数
@LastEditTime: 2023-09-14 17:19:50
'''
import numpy as np
import gymnasium as gym
from gymnasium.core import Env
from typing import Any, SupportsFloat, Tuple, Dict

class ACEnvWrapper(gym.Wrapper):
    """Aircraft Env Wrapper for single junction with tls_id
    """
    def __init__(self, env: Env) -> None:
        super().__init__(env)
    
    @property
    def action_space(self):
        return gym.spaces.Discrete(8)
    
    @property
    def observation_space(self):
        obs_space = gym.spaces.Box(
            low=np.zeros((5,12)),
            high=np.ones((5,12)),
            shape=(5,12)
        )
        return obs_space
    
    # Wrapper
    def state_wrapper(self, state):
        """自定义 state 的处理, 只找出与 aircraft 通信范围内的 vehicle
        """
        new_state = dict()
        veh = state['vehicle']
        aircraft = state['aircraft']
        for aircraft_id, aircraft_info in aircraft.items():
            vehicle_state = {}
            ground_cover_radius = aircraft_info['ground_cover_radius']
            aircraft_type = aircraft_info['aircraft_type']
            
            if aircraft_type == 'drone': # 只统计 drone 类型
                for vehicle_id, vehicle_info in veh.items():
                    vehicle_position = vehicle_info['position']
                    distance = ((vehicle_position[0] - aircraft_info['position'][0]) ** 2 +
                                (vehicle_position[1] - aircraft_info['position'][1]) ** 2) ** 0.5
                    
                    if distance <= ground_cover_radius:
                        vehicle_state[vehicle_id] = vehicle_info
                
                new_state[aircraft_id] = vehicle_state
        return new_state
    
    def reward_wrapper(self, states) -> float:
        """自定义 reward 的计算
        """
        total_cover_vehicles = 0 # 覆盖车的数量
        for _, aircraft_info in states.items():
            total_cover_vehicles += len(aircraft_info)
        return total_cover_vehicles

    def reset(self, seed=1) -> Tuple[Any, Dict[str, Any]]:
        """reset 时初始化 (1) 静态信息; (2) 动态信息
        """
        state =  self.env.reset()
        state = self.state_wrapper(state=state)
        return state, {'step_time':0}
    

    def step(self, action: int) -> Tuple[Any, SupportsFloat, bool, bool, Dict[str, Any]]:
        states, rewards, truncated, dones, infos = super().step(action) # 与环境交互
        states = self.state_wrapper(state=states) # 处理 state
        rewards = self.reward_wrapper(states=states) # 处理 reward

        return states, rewards, truncated, dones, infos
    
    def close(self) -> None:
        return super().close()