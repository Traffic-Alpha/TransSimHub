'''
@Author: WANG Maonan
@Date: 2023-09-05 11:27:05
@Description: 处理 Traffic Signal Control Env 的 State
1. 处理路口的信息
    - 路口的静态信息, 道路拓扑信息 (这个是用于相似度的比较)
    - 道路的动态信息, 会随着时间进行变化（每个 phase 的排队长度和当前所在的 phase）
2. 实现一些查询的接口
    - （a）所有可能的动作, 这里就是 `change phase 0 green` or `change phase k green`, 切换到某个 phase 是绿灯
    - （b）作出动作后，成为的新的 phase
    - （c）作出某个动作后, phase 对应排队长度的变化的预测（这里预测可以直接使用 MCT 来进行预测，或者服从某个分布，这里需要做一个预测）
    - （d）比较前后两次 phase 之间的排队的增加
    - （e）分析路口的性能（就是根据 c 的结果做进一步的计算）
@LastEditTime: 2023-09-07 11:34:05
'''
import gymnasium as gym
from typing import Any, SupportsFloat, Tuple, Dict
from gymnasium.core import Env
from tshub.utils.nested_dict_conversion import create_nested_defaultdict, defaultdict2dict

from TSCEnvironment.wrapper_utils import calculate_queue_lengths, predict_queue_length, QueueMetrics

class TSCEnvWrapper(gym.Wrapper):
    def __init__(self, env: Env) -> None:
        super().__init__(env)
        self.state = None # 当前的 state
        self.queue_metrics = {} # 存储每个 tls 的排队长度
        for _tls_id in self.env.tsc_env.tls_ids:
            self.queue_metrics[_tls_id] = QueueMetrics()

    def state_wrapper(self, state):
        """返回当前的 phase id 和每一个 phase 的平均排队情况

        Args:
            state (_type_): _description_
        """
        tls_wrapper_state = {}
        for tls_id, tls_info in state['tls'].items():
            movement_ids = tls_info['movement_ids']
            jam_length_meters = tls_info['jam_length_meters']
            phase2movements = tls_info['phase2movements']

            phase_queue_lengths = calculate_queue_lengths(movement_ids, jam_length_meters, phase2movements)
            this_phase_index = tls_info['this_phase_index'] # 当前的 phase index
            can_perform_action = tls_info['can_perform_action']
            phase_num = len(phase2movements) # phase 的数量
            tls_wrapper_state[tls_id] = {
                'phase_queue_lengths': phase_queue_lengths,
                'this_phase_index': this_phase_index,
                'phase_num': phase_num,
                'can_perform_action': can_perform_action,
            }
        return tls_wrapper_state


    def reset(self) -> Tuple[Any, Dict[str, Any]]:
        state =  self.env.reset()
        self.state = self.state_wrapper(state=state)
        return self.state
    

    def step(self, action: Any) -> Tuple[Any, SupportsFloat, bool, bool, Dict[str, Any]]:
        can_perform_action = False
        while not can_perform_action:
            states, rewards, truncated, dones, infos = super().step(action) # 与环境交互
            single_state_wrapper = self.state_wrapper(state=states) # 处理每一帧的数据
            # 记录每一时刻的数据
            for _tls_id, _tls_info in single_state_wrapper.items():
                self.queue_metrics[_tls_id].add(_tls_info['phase_queue_lengths'])
            # 判断是否需要执行动作
            can_perform_action = any(
                [single_state_wrapper[_tls_id]['can_perform_action'] 
                 for _tls_id in single_state_wrapper.keys()]
                )
        
        # 处理好的时序的 state
        state_wrapper = create_nested_defaultdict()
        for _tls_id, _queue_metrics in self.queue_metrics.items():
            state_wrapper[_tls_id]['phase_queue_lengths'] = _queue_metrics.get()
            state_wrapper[_tls_id]['this_phase_index'] = single_state_wrapper[_tls_id]['this_phase_index']
            state_wrapper[_tls_id]['phase_num'] = single_state_wrapper[_tls_id]['phase_num']
        self.state = defaultdict2dict(state_wrapper)

        return self.state, rewards, truncated, dones, infos
    
    def close(self) -> None:
        return super().close()
    
    
    # Custom Tools for TSC Agent
    def get_available_actions(self, action_type='next_or_not'):
        """获得每个 tls 的可行动作空间
        """
        tls_available_actions = {}
        if action_type == 'next_or_not':
            for _tls_id, tls_info in self.state.items():
                current_phase_index = tls_info['this_phase_index'] # 当前相位的 id
                current_phase_num = tls_info['phase_num'] # 当前有多少相位
                next_phase_index = (current_phase_index+1)%current_phase_num # 下一个阶段的相位
                tls_available_actions[_tls_id] = [current_phase_index, next_phase_index]
        elif action_type == 'choose_next_phases':
            for _tls_id, tls_info in self.state:
                current_phase_num = tls_info['phase_num'] # 当前有多少相位
                tls_available_actions[_tls_id] = list(range(current_phase_num))
        else:
            raise ValueError(f'Action Type can only be next_or_not or choose_next_phases, now {action_type}')
        return tls_available_actions
    
    def predict_future_scene(self, phase_index):
        """预测将 phase index 设置为绿灯后, 路口排队长度的变化
        """
        try:
            phase_index = int(phase_index)
        except:
            raise ValueError(f"phase_index need to be a number, rather than {phase_index}.")
        predict_state = create_nested_defaultdict()
        for _tls_id, _tls_info in self.state.items():
            _tls_phase_queue_info = _tls_info['phase_queue_lengths']
            for _phase_index, (_phase_name, _queue_info) in enumerate(_tls_phase_queue_info.items()):
                if _phase_index == phase_index: # green light
                    _p_state = predict_queue_length(_queue_info, is_green=True)
                else: # red light
                    _p_state = predict_queue_length(_queue_info, is_green=False)
                predict_state[_tls_id][_phase_name] = _p_state
        return defaultdict2dict(predict_state)