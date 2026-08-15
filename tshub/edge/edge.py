'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: Edge Dataclass, 路段级的交通状态 (中观视图的默认粒度)
- https://sumo.dlr.de/docs/TraCI/Edge_Value_Retrieval.html

与 tshub/lane/ 的关系: 同一套指标的两个粒度。
1. edge 级由 SUMO 自己聚合, 权威且数量少 (实测 20 edge : 60 lane), 用来驱动中观视图的路网着色;
2. lane 级 (obs['lane_state']) 数量大, 在点开某条路段看车道明细时才需要,
   能看到「左转道排队、直行道畅通」这类 edge 级看不到的差异。
两者与 SUMO meandata 的 edgeData / laneData 是同样的分工。

注意: traci.edge 没有 getMaxSpeed, 所以路段限速由其车道的限速推出 (取最大值)。
@LastEditTime: 2026-08-11 10:00:00
'''
import traci
from typing import Dict, Any, List
from dataclasses import dataclass, fields


@dataclass
class EdgeInfo:
    """一个路段的静态属性 + 最近一个仿真步的交通状态"""
    # -- 静态属性 (创建时读取一次, 之后不变) --
    id: str  # 路段的 ID
    lane_ids: List[str]  # 路段包含的车道 ID, 用于向 obs['lane_state'] 下钻
    length: float  # 路段长度 (m)
    max_speed: float  # 路段限速 (m/s), 由车道限速推出
    street_name: str  # 路段的街道名 (OSM 路网才有, 否则为空字符串)
    # -- 动态状态 (每步从订阅结果更新) --
    mean_speed: float  # 最近一步路段上车辆的平均速度 (m/s), 空路段时等于限速
    occupancy: float  # 最近一步的占有率 (0~1)
    halting_number: int  # 最近一步的停车数 (速度 < 0.1 m/s 的车辆数)
    vehicle_count: int  # 最近一步路段上的车辆数
    sumo: traci.connection.Connection

    def __post_init__(self) -> None:
        # 订阅路段. 路段集合在仿真过程中不变, 因此只需要在创建时订阅一次
        self.sumo.edge.subscribe(
            self.id,
            [
                traci.constants.LAST_STEP_MEAN_SPEED,
                traci.constants.LAST_STEP_OCCUPANCY,
                traci.constants.LAST_STEP_VEHICLE_HALTING_NUMBER,
                traci.constants.LAST_STEP_VEHICLE_NUMBER,
            ]
        )

    @classmethod
    def create_edge(cls, id: str, sumo: traci.connection.Connection,
                    lane_ids: List[str], length: float, max_speed: float,
                    street_name: str):
        return cls(
            id=id, sumo=sumo,
            lane_ids=lane_ids, length=length, max_speed=max_speed,
            street_name=street_name,
            mean_speed=max_speed,  # 初始视作自由流, 与空路段的语义一致
            occupancy=0.0, halting_number=0, vehicle_count=0,
        )

    @staticmethod
    def get_feature_index(feature: str) -> int:
        """获得某个特征在订阅结果中的 index"""
        feature_mapping = {
            'mean_speed': 17,  # 0x11, LAST_STEP_MEAN_SPEED
            'occupancy': 19,  # 0x13, LAST_STEP_OCCUPANCY
            'halting_number': 20,  # 0x14, LAST_STEP_VEHICLE_HALTING_NUMBER
            'vehicle_count': 16,  # 0x10, LAST_STEP_VEHICLE_NUMBER
        }
        return feature_mapping.get(feature, -1)

    def update_features(self, edge_info: Dict[int, Any]) -> None:
        """从订阅结果更新路段的交通状态"""
        self.mean_speed = edge_info.get(EdgeInfo.get_feature_index('mean_speed'), self.mean_speed)
        self.occupancy = edge_info.get(EdgeInfo.get_feature_index('occupancy'), self.occupancy)
        self.halting_number = edge_info.get(EdgeInfo.get_feature_index('halting_number'), self.halting_number)
        self.vehicle_count = edge_info.get(EdgeInfo.get_feature_index('vehicle_count'), self.vehicle_count)

    @property
    def speed_relative(self) -> float:
        """拥堵指数: 实际速度/限速, 截断到 [0, 1]. 越小越堵, 1 表示自由流"""
        if (self.max_speed is None) or (self.max_speed <= 0):
            return 1.0  # 限速非正时无从判断拥堵, 按自由流处理
        return min(self.mean_speed / self.max_speed, 1.0)

    def get_features(self) -> Dict[str, Any]:
        output_dict = {}
        for field in fields(self):
            if field.name != 'sumo':
                output_dict[field.name] = getattr(self, field.name)
        output_dict['speed_relative'] = self.speed_relative  # 派生量, 一并返回
        return output_dict

    def control_edge(self) -> None:
        """路段是只读的观测对象, 不做控制"""
        pass
