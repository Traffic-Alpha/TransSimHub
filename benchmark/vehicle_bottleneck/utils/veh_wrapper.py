'''
@Author: Liu Lu & WANG Maonan
@Date: 2023-10-27 20:19:13
@Description: Ego Vehicle Env Wrapper
@ + State: 1. 自身信息; 2. 每一个车道的信息 (包括 bottleneck 的信息)
    -> 自身信息: (1) 速度; (2) 距离 bottleneck 距离; (3) road id; (4) lane id
    -> 每一个车道的信息 (包括 bottleneck): (1) 平均速度; (2) 平均等待时间; (3) 平均 timeloss
@ + Action: 每个 ego vehicle 三个离散的动作: (加速, 减速, 维持不变)
@ + Reward: 离开环境的车辆的行驶时间

TODO
1. 修改 reward 的计算方式, 计算得到离开环境车辆的 travel time
2. 修改 reset, 可以传入参数 N, 表示仿真 N 步骤来预热
3. 写 result writer, 可以将环境的 reward 保存到文件中去
- state wrapper 里面如果车辆达到了 E4 就不再控制了, 需要返回一个 action mask
@LastEditTime: 2023-12-18 01:15:59
'''
import numpy as np
import pandas as pd
import gymnasium as gym

from gymnasium.core import Env
from typing import Any, SupportsFloat, Tuple, Dict, List
from collections import defaultdict

from .wrapper_utils import (
    analyze_traffic,
    count_bottleneck_vehicles,
    calculate_congestion,
    calculate_speed,
    compute_ego_vehicle_features
)

