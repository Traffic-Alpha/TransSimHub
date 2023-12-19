'''
@Author: Liu Lu & WANG Maonan
@Date: 2023-10-27 20:19:13
@Description: Ego Vehicle Env Wrapper
@ + State: 1. 自身信息; 2. 每一个车道的信息 (包括 bottleneck 的信息)
    -> 自身信息: (1) 速度; (2) 距离 bottleneck 距离; (3) road id; (4) lane id
    -> 每一个车道的信息 (包括 bottleneck): (1) 平均速度; (2) 平均等待时间; (3) 平均 timeloss
@ + Action: 每个 ego vehicle 三个离散的动作: (加速, 减速, 维持不变)
@ + Reward: 全局平均速度(距离/时间) + ego 自己的速度
@LastEditTime: 2023-12-19 22:52:42
'''
import time
import numpy as np
import gymnasium as gym

from loguru import logger
from gymnasium.core import Env
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
        self.action_speed = {
            0: 1, 1: 3, 2: 5,
            3: 6, 4: 7, 5: 8, 
            6: 9,
        } # 速度的选择

        self.congestion_level = 0 # 初始是不堵车的
        self.vehicles_info = {} # 记录仿真内车辆的 (初始 lane index, travel time)
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
        for _veh_id in raw_action:
            if _veh_id in self.actions:
                speed = self.action_speed.get(raw_action[_veh_id], 1)
                edge_id = self.vehicles_info.get(_veh_id, [0, None])[0]
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
            state=state, lane_ids=self.calc_features_lane_ids
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
            lane_statistics=lane_statistics,
            ego_statistics=ego_statistics,
            unique_edges=self.edge_ids,
            edge_lane_num=self.edge_lane_num,
            bottle_neck_positions=self.bottle_neck_positions,
        )
        return feature_vectors, ego_statistics, reward_statistics

    def reward_wrapper(self, ego_statistics, reward_statistics) -> float:
        """Calculate the custom reward, considering both global and local components.
        """
        rewards = {}
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
            if edge_id in self.bottle_necks:
                vehicle_speed.append(0*distance/veh_travel_time + 1*speed) # 平均速度
            if veh_id not in reward_statistics: # Vehicle has left the environment
                del self.vehicles_info[veh_id] # Remove vehicle from tracking

        # Global Reward Component
        global_speed = np.mean(vehicle_speed) if vehicle_speed else 0
        global_reward = -abs(global_speed - optimal_speed)/optimal_speed

        # Calculate reward for ego vehicles
        for ego_id, ego_info in ego_statistics.items():
            ego_speed = ego_info[0]
            # Local Reward Component: Encourage maintaining optimal speed
            speed_diff = abs(ego_speed - optimal_speed)
            local_reward = -speed_diff / optimal_speed  # Penalize deviation from optimal speed

            # Combine Global and Local Rewards
            rewards[ego_id] = 1*global_reward + 0*local_reward + 0*time_penalty

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
        self.agent_mask = {ego_id:True for ego_id in self.ego_ids} # 还需要控制的车辆

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
        for ego_id, ego_live in self.agent_mask.items():
            if not ego_live:
                del action[ego_id] # 离开 bottleneck 的车辆不控制
        action = self.__update_actions(raw_action=action).copy()
        init_state, rewards, truncated, _dones, infos = super().step(action)
        feature_vectors, ego_statistics, reward_statistics = self.state_wrapper(state=init_state)
        self.__init_actions(raw_state=init_state)

        # 处理 dones 和 infos
        dones = {}
        if feature_vectors: # feature_vectors 不是空的
            done = False
            rewards = self.reward_wrapper(ego_statistics, reward_statistics)
        else: # 所有车离开的时候, 就结束
            done = True
            rewards = {}
            while self.vehicles_info: # 仿真到没有车在 self.edge_ids
                init_state, _, _, _, _ = super().step(self.actions)
                feature_vectors, _, reward_statistics = self.state_wrapper(state=init_state)
                reward = self.reward_wrapper(ego_statistics, reward_statistics) # 更新 veh info
                self.__init_actions(raw_state=init_state)
                if not rewards:
                    rewards = reward.copy()
                else:
                    ego_id = list(ego_statistics.keys())[0]
                    rewards[ego_id] += reward[ego_id]

        # 计算 done 和 info
        for _ego_id in self.ego_ids:
            dones[_ego_id] = done
            infos[_ego_id] = {'termination': done}
            if _ego_id not in feature_vectors:
                feature_vectors[_ego_id] = [0.0]*57 # 如果 ego vehicle 离开环境, 则 state 全部是 0
                self.agent_mask[_ego_id] = False # agent 离开了路网, mask 设置为 False
            if _ego_id not in rewards:
                rewards[_ego_id] = -0.5 # 离开路网之后 reward 也是 0
                
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