'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 渲染器无关场景描述层 (vis3d_scene) 的单元测试.
重点验证: (1) 该层不依赖 panda3d; (2) build_frame/build_tls_rigs/validate 行为正确.
@LastEditTime: 2026-06-01 00:00:00
'''
import sys
import math
import unittest


class TestSceneBuilder(unittest.TestCase):
    def test_layer_is_panda3d_free(self):
        """导入场景描述层不应引入 panda3d (这是解耦的关键)."""
        import tshub.tshub_env3d.scene  # noqa: F401
        self.assertFalse(
            any(m == 'panda3d' or m.startswith('panda3d.') for m in sys.modules),
            "vis3d_scene 不应该 import panda3d"
        )

    def test_build_frame_vehicle_and_aircraft(self):
        from tshub.tshub_env3d.scene import build_frame
        from tshub.tshub_env3d.scene.utils.core_math import vec_to_radians, vec_2d

        obs = {
            'vehicle': {
                'v1': {'position': (10.0, 20.0, 0.0), 'heading': (1, 0), 'vehicle_type': 'passenger', 'length': 5.0},
            },
            'aircraft': {
                'a1': {'position': (5.0, 6.0, 100.0), 'heading': (0, 1, 0)},
            },
        }
        frame = build_frame(obs)

        # 车辆字段原样透传
        v = frame.vehicles['v1']
        self.assertEqual(v.position, (10.0, 20.0, 0.0))
        self.assertEqual(v.object_type, 'passenger')
        self.assertEqual(v.length, 5.0)
        self.assertEqual(v.heading, (1, 0))

        # 飞行器 heading 转换为角度, 与同一套 helper 计算一致
        a = frame.aircraft['a1']
        expected_deg = math.degrees(vec_to_radians(vec_2d((0, 1, 0)))) % 360
        self.assertAlmostEqual(a.heading, expected_deg)
        self.assertEqual(a.position, (5.0, 6.0, 100.0))

    def test_build_frame_empty(self):
        from tshub.tshub_env3d.scene import build_frame
        frame = build_frame({})
        self.assertEqual(frame.vehicles, {})
        self.assertEqual(frame.aircraft, {})

    def test_build_tls_rigs(self):
        from tshub.tshub_env3d.scene import build_tls_rigs
        init_obs = {
            'tls': {
                'J1': {
                    'in_roads_heading': {'r_a': 90.0, 'r_b': 0.0},
                    'in_road_stop_line': {
                        'r_a': [(0.0, 0.0), (2.0, 0.0)],
                        'r_b': [(0.0, 0.0), (0.0, 4.0)],
                    },
                },
                'J2': {  # 未配置传感器, 应被跳过
                    'in_roads_heading': {'r_c': 0.0},
                    'in_road_stop_line': {'r_c': [(0.0, 0.0)]},
                },
            }
        }
        sensor_config = {'tls': {'J1': {'sensor_types': ['junction_front_rgb'], 'tls_camera_height': 15}}}
        rigs = build_tls_rigs(init_obs, sensor_config)

        # J1 的两个 road 各一个 rig, 按 heading 排序 -> r_b(0) 为 index 0, r_a(90) 为 index 1
        self.assertEqual(set(rigs), {'J1_0', 'J1_1'})
        self.assertEqual(rigs['J1_0']['heading'], 0.0)
        self.assertEqual(rigs['J1_1']['heading'], 90.0)
        self.assertEqual(rigs['J1_0']['sensor_types'], ['junction_front_rgb'])
        self.assertEqual(rigs['J1_0']['tls_camera_height'], 15)
        self.assertIn('position', rigs['J1_0'])

    def test_build_tls_rigs_no_config(self):
        from tshub.tshub_env3d.scene import build_tls_rigs
        self.assertEqual(build_tls_rigs({}, {}), {})
        self.assertEqual(build_tls_rigs({'tls': {'J1': {}}}, {}), {})

    def test_validate_sensor_config(self):
        from tshub.tshub_env3d.scene import validate_sensor_config
        self.assertTrue(validate_sensor_config({'tls': {'J1': {'sensor_types': ['junction_front_rgb']}}}))
        self.assertTrue(validate_sensor_config({}))
        # 非法 object 类别
        self.assertFalse(validate_sensor_config({'spaceship': {'x': {'sensor_types': []}}}))
        # 非法传感器类型
        self.assertFalse(validate_sensor_config({'vehicle': {'v1': {'sensor_types': ['not_a_sensor']}}}))

    def test_renderer_backend_is_abstract(self):
        from tshub.tshub_env3d.scene import RendererBackend
        with self.assertRaises(TypeError):
            RendererBackend()  # 抽象类不能实例化


if __name__ == '__main__':
    unittest.main()
