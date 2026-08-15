'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: UAV 邻近对象查询 (tshub.aircraft.aircraft_nearby) 的单元测试. 纯函数, 无需 SUMO.
@LastEditTime: 2026-08-11 10:00:00
'''
import unittest

from tshub.aircraft.aircraft_nearby import find_objects_near_aircraft


OBS = {
    'aircraft': {
        'uav_1': {'position': (0.0, 0.0, 100.0)},
    },
    'vehicle': {
        'near': {'position': (30.0, 40.0, 0.0)},    # 距离 50
        'edge': {'position': (100.0, 0.0, 0.0)},    # 距离 100, 正好在边界上
        'far': {'position': (300.0, 0.0, 0.0)},     # 距离 300
    },
    'tls': {
        'J1': {'in_road_stop_line': {'r_a': [(10.0, 0.0), (30.0, 0.0)]}},   # 中心 (20, 0)
        'J2': {'in_road_stop_line': {'r_a': [(500.0, 0.0), (520.0, 0.0)]}},  # 中心 (510, 0)
    },
}


class TestFindObjectsNearAircraft(unittest.TestCase):
    def test_radius_filter(self):
        nearby = find_objects_near_aircraft(OBS, radius=100.0)
        self.assertEqual(nearby['uav_1']['vehicle'], ['near', 'edge'])  # 按距离排序, far 被排除
        self.assertEqual(nearby['uav_1']['tls'], ['J1'])

    def test_boundary_is_inclusive(self):
        """距离正好等于半径时算「在附近」"""
        self.assertIn('edge', find_objects_near_aircraft(OBS, radius=100.0)['uav_1']['vehicle'])
        self.assertNotIn('edge', find_objects_near_aircraft(OBS, radius=99.0)['uav_1']['vehicle'])

    def test_distance_ignores_altitude(self):
        """UAV 在 100m 高空时, 正下方的车辆仍应算「在附近」(距离只算 XY 平面)"""
        obs = {
            'aircraft': {'uav_1': {'position': (0.0, 0.0, 100.0)}},
            'vehicle': {'below': {'position': (0.0, 0.0, 0.0)}},
        }
        nearby = find_objects_near_aircraft(obs, radius=10.0, targets=['vehicle'])
        self.assertEqual(nearby['uav_1']['vehicle'], ['below'])

    def test_max_per_type(self):
        nearby = find_objects_near_aircraft(OBS, radius=1000.0, targets=['vehicle'], max_per_type=2)
        self.assertEqual(nearby['uav_1']['vehicle'], ['near', 'edge'])  # 只留最近的两个

    def test_targets_selection(self):
        nearby = find_objects_near_aircraft(OBS, radius=100.0, targets=['tls'])
        self.assertEqual(set(nearby['uav_1']), {'tls'})

    def test_aircraft_ids_filter(self):
        obs = dict(OBS)
        obs['aircraft'] = {'uav_1': {'position': (0.0, 0.0, 100.0)},
                           'uav_2': {'position': (0.0, 0.0, 100.0)}}
        nearby = find_objects_near_aircraft(obs, radius=100.0, aircraft_ids=['uav_2'])
        self.assertEqual(set(nearby), {'uav_2'})

    def test_no_aircraft_returns_empty(self):
        self.assertEqual(find_objects_near_aircraft({'vehicle': {}}), {})
        self.assertEqual(find_objects_near_aircraft({'aircraft': {}}), {})

    def test_missing_target_obs_is_tolerated(self):
        """只开了 aircraft builder 时, obs 里没有 vehicle/tls 也不应该报错"""
        nearby = find_objects_near_aircraft({'aircraft': {'uav_1': {'position': (0.0, 0.0, 100.0)}}})
        self.assertEqual(nearby['uav_1'], {'vehicle': [], 'tls': []})


if __name__ == '__main__':
    unittest.main()
