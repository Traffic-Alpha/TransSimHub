'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 车道/路段级交通状态 (tshub.lane / tshub.edge) 的单元测试.
用假的 sumo connection 喂订阅结果, 不需要真的启动 SUMO.
@LastEditTime: 2026-08-11 10:00:00
'''
import unittest


class FakeLaneAPI:
    def __init__(self, lanes):
        self._lanes = lanes  # {lane_id: (edge_id, length, max_speed)}
        self.subscribed = []
        self.results = {}

    def getIDList(self):
        return list(self._lanes)

    def getEdgeID(self, lane_id):
        return self._lanes[lane_id][0]

    def getLength(self, lane_id):
        return self._lanes[lane_id][1]

    def getMaxSpeed(self, lane_id):
        return self._lanes[lane_id][2]

    def subscribe(self, lane_id, var_ids):
        self.subscribed.append(lane_id)

    def getAllSubscriptionResults(self):
        return self.results


class FakeEdgeAPI:
    def __init__(self, edges):
        self._edges = edges  # {edge_id: n_lanes}
        self.subscribed = []
        self.results = {}

    def getIDList(self):
        return list(self._edges)

    def getLaneNumber(self, edge_id):
        return self._edges[edge_id]

    def getStreetName(self, edge_id):
        return ''

    def subscribe(self, edge_id, var_ids):
        self.subscribed.append(edge_id)

    def getAllSubscriptionResults(self):
        return self.results


class FakeSumo:
    def __init__(self, lanes, edges=None):
        self.lane = FakeLaneAPI(lanes)
        self.edge = FakeEdgeAPI(edges or {})


# 订阅结果的 key (与 traci.constants 一致)
MEAN_SPEED, OCCUPANCY, HALTING, VEH_NUM = 17, 19, 20, 16


class TestLaneBuilder(unittest.TestCase):
    def _build(self):
        from tshub.lane.lane_builder import LaneBuilder
        sumo = FakeSumo({
            'E0_0': ('E0', 100.0, 13.89),
            'E0_1': ('E0', 100.0, 13.89),
            ':J1_0_0': (':J1_0', 10.0, 13.89),  # 路口内部车道
        })
        return LaneBuilder(sumo=sumo), sumo

    def test_skips_internal_lanes_by_default(self):
        builder, sumo = self._build()
        self.assertEqual(set(builder.lanes), {'E0_0', 'E0_1'})
        self.assertEqual(set(sumo.lane.subscribed), {'E0_0', 'E0_1'})

    def test_with_internal_lanes(self):
        from tshub.lane.lane_builder import LaneBuilder
        sumo = FakeSumo({'E0_0': ('E0', 100.0, 13.89), ':J1_0_0': (':J1_0', 10.0, 13.89)})
        builder = LaneBuilder(sumo=sumo, with_internal=True)
        self.assertEqual(set(builder.lanes), {'E0_0', ':J1_0_0'})

    def test_empty_lane_is_free_flow(self):
        """空车道时 SUMO 返回的 mean_speed 就是限速, 拥堵指数应为 1.0 (自由流)."""
        builder, sumo = self._build()
        sumo.lane.results = {
            'E0_0': {MEAN_SPEED: 13.89, OCCUPANCY: 0.0, HALTING: 0, VEH_NUM: 0},
        }
        infos = builder.get_objects_infos()
        self.assertAlmostEqual(infos['E0_0']['speed_relative'], 1.0)

    def test_congested_lane(self):
        builder, sumo = self._build()
        sumo.lane.results = {
            'E0_0': {MEAN_SPEED: 3.4725, OCCUPANCY: 0.8, HALTING: 5, VEH_NUM: 7},
        }
        infos = builder.get_objects_infos()
        self.assertAlmostEqual(infos['E0_0']['speed_relative'], 0.25)
        self.assertEqual(infos['E0_0']['halting_number'], 5)
        self.assertEqual(infos['E0_0']['edge_id'], 'E0')

    def test_speed_factor_overspeed_is_clamped(self):
        """speedFactor 会让实际速度超过限速, 拥堵指数必须截断到 1.0."""
        builder, sumo = self._build()
        sumo.lane.results = {'E0_0': {MEAN_SPEED: 14.414, OCCUPANCY: 0.1, HALTING: 0, VEH_NUM: 1}}
        infos = builder.get_objects_infos()
        self.assertEqual(infos['E0_0']['speed_relative'], 1.0)

    def test_zero_max_speed_is_free_flow(self):
        from tshub.lane.lane_builder import LaneBuilder
        sumo = FakeSumo({'E0_0': ('E0', 100.0, 0.0)})
        builder = LaneBuilder(sumo=sumo)
        sumo.lane.results = {'E0_0': {MEAN_SPEED: 0.0, OCCUPANCY: 0.0, HALTING: 0, VEH_NUM: 0}}
        self.assertEqual(builder.get_objects_infos()['E0_0']['speed_relative'], 1.0)

    def test_missing_subscription_result_keeps_previous(self):
        """某一步没有该车道的订阅结果时, 保留上一步的值而不是崩溃."""
        builder, sumo = self._build()
        sumo.lane.results = {}
        infos = builder.get_objects_infos()
        self.assertAlmostEqual(infos['E0_0']['speed_relative'], 1.0)  # 初始即自由流


class TestEdgeBuilder(unittest.TestCase):
    def _build(self):
        from tshub.edge.edge_builder import EdgeBuilder
        sumo = FakeSumo(
            lanes={
                'E0_0': ('E0', 100.0, 13.89),
                'E0_1': ('E0', 100.0, 13.89),
                'E1_0': ('E1', 50.0, 8.33),
            },
            edges={'E0': 2, 'E1': 1, ':J1_0': 1},
        )
        return EdgeBuilder(sumo=sumo), sumo

    def test_skips_internal_edges_and_derives_lane_ids(self):
        builder, sumo = self._build()
        self.assertEqual(set(builder.edges), {'E0', 'E1'})
        self.assertEqual(builder.edges['E0'].lane_ids, ['E0_0', 'E0_1'])
        # traci.edge 没有 getMaxSpeed, 限速由车道推出
        self.assertAlmostEqual(builder.edges['E0'].max_speed, 13.89)
        self.assertAlmostEqual(builder.edges['E1'].max_speed, 8.33)

    def test_congested_edge(self):
        builder, sumo = self._build()
        sumo.edge.results = {'E0': {MEAN_SPEED: 6.945, OCCUPANCY: 0.5, HALTING: 3, VEH_NUM: 6}}
        infos = builder.get_objects_infos()
        self.assertAlmostEqual(infos['E0']['speed_relative'], 0.5)
        self.assertEqual(infos['E0']['lane_ids'], ['E0_0', 'E0_1'])


if __name__ == '__main__':
    unittest.main()
