'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 初始化 Lane Object, 提供全路网车道级的交通状态
- 车道集合在仿真过程中是不变的, 因此在 create_objects 里一次性建好并订阅,
  之后每步只需要一次 getAllSubscriptionResults, 开销与车辆数无关;
- 输出在 obs['lane_state'], 与 obs['lane_shape'] (map 的静态几何) 用 lane_id 关联。
@LastEditTime: 2026-08-11 10:00:00
'''
from loguru import logger
from typing import Dict, Any

from .lane import LaneInfo
from ..tshub_env.base_builder import BaseBuilder


class LaneBuilder(BaseBuilder):
    """提供路网内所有车道的交通状态 (中观视图的数据来源)"""

    def __init__(self, sumo, with_internal: bool = False) -> None:
        """
        Args:
            sumo: sumo connection.
            with_internal (bool, optional): 是否统计路口内部 (':' 开头) 的车道。
                中观视图只画普通路段, 因此默认关闭。Defaults to False.
        """
        self.sumo = sumo
        self.with_internal = with_internal
        self.lanes: Dict[str, LaneInfo] = {}
        self.create_objects()  # 车道是静态的, 创建一次即可

    def create_objects(self) -> None:
        """初始化路网内所有的车道, 并完成订阅"""
        for lane_id in self.sumo.lane.getIDList():
            if (not self.with_internal) and lane_id.startswith(':'):
                continue  # 跳过路口内部车道
            self.lanes[lane_id] = LaneInfo.create_lane(
                id=lane_id,
                sumo=self.sumo,
                edge_id=self.sumo.lane.getEdgeID(lane_id),
                length=self.sumo.lane.getLength(lane_id),
                max_speed=self.sumo.lane.getMaxSpeed(lane_id),
            )
        logger.info(f'SIM: Init Lane Builder, 共订阅 {len(self.lanes)} 条车道.')

    def update_objects_state(self) -> None:
        """更新所有车道的交通状态 (一次 traci 交互拿全网)"""
        subscription_results = self.sumo.lane.getAllSubscriptionResults()
        for lane_id, lane_info in self.lanes.items():
            if lane_id in subscription_results:
                lane_info.update_features(subscription_results[lane_id])

    def get_objects_infos(self) -> Dict[str, Any]:
        """返回所有车道的交通状态, key 是 lane_id"""
        self.update_objects_state()
        return {
            lane_id: lane_info.get_features()
            for lane_id, lane_info in self.lanes.items()
        }

    def control_objects(self) -> None:
        """车道是只读的观测对象, 不做控制"""
        pass
