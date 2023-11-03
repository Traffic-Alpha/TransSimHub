'''
@Author: WANG Maonan
@Date: 2023-10-27 20:19:13
@Description: 处理 vehicle 的特征
@LastEditTime: 2023-11-03 18:08:33
'''
import numpy as np
import gymnasium as gym
from gymnasium.core import Env
from typing import Any, SupportsFloat, Tuple, Dict

class VehEnvWrapper(gym.Wrapper):
    """Vehicle Env Wrapper for vehicle info
    """
    def __init__(self, env: Env) -> None:
        super().__init__(env)
        self.actions = dict()
        self.ego_ids = [] # ego 车辆 id
    
    @property
    def action_space(self):
        pass
    
    @property
    def observation_space(self):
        pass
    
    # Tools for actions
    def __get_actions(self, raw_action):
        """更新 ego 车辆的速度
        """
        for _veh_id in raw_action:
            if _veh_id in self.actions:
                self.actions[_veh_id] = raw_action[_veh_id]
        return self.actions
    
    def __update_actions(self, raw_state):
        """给所有车辆生成默认的 action, {id:(0, -1), ...}
        + 0 表示不换道
        + -1 表示速度不变
        """
        self.actions = dict()
        for _veh_id, _ in raw_state['vehicle'].items():
            self.actions[_veh_id] = (0, -1)

    # Wrapper
    def state_wrapper(self, state):
        """自定义 state 的处理, 只找出在 (self.center_x, self.center_y) 的 500m 范围内的车辆
        """
        ego_pos = dict() # 存储所有 ego 的 position
        new_state = dict()
        for veh_id, veh_info in state['vehicle'].items():
            if veh_info['vehicle_type'] == 'ego':
                _pos = veh_info['position']
                ego_pos[veh_id] = _pos
                new_state[veh_id] = dict()
        
        for _ego_id, (_ego_pos_x, _ego_pos_y) in ego_pos.items():
            for veh_id, veh_info in state['vehicle'].items():
                _pos_x, _pos_y = veh_info['position']
                distance = np.sqrt((_pos_x - _ego_pos_x)**2 + (_pos_y - _ego_pos_y)**2)
                if (distance < 50) and (veh_id != _ego_id):
                    new_state[_ego_id][veh_id] = veh_info
        return new_state
    
    def reward_wrapper(self, states) -> float:
        """自定义 reward 的计算
        """
        return 0

    def reset(self, seed=1) -> Tuple[Any, Dict[str, Any]]:
        """reset 时初始化
        """
        state =  self.env.reset()
        self.__update_actions(raw_state=state) # 生成默认的动作
        states = self.state_wrapper(state=state).copy()
        return states, {'step_time':0}
    
    def step(self, action: Dict[str, int]) -> Tuple[Any, SupportsFloat, bool, bool, Dict[str, Any]]:
        """1. get action; 2. update action
        """
        action = self.__get_actions(raw_action=action).copy() # 1. get action
        states, rewards, truncated, dones, infos = super().step(action) # 与环境交互
        self.__update_actions(raw_state=states) # 2. update action
        states = self.state_wrapper(state=states).copy() # 处理 state
        rewards = self.reward_wrapper(states=states) # 处理 reward

        return states, rewards, truncated, dones, infos
    
    def close(self) -> None:
        return super().close()