ROAD_IDS = ['E0', 'E1', 'E2','E3']  # 路网中所有路段的id
CONTROL = ['E1', 'E2']  # 路网中受控路段
BOTTLENECK = 'E2'  # 路网中bottleneck路段
MAX_SPEED = 15
OUT_DISTANCE = 1400 # 出口距离
BOTTLENECK_LANEID= [f"E2_{j}" for j in range(4)]
K = np.array([[-7.735, 0.2295, -5.16e-3, 9.773e-5],
              [0.02799, 0.0068, -7.722e-4, 8.38e-6],
              [-2.228e-4, -4.402e-5, 7.90e-7, 8.17e-7],
              [1.09e-6, 4.80e-8, 3.27e-8, -7.79e-9]]) # 计算油耗的矩阵

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
                 speed_change_range:float = 3 # 速度改变的范围
        ) -> None:
        super().__init__(env)
        self.edge_ids = edge_ids
        self.edge_lane_num = edge_lane_num
        self.ego_ids = ego_ids # 控制车辆的 id
        self.speed_change_range = speed_change_range
        self.bottle_necks = bottle_necks
        self.calc_features_lane_ids = calc_features_lane_ids # 需要统计特征的 lane id
        self.bottle_neck_positions = bottle_neck_positions # bottle neck 的坐标

        self.max_state_vector_length = 42 # 状态向量最大长度
        self.actions = dict()  # 动作
        self.ego_ids = list()  # ego 车辆 id
        self.vehicle_alltime = dict()  # 车辆总行驶时间
        self.vehicle_slowtime = dict()  # ego车辆的slowtime
        self.current_time = 0  # 当前时间步
        self.outflow_rate = 0  # 过去十秒流出量
        self.outflow_rates = []  # 存储每个时间步的流出量
        self.entrance_lanes = dict()  # 存储每个车辆在入口处的车道
        self.previous_out_vehicle_ids = set()  # 上一时间步流出的车辆ID
        self.exited_vehicles = dict()  # 离开的车辆及其离开的时间
        self.vehicle_speeds = dict()  # 车辆的速度
        self.vehicle_roadid = dict()  # 车辆的路段id
        self.ego_waiting = dict()  # 车辆的waiting_time
        self.bottleneck_avg_speeds = list()  # 每个仿真步骤的bottleneck路段平均速度
        self.avg_speeds = list()  # 每个仿真步骤车辆平均速度
        self.lane_ids = [f"E{i}_{j}" for i in range(3) for j in range(4)]  # 每个路段每个车道的id
        self.bottleneck_lane_ids = [f"E2_{j}" for j in range(4)]  # bottleneck路段每个车道的id
        self.bottleneck_congestion = dict()  # bottleneck的拥堵情况
        self.previous_speeds = dict()  # 存储上一状态的速度
        self.fuel_consumption = 0  # 总油耗
        self.fuel_consumptions = dict()  # 存储每个车辆的油耗
        self.veh_out_distance = dict()  # 存储所有 ego 车辆距离 出口E3 起始处的距离
        self.bottleneck_vehicle_counts = []  # 存储每个时间步的bottleneck路段车流量
        self.reward_given = {}  # 标记大的奖励是否给出
        self.vehicle_counts = 0  # 当前时间步车辆数量
        self.ego_laneid = dict()  # 存储ego车所在车道信息
        self.ego_roadid = dict()  # 存储ego车所在路段信息
        self.lane_counts = defaultdict(int)  # 每个车道上车辆数量信息

    # #####################
    # Obs and Action Space
    # #####################
    @property
    def action_space(self):
        """每个 ego vehicle 控制加减速, 共有三个选择:
        1. min(speed+speed_change_range, NAX_SPEED) -> 加速
        2. max(speed-speed_change_range, 0) -> 减速
        3. speed -> 维持速度不变
        """
        return {_ego_id:gym.spaces.Discrete(3) for _ego_id in self.ego_ids}

    @property
    def observation_space(self):
        obs_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.max_state_vector_length,)
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
                    speed=veh_info['speed']
                )
                self.actions[_veh_id] = (0, veh_speed)
            else: # 其他的车辆
                self.actions[_veh_id] = (0, -1)

    def __update_actions(self, raw_action):
        """更新 ego 车辆的速度
        """
        for _veh_id in raw_action:
            if _veh_id in self.actions:
                self.actions[_veh_id] = raw_action[_veh_id]
        return self.actions

    def __get_ego_ids(self, state):
        """从观测状态中获取 ego_id, 这里需要注意 ego vehicle 是否离开了环境
        获得仍然存活的 agent
        """
        self.ego_ids = [1,2,3]
        return self.ego_ids
    
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
        lane_statistics, ego_statistics = analyze_traffic(
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
        return feature_vectors, congestion_level

    def reward_wrapper(self, states, ego_info) -> float:
        """自定义 reward 的计算, 离开路网的车辆的 travel time
        """
        rewards = {}
        for ego_id in self.ego_ids:
            if ego_id not in states:
                continue
            if states[ego_id][0] <= 0.13:
                rewards[ego_id] = -20
            else:
                rewards[ego_id] = 0.3 * ego_info['all_vehicle_avg_speed'] - 0.7 * self.fuel_consumptions[ego_id]
            if self.current_time <= 150:
                rewards[ego_id] += 0
            else:
                # 检查 ego 车是否在 BOTTLENECK 路段
                ego_road = self.vehicle_roadid[ego_id]
                if ego_road == BOTTLENECK:
                    # 检查除 ego 车所在车道之外的 BOTTLENECK 路段上的其他车道上的车辆数量
                    ego_lane = self.ego_laneid[ego_id]
                    other_lanes = [lane for lane in self.lane_counts if
                                   lane != ego_lane and lane.startswith(BOTTLENECK)]
                    if all(self.lane_counts[lane] < 3 for lane in other_lanes):
                        # 如果所有这些车道上的车辆数量都少于 3，那么就给 ego 车一个大的奖励
                        if ego_id not in self.reward_given or not self.reward_given[ego_id]:  # 检查是否已经给出了奖励
                            rewards[ego_id] += 100  # 给 ego 车一个大的奖励
                            self.reward_given[ego_id] = True  # 标记奖励已经给出
                else:
                    rewards[ego_id] -= 1

        return rewards

    def reset(self, seed=1) -> Tuple[Any, Dict[str, Any]]:
        """reset 时初始化
        """
        init_state = self.env.reset() # 初始化环境
        feature_vectors, congestion_level = self.state_wrapper(state=init_state)
        self.__init_actions(raw_state=init_state, congestion_level=congestion_level) # 初始化动作
        self.ego_ids = []

        return feature_vectors, {'step_time': 0}

    def step(self, action: Dict[str, int]) -> Tuple[Any, SupportsFloat, bool, bool, Dict[str, Any]]:
        """1. get action; 2. update action
        """
        action = self.__update_actions(raw_action=action).copy()  # 1. get action
        for ego_id, ego_action in action.items():
            if ego_id in self.ego_ids:
                if self.vehicle_roadid[ego_id] in CONTROL: # 只控制部分的路段
                    current_speed = self.vehicle_speeds[ego_id]
                    new_speed = current_speed + ego_action[1]
                    new_speed = max(0, min(new_speed, MAX_SPEED))
                    action[ego_id] = (0, new_speed)
        
        init_state, rewards, truncated, dones, infos = super().step(action)
        feature_vectors, congestion_level = self.state_wrapper(state=init_state)
        self.__init_actions(raw_state=init_state, congestion_level=congestion_level)
        rewards = 0  # 处理 reward
        self.ego_ids = [] # 获取 ego_ids
        return feature_vectors, rewards, truncated, dones, infos

    def close(self) -> None:
        return super().close()