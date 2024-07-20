'''
@Author: Liu Lu & WANG Maonan
@Date: 2023-10-27 20:19:13
@Description: Ego Vehicle Env Wrapper, 一个 Agent 控制所有的 ego vehicles
@ + State: 1. 自身信息; 2. 每一个车道的信息 (包括 bottleneck 的信息)
    -> 自身信息: (1) 速度; (2) 距离 bottleneck 距离; (3) road id; (4) lane id
    -> 每一个车道的信息 (包括 bottleneck): (1) 平均速度; (2) 平均等待时间; (3) 平均 timeloss
@ + Action: 每个 ego vehicle 三个离散的动作: (加速, 减速, 维持不变)
@ + Reward: 全局平均速度(距离/时间) + ego 自己的速度
@LastEditTime: 2023-12-21 23:24:45
'''
import time
import numpy as np
import gymnasium as gym

from loguru import logger
from gymnasium.core import Env
from typing import Any, SupportsFloat, Tuple, Dict, List

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
                 out_edge_ids:List[str], # 离开路段的 id
                 calc_features_lane_ids:List[str], # 需要统计特征的 lane id
                 bottle_necks:List[str], # 路网中 bottleneck
                 bottle_neck_positions:Tuple[float], # bottle neck 的坐标
                 delta_t:int = 1, # 动作之间的间隔时间
                 warmup_steps:int=100, # reset 的时候仿真的步数, 确保 ego vehicle 可以全部出现
        ) -> None:
        super().__init__(env)
        self.ego_ids = ego_ids # 控制车辆的 id
        self.out_edge_ids = out_edge_ids
        self.bottle_necks = bottle_necks
        self.calc_features_lane_ids = calc_features_lane_ids # 需要统计特征的 lane id
        self.bottle_neck_positions = bottle_neck_positions # bottle neck 的坐标
        self.warmup_steps = warmup_steps
        self.delta_t = delta_t
        self.action_speed = {
            0: 1, 1: 9,
        } # 速度的选择

        self.congestion_level = 0 # 初始是不堵车的
        self.vehicles_info = {} # 记录仿真内车辆的 (初始 lane index, travel time)


    # #####################
    # Obs and Action Space
    # #####################
    @property
    def action_space(self):
        """直接控制 ego vehicle 的速度
        """
        return gym.spaces.MultiDiscrete([2 for _ in self.ego_ids])

    @property
    def observation_space(self):
        obs_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(18,) # 12*N + 6
        )
        return obs_space

    # ##################
    # Tools for actions
    # ##################
    def __init_actions(self, raw_state):
        """初始化所有车辆的速度:
        1. 所有车辆的速度保持不变, (0, -1) --> 0 表示不换道, -1 表示速度不变
        2. 如果车辆处在 bottleneck 处, 则根据拥堵程度进行调整
        """
        self.actions = dict()
        for _veh_id, veh_info in raw_state['vehicle'].items():
            if veh_info['road_id'] in self.bottle_necks: # 如果在 bottle-neck 的车辆
                veh_speed = calculate_speed(
                    congestion_level=self.congestion_level,
                    speed=6
                )
                self.actions[_veh_id] = (0, veh_speed)
            else: # 其他的车辆
                self.actions[_veh_id] = (0, -1)

    def __update_actions(self, raw_action):
        """更新 ego 车辆的速度
        """
        for _veh_id, _action in zip(self.ego_ids, raw_action):
            if _veh_id in self.actions:
                speed = self.action_speed.get(_action, 1) # 获得对应的速度
                edge_id = self.vehicles_info.get(_veh_id, [0, None])[1] # 判断是否在 bottleneck 上
                vspeed = self.vehicles_info.get(_veh_id, [0, 0])[-1]
                if vspeed > 10:
                    print(1)
                if edge_id in self.bottle_necks:
                    new_speed = calculate_speed(
                        congestion_level=self.congestion_level,
                        speed=speed
                    )
                else:
                    new_speed = speed
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
            state=state, 
            lane_ids=self.calc_features_lane_ids,
            out_edge_ids=self.out_edge_ids
        )

        # 计算 bottle neck 的拥堵程度
        bottleneck_veh_num = count_bottleneck_vehicles(
            lane_statistics=lane_statistics, 
            bottle_necks=self.bottle_necks
        ) # 计算 bottle neck 处车辆的数量
        self.congestion_level = calculate_congestion(
            bottleneck_veh_num, length=300, num_lane=4
        ) # 计算 bottle neck 处的拥堵程度

        # 计算每个 ego vehicle 的 state 拼接为向量
        feature_vectors = compute_ego_vehicle_features(
            ego_ids=self.ego_ids,
            lane_statistics=lane_statistics,
            ego_statistics=ego_statistics,
            bottle_neck_positions=self.bottle_neck_positions,
        )
        return feature_vectors, ego_statistics, reward_statistics

    def reward_wrapper(self, reward_statistics) -> float:
        """Calculate the custom reward, considering both global and local components.
        """
        rewards = 0
        vehicle_speed = list()
        optimal_speed = 15  # ego vehicle 的最快的速度
        time_penalty = -0.5 

        # Update vehicles still in the environment
        for veh_id, (edge_id, distance, speed) in reward_statistics.items():
            self.vehicles_info[veh_id] = [
                self.vehicles_info.get(veh_id, [0, None])[0] + 1, # travel time
                edge_id,
                distance,
                speed
            ]

        # Calculate Vehicle Speed & Remove vehicles that left the environment
        for veh_id, (veh_travel_time, edge_id, distance, speed) in list(self.vehicles_info.items()):
            if edge_id in self.bottle_necks: # 希望 bottleneck 速度最快
                vehicle_speed.append(0*distance/veh_travel_time + 1*speed) # 平均速度
            if veh_id not in reward_statistics: # Vehicle has left the environment
                del self.vehicles_info[veh_id] # Remove vehicle from tracking

        # Global Reward Component
        global_speed = np.mean(vehicle_speed) if vehicle_speed else 0
        global_reward = -abs(global_speed - optimal_speed)/optimal_speed

        rewards = 1*global_reward + 0*time_penalty

        return rewards
    
    # ############
    # reset & step
    # #############
    def reset(self, seed=1) -> Tuple[Any, Dict[str, Any]]:
        """reset 时初始化
        """
        # 初始化超参数
        self.congestion_level = 0
        self.vehicles_info = {} # 记录仿真内车辆的 (初始 lane index, travel time)

        # 初始化环境
        init_state = self.env.reset() # 初始化环境
        self.__init_actions(raw_state=init_state)

        for _ in range(self.warmup_steps):
            init_state, _, _, _, _ = super().step(self.actions)
            feature_vectors, _, _ = self.state_wrapper(state=init_state)
            self.__init_actions(raw_state=init_state)

        return feature_vectors, {'step_time': 0}

    def step(self, action: Dict[str, int]) -> Tuple[Any, SupportsFloat, bool, bool, Dict[str, Any]]:
        """这里我们假设 agent 数量不会动态的改变, 如果 ego vehicle 离开了 bottleneck, state 就全部是 0
        """
        action = self.__update_actions(raw_action=action).copy()
        init_state, rewards, truncated, _dones, infos = super().step(action)
        feature_vectors, ego_statistics, reward_statistics = self.state_wrapper(state=init_state)
        self.__init_actions(raw_state=init_state)

        # 处理 dones 和 infos
        if ego_statistics: # 如果还存在 ego 车
            done = False
            rewards = self.reward_wrapper(reward_statistics)
        else: # 所有车离开 bottleneck, 就结束
            done = True
            rewards = 0
            while self.vehicles_info:
                init_state, _, _, _, _ = super().step(self.actions)
                feature_vectors, _, reward_statistics = self.state_wrapper(state=init_state)
                reward = self.reward_wrapper(reward_statistics) # 更新 veh info
                self.__init_actions(raw_state=init_state)
                rewards += reward
                

        return feature_vectors, rewards, done, done, infos

    def close(self) -> None:
        return super().close()