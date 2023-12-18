'''
@Author: Liu Lu & WANG Maonan
@Date: 2023-10-27 20:19:13
@Description: Ego Vehicle Env Wrapper
@ + State: 1. 自身信息; 2. 每一个车道的信息 (包括 bottleneck 的信息)
    -> 自身信息: (1) 速度; (2) 距离 bottleneck 距离; (3) road id; (4) lane id
    -> 每一个车道的信息 (包括 bottleneck): (1) 平均速度; (2) 平均等待时间; (3) 平均 timeloss
@ + Action: 每个 ego vehicle 三个离散的动作: (加速, 减速, 维持不变)
@ + Reward: 对应 lane index 车辆离开时候的 travel time
@LastEditTime: 2023-12-18 23:21:25
'''
import time
import numpy as np
import gymnasium as gym

from loguru import logger
from gymnasium.core import Env
from collections import defaultdict
from typing import Any, SupportsFloat, Tuple, Dict, List
from stable_baselines3.common.monitor import ResultsWriter

from .wrapper_utils import (
    analyze_traffic,
    count_bottleneck_vehicles,
    calculate_congestion,
    calculate_speed,
    compute_ego_vehicle_features
)


class VehEnvWrapper(gym.Wrapper):
    """Vehicle Env Wrapper for vehicle info
    """
    def __init__(self, env: Env,
                 ego_ids:List[str], # ego vehicle id
                 edge_ids:List[str], # 路网中所有路段的 id
                 edge_lane_num:Dict[str, int], # 每个 edge 的车道数
                 calc_features_lane_ids:List[str], # 需要统计特征的 lane id
                 bottle_necks:List[str], # 路网中 bottleneck
                 bottle_neck_positions:Tuple[float], # bottle neck 的坐标
                 filepath:str, # 日志文件的路径
                 delta_t:int = 1, # 动作之间的间隔时间
                 warmup_steps:int=100, # reset 的时候仿真的步数, 确保 ego vehicle 可以全部出现
        ) -> None:
        super().__init__(env)
        self.edge_ids = edge_ids
        self.edge_lane_num = edge_lane_num
        self.ego_ids = ego_ids # 控制车辆的 id
        self.bottle_necks = bottle_necks
        self.calc_features_lane_ids = calc_features_lane_ids # 需要统计特征的 lane id
        self.bottle_neck_positions = bottle_neck_positions # bottle neck 的坐标
        self.warmup_steps = warmup_steps
        self.delta_t = delta_t
        self.vehicles_info = {} # 记录仿真内车辆的 (初始 lane index, travel time)
        self.action_speed = {
            0: 1, 1: 3, 2: 5,
            3: 7, 4: 9, 5: 11, 6: 13,
        } # 速度的选择
        self.agent_mask = {ego_id:True for ego_id in self.ego_ids} # 还需要控制的车辆
        
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

    # #####################
    # Obs and Action Space
    # #####################
    @property
    def action_space(self):
        """直接控制 ego vehicle 的速度
        """
        return {_ego_id:gym.spaces.Discrete(7) for _ego_id in self.ego_ids}

    @property
    def observation_space(self):
        obs_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(57,)
        )
        return {_ego_id:obs_space for _ego_id in self.ego_ids}

    # ##################
    # Tools for actions
    # ##################
    def __init_actions(self, raw_state, congestion_level):
        """初始化所有车辆的速度:
        1. 所有车辆的速度保持不变, (0, -1) --> 0 表示不换道, -1 表示速度不变
        2. 如果车辆处在 bottleneck 处, 则根据拥堵程度进行调整
        """
        self.actions = dict()
        for _veh_id, veh_info in raw_state['vehicle'].items():
            if veh_info['road_id'] in self.bottle_necks: # 如果在 bottle-neck 的车辆
                veh_speed = calculate_speed(
                    congestion_level=congestion_level,
                    speed=10
                )
                self.actions[_veh_id] = (0, veh_speed)
            else: # 其他的车辆
                self.actions[_veh_id] = (0, -1)

    def __update_actions(self, raw_action):
        """更新 ego 车辆的速度
        """
        for _veh_id in raw_action:
            if _veh_id in self.actions:
                new_speed = self.action_speed.get(raw_action[_veh_id], 1)
                self.actions[_veh_id] = (0, new_speed)
        return self.actions
    
    # ##########################
    # State and Reward Wrappers
    # ##########################
    def state_wrapper(self, state):
        """对原始信息的 state 进行处理, 分别得到:
        - 车道的信息
        - ego vehicle 的属性
        """
        state = state['vehicle'].copy() # 只需要分析车辆的信息
        # 计算车辆和地图的数据
        lane_statistics, ego_statistics, reward_statistics = analyze_traffic(
            state=state, lane_ids=self.calc_features_lane_ids
        )

        # 计算 bottle neck 的拥堵程度
        bottleneck_veh_num = count_bottleneck_vehicles(
            lane_statistics=lane_statistics, 
            bottle_necks=self.bottle_necks
        ) # 计算 bottle neck 处车辆的数量
        congestion_level = calculate_congestion(
            bottleneck_veh_num, length=300, num_lane=4
        ) # 计算 bottle neck 处的拥堵程度

        # 计算每个 ego vehicle 的 state 拼接为向量
        feature_vectors = compute_ego_vehicle_features(
            lane_statistics=lane_statistics,
            ego_statistics=ego_statistics,
            unique_edges=self.edge_ids,
            edge_lane_num=self.edge_lane_num,
            bottle_neck_positions=self.bottle_neck_positions,
        )
        return feature_vectors, congestion_level, ego_statistics, reward_statistics

    def reward_wrapper(self, ego_statistics, reward_statistics, last_step:bool=False) -> float:
        """自定义 reward 的计算, 如果是最后一个时刻, 则计算整个路网的 travel time
        """
        rewards = {}
        lane_index_travel_time = defaultdict(list)

        # Update vehicles still in the environment
        for veh_id, veh_lane_index in reward_statistics.items():
            self.vehicles_info[veh_id] = [
                self.vehicles_info.get(veh_id, [0, None])[0] + 1, 
                veh_lane_index
            ]

        # Gather information for vehicles that left the environment
        for veh_id, (veh_travel_time, veh_lane_index) in list(self.vehicles_info.items()):
            if veh_id not in reward_statistics:
                lane_index_travel_time[veh_lane_index].append(veh_travel_time)
                del self.vehicles_info[veh_id]  # Remove vehicle from tracking

        # Calculate reward for ego vehicles
        if not last_step:
            for ego_id, ego_info in ego_statistics.items():
                ego_lane_index = ego_info[-1]
                travel_times = lane_index_travel_time.get(ego_lane_index, [])
                mean_travel_time = np.mean(travel_times) if travel_times else 0
                rewards[ego_id] = 0 if mean_travel_time==0 else 50 - mean_travel_time # 200 is the baseline mean travel time
        else: # 最后一个时刻, 我们计算路网里面完整的 travel time
            travel_times = np.array([veh_info[0] for veh_info in self.vehicles_info.values()])
            mean_travel_time = np.mean(travel_times)
            ego_id = list(ego_statistics.keys())[0] # 找到最后的车辆的 id
            rewards[ego_id] = 0 if mean_travel_time==0 else 50 - mean_travel_time # 200 is the baseline mean travel time

        return rewards
    
    # ############
    # reset & step
    # #############
    def reset(self, seed=1) -> Tuple[Any, Dict[str, Any]]:
        """reset 时初始化
        """
        init_state = self.env.reset() # 初始化环境
        _, congestion_level, _, _ = self.state_wrapper(state=init_state)
        self.__init_actions(raw_state=init_state, congestion_level=congestion_level)

        for _ in range(self.warmup_steps):
            init_state, _, _, _, _ = super().step(self.actions)
            feature_vectors, congestion_level, _, _ = self.state_wrapper(state=init_state)
            self.__init_actions(raw_state=init_state, congestion_level=congestion_level)

        return feature_vectors, {'step_time': 0}

    def step(self, action: Dict[str, int]) -> Tuple[Any, SupportsFloat, bool, bool, Dict[str, Any]]:
        """这里我们假设 agent 数量不会动态的改变, 如果 ego vehicle 离开了 bottleneck, state 就全部是 0
        """
        for ego_id, ego_live in self.agent_mask.items():
            if not ego_live:
                del action[ego_id] # 离开 bottleneck 的车辆不控制
        action = self.__update_actions(raw_action=action).copy()
        init_state, rewards, truncated, _dones, infos = super().step(action)
        feature_vectors, congestion_level, ego_statistics, reward_statistics = self.state_wrapper(state=init_state)
        self.__init_actions(raw_state=init_state, congestion_level=congestion_level)

        # 处理 dones 和 infos
        dones = {}
        if feature_vectors: # feature_vectors 不是空的
            rewards = self.reward_wrapper(ego_statistics, reward_statistics)
            done = False
        else:
            rewards = self.reward_wrapper(ego_statistics, reward_statistics, last_step=True)
            done = True # 所有车离开的时候, 就结束

        for _ego_id in self.ego_ids:
            dones[_ego_id] = done
            infos[_ego_id] = {'termination': done}
            if _ego_id not in feature_vectors:
                feature_vectors[_ego_id] = [0.0]*57 # 如果 ego vehicle 离开环境, 则 state 全部是 0
                self.agent_mask[_ego_id] = False
            if _ego_id not in rewards:
                rewards[_ego_id] = 0
                
        # Writer
        self.rewards_writer.append(float(sum(rewards.values())))
        if all(dones.values()): # 所有结束才算结束
            ep_rew = sum(self.rewards_writer)
            ep_len = len(self.rewards_writer)
            ep_info = {"r": round(ep_rew, 6), "l": ep_len, "t": round(time.time() - self.t_start, 6)}
            self.results_writer.write_row(ep_info)
            self.rewards_writer = list()

        return feature_vectors, rewards, dones.copy(), dones.copy(), infos

    def close(self) -> None:
        self.results_writer.close()
        return super().close()