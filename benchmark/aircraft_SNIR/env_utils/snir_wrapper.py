'''
@Author: WANG Maonan
@Date: 2024-05-29 16:44:51
@Description: 处理环境的信息, 或是重新定义 agent design, 
TODO, 可视化, 可视化当前位置, 目标的位置, SNIR 的数值
@LastEditTime: 2024-05-29 18:40:36
'''
import gymnasium as gym
from gymnasium.core import Env
from typing import Any, SupportsFloat, Tuple, Dict

class SNIRWrapper(gym.Wrapper):
    """Aircraft Env Wrapper for single junction with tls_id
    """
    def __init__(self, env: Env) -> None:
        super().__init__(env)

        # reset 的时候会获得的静态信息
        self.x_min, self.y_min, self.resolution = None, None, None
        self.grid_z = None
        self.ac_history_pos = None # 记录 aircraft 的历史轨迹, 用于绘图, 需要在 reset 的时候哦初始化
        
        # 目标点
        self.goal_points = ((1300, 1600), (1000, 2700))
    
    # Wrapper
    def state_wrapper(self, state):
        """自定义 state 的处理, 计算 aircraft 所在位置的 SNIR
        """
        new_state = {}
        aircraft = state['aircraft']
        grid = state['grid']['100'] # !==> 这里是 grid 的信息
        for _aircraft_id, _aircraft_info in aircraft.items():
            _aircraft_pos = _aircraft_info['position'] # 获得 aircraft 的位置
            self.ac_history_pos[_aircraft_id].append(_aircraft_pos[:2])
            snir_value = grid.get_value_at_coordinate(*_aircraft_pos[:2])
            new_state[_aircraft_id] = snir_value
        return new_state
    
    def reward_wrapper(self) -> float:
        """自定义 reward 的计算
        """
        return -10

    def reset(self, seed=1) -> Tuple[Any, Dict[str, Any]]:
        """reset 时初始化 (1) 静态信息; (2) 动态信息
        """
        state =  self.env.reset()
        self.x_min = state['grid']['100'].x_min
        self.y_min = state['grid']['100'].y_min
        self.grid_z = state['grid']['100'].grid_z
        self.resolution = state['grid']['100'].resolution

        self.ac_history_pos = {
            ac_id: list()
            for ac_id in self.env.tsc_env.aircraft_inits.keys()
        } # 初始化 aircraft 的历史轨迹, 用于绘图
        state = self.state_wrapper(state=state)
        return state, {'step_time':0}

    def step(self, action: int) -> Tuple[Any, SupportsFloat, bool, bool, Dict[str, Any]]:
        states, rewards, truncated, dones, infos = super().step(action) # 与环境交互
        states = self.state_wrapper(state=states) # 处理 state
        rewards = self.reward_wrapper() # 处理 reward, 这里输出一个常数

        return states, rewards, truncated, dones, infos
    
    def close(self) -> None:
        return super().close()