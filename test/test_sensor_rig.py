'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 渲染器无关的相机 rig 规格 (scene.sensor_rig) 单元测试.
@LastEditTime: 2026-06-01 00:00:00
'''
import math
import unittest


class TestSensorRig(unittest.TestCase):
    def test_registry_covers_all_valid_sensors(self):
        """CAMERA_RIGS 必须覆盖 VALID_SENSORS 中的每一个 sensor_type."""
        from tshub.tshub_env3d.scene import CAMERA_RIGS, VALID_SENSORS
        all_valid = {s for sensors in VALID_SENSORS.values() for s in sensors}
        missing = all_valid - set(CAMERA_RIGS)
        self.assertEqual(missing, set(), f"these sensor_types have no rig: {missing}")

    def test_modality_and_carrier_parsed(self):
        """每个 base rig 会派生 _rgb / _seg 两个 modality, carrier 保持不变."""
        from tshub.tshub_env3d.scene import get_camera_rig
        self.assertEqual(get_camera_rig('front_left_rgb').modality, 'rgb')
        self.assertEqual(get_camera_rig('front_left_seg').modality, 'seg')
        self.assertEqual(get_camera_rig('front_left_rgb').carrier, 'vehicle')
        self.assertEqual(get_camera_rig('junction_front_rgb').carrier, 'tls')
        self.assertEqual(get_camera_rig('aircraft_rgb').carrier, 'aircraft')

    def test_unknown_sensor_raises(self):
        from tshub.tshub_env3d.scene import get_camera_rig
        with self.assertRaises(KeyError):
            get_camera_rig('nope')

    def test_compute_pose_front_camera(self):
        """车头相机: 朝车辆 heading 正前方, 注视点在前方 look_distance 处.

        heading 采用 tshub/SMARTS 约定: 0 度指向 +Y, 逆时针为正 (见 compute_camera_pose).
        front 的 pull_back 为负 (-1.8), 表示 eye 沿视线方向前移到车头, 而不是后退.
        """
        from tshub.tshub_env3d.scene import get_camera_rig, compute_camera_pose
        rig = get_camera_rig('front_rgb')
        eye, target = compute_camera_pose(rig, (100.0, 200.0), carrier_heading_deg=0.0)
        # heading=0 -> 前方是 +Y; eye 在车头前 |pull_back| 处、抬高 height
        self.assertAlmostEqual(eye[0], 100.0)
        self.assertAlmostEqual(eye[1], 200.0 - rig.pull_back)
        self.assertAlmostEqual(eye[2], rig.height)
        # 注视点在 +Y 方向 look_distance 处
        self.assertAlmostEqual(target[0], 100.0)
        self.assertAlmostEqual(target[1], 200.0 + rig.look_distance)

    def test_compute_pose_yaw_offset(self):
        """front_left 看向相对 heading -30 度 (即从 +Y 起逆时针转 -30 -> 60 度)."""
        from tshub.tshub_env3d.scene import get_camera_rig, compute_camera_pose
        rig = get_camera_rig('front_left_rgb')
        _, target = compute_camera_pose(rig, (0.0, 0.0), carrier_heading_deg=0.0)
        ang = math.degrees(math.atan2(target[1], target[0]))
        self.assertAlmostEqual(ang, 90.0 + rig.yaw_offset_deg, places=3)

    def test_compute_pose_top_down_and_height_override(self):
        """俯视相机看正下方; tls 用 height_override 覆盖相机高度."""
        from tshub.tshub_env3d.scene import get_camera_rig, compute_camera_pose
        bev = get_camera_rig('bev_rgb')
        eye, target = compute_camera_pose(bev, (5.0, 6.0), carrier_heading_deg=123.0)
        self.assertEqual((eye[0], eye[1]), (5.0, 6.0))
        self.assertEqual((target[0], target[1]), (5.0, 6.0))   # 正下方
        self.assertGreater(eye[2], target[2])                  # 相机在上方

        jf = get_camera_rig('junction_front_rgb')
        eye2, _ = compute_camera_pose(jf, (0.0, 0.0), 0.0, height_override=15.0)
        self.assertAlmostEqual(eye2[2], 15.0)


if __name__ == '__main__':
    unittest.main()
