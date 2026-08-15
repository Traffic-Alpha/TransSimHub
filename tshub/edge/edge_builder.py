'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 初始化 Edge Object, 提供全路网路段级的交通状态
- 路段集合在仿真过程中是不变的, 因此在 create_objects 里一次性建好并订阅,
  之后每步只需要一次 getAllSubscriptionResults, 开销与车辆数无关;
- 输出在 obs['edge_state'], 是中观视图的默认粒度 (再细可下钻到 obs['lane_state'])。
@LastEditTime: 2026-08-11 10:00:00
'''
from loguru import logger
from typing import Dict, Any

from .edge import EdgeInfo
from ..tshub_env.base_builder import BaseBuilder


class EdgeBuilder(BaseBuilder):
    """提供路网内所有路段的交通状态 (中观视图的数据来源)"""

    def __init__(self, sumo, with_internal: bool = False) -> None:
        """
        Args:
            sumo: sumo connection.
            with_internal (bool, optional): 是否统计路口内部 (':' 开头) 的路段。
                中观视图只画普通路段, 因此默认关闭。Defaults to False.
        """
        self.sumo = sumo
        self.with_internal = with_internal
        self.edges: Dict[str, EdgeInfo] = {}
        self.create_objects()  # 路段是静态的, 创建一次即可

    def create_objects(self) -> None:
        """初始化路网内所有的路段, 并完成订阅"""
        for edge_id in self.sumo.edge.getIDList():
            if (not self.with_internal) and edge_id.startswith(':'):
                continue  # 跳过路口内部路段
            # traci.edge 没有 getMaxSpeed/getLength, 因此从其车道推出
            lane_ids = [
                f'{edge_id}_{lane_index}'
                for lane_index in range(self.sumo.edge.getLaneNumber(edge_id))
            ]
            lane_max_speeds = [self.sumo.lane.getMaxSpeed(lane_id) for lane_id in lane_ids]
            lane_lengths = [self.sumo.lane.getLength(lane_id) for lane_id in lane_ids]
            self.edges[edge_id] = EdgeInfo.create_edge(
                id=edge_id,
                sumo=self.sumo,
                lane_ids=lane_ids,
                length=max(lane_lengths) if lane_lengths else 0.0,
                max_speed=max(lane_max_speeds) if lane_max_speeds else 0.0,
                street_name=self.sumo.edge.getStreetName(edge_id),
            )
        logger.info(f'SIM: Init Edge Builder, 共订阅 {len(self.edges)} 个路段.')

    def update_objects_state(self) -> None:
        """更新所有路段的交通状态 (一次 traci 交互拿全网)"""
        subscription_results = self.sumo.edge.getAllSubscriptionResults()
        for edge_id, edge_info in self.edges.items():
            if edge_id in subscription_results:
                edge_info.update_features(subscription_results[edge_id])

    def get_objects_infos(self) -> Dict[str, Any]:
        """返回所有路段的交通状态, key 是 edge_id"""
        self.update_objects_state()
        return {
            edge_id: edge_info.get_features()
            for edge_id, edge_info in self.edges.items()
        }

    def control_objects(self) -> None:
        """路段是只读的观测对象, 不做控制"""
        pass
