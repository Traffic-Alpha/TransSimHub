'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: Lane Dataclass, 车道级的交通状态 (中观视图的数据来源)
- https://sumo.dlr.de/docs/TraCI/Lane_Value_Retrieval.html

与 tshub/map/ 的区别 (两者都是 lane, 但一静一动):
1. map 提供 lane 的「静态几何」(多边形 shape), 在 obs['lane_shape'];
2. 这里提供 lane 的「动态状态」(速度/占有率/排队), 在 obs['lane_state'].
两者用 lane_id 关联, 中观大屏把这里的拥堵指数涂到 map 的多边形上。

关于拥堵指数 speed_relative (实际速度/限速, 与 SUMO meandata 的 speedRelative 同义):
1. 空车道时 SUMO 的 mean_speed 返回的就是限速本身, 所以空路自然是 1.0 (自由流), 不需要特判;
2. 车辆的 speedFactor 会让实际速度超过限速 (实测有 14.41 > 13.89), 所以要向上截断到 1.0.
@LastEditTime: 2026-08-11 10:00:00
'''
import traci
from typing import Dict, Any
from dataclasses import dataclass, fields


@dataclass
class LaneInfo:
    """一条车道的静态属性 + 最近一个仿真步的交通状态"""
    # -- 静态属性 (创建时读取一次, 之后不变) --
    id: str  # 车道的 ID
    edge_id: str  # 车道所属的 edge ID
    length: float  # 车道长度 (m)
    max_speed: float  # 车道限速 (m/s)
    # -- 动态状态 (每步从订阅结果更新) --
    mean_speed: float  # 最近一步车道上车辆的平均速度 (m/s), 空车道时等于限速
    occupancy: float  # 最近一步的占有率 (0~1)
    halting_number: int  # 最近一步的停车数 (速度 < 0.1 m/s 的车辆数)
    vehicle_count: int  # 最近一步车道上的车辆数
    sumo: traci.connection.Connection

    def __post_init__(self) -> None:
        # 订阅车道. 车道集合在仿真过程中不变, 因此只需要在创建时订阅一次
        self.sumo.lane.subscribe(
            self.id,
            [
                traci.constants.LAST_STEP_MEAN_SPEED,
                traci.constants.LAST_STEP_OCCUPANCY,
                traci.constants.LAST_STEP_VEHICLE_HALTING_NUMBER,
                traci.constants.LAST_STEP_VEHICLE_NUMBER,
            ]
        )

    @classmethod
    def create_lane(cls, id: str, sumo: traci.connection.Connection,
                    edge_id: str, length: float, max_speed: float):
        return cls(
            id=id, sumo=sumo,
            edge_id=edge_id, length=length, max_speed=max_speed,
            mean_speed=max_speed,  # 初始视作自由流, 与空车道的语义一致
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

    def update_features(self, lane_info: Dict[int, Any]) -> None:
        """从订阅结果更新车道的交通状态"""
        self.mean_speed = lane_info.get(LaneInfo.get_feature_index('mean_speed'), self.mean_speed)
        self.occupancy = lane_info.get(LaneInfo.get_feature_index('occupancy'), self.occupancy)
        self.halting_number = lane_info.get(LaneInfo.get_feature_index('halting_number'), self.halting_number)
        self.vehicle_count = lane_info.get(LaneInfo.get_feature_index('vehicle_count'), self.vehicle_count)

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

    def control_lane(self) -> None:
        """车道是只读的观测对象, 不做控制"""
        pass
