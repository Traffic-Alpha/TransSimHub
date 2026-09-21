'''
@Author: WANG Maonan
@Date: 2026-08-18
@Description: 守住「刻意的重复实现」—— core/export 的纯 math 几何 必须与
core/utils/coordinates 的 SMARTS 实现逐值等价.

背景: core/export/blender_export.py 为了让离线导出这条路径只依赖标准库 (不拖
numpy/shapely 进来), 自己实现了「SUMO 航向 -> 逆时针角度」与「车头 -> 车辆中心」.
这是有意的取舍, 代价是同一套几何有两份实现 —— 本测试就是那份取舍的兜底:
两边一旦漂移, 这里立刻失败.
@LastEditTime: 2026-08-18
'''
import math
import unittest

HEADINGS = [0.0, 1.0, 45.0, 89.9, 90.0, 135.0, 180.0, 225.0, 270.0, 359.9, 360.0, -30.0, 725.0]


class TestExportGeometryEquivalence(unittest.TestCase):
    def test_sumo_heading_matches_Heading_from_sumo(self):
        """sumo_heading_to_ccw_deg ≡ degrees(Heading.from_sumo(·))  (可差整数圈)."""
        from tshub.tshub_env3d.core.export.blender_export import sumo_heading_to_ccw_deg
        from tshub.tshub_env3d.core.utils.coordinates import Heading
        for sumo_deg in HEADINGS:
            mine = sumo_heading_to_ccw_deg(sumo_deg)
            ref = math.degrees(Heading.from_sumo(sumo_deg))
            diff = (mine - ref) % 360.0
            diff = min(diff, 360.0 - diff)  # 角度环绕: 359.999… 与 0 是同一个角
            self.assertAlmostEqual(diff, 0.0, places=6,
                                   msg=f"sumo_heading={sumo_deg}: {mine} vs {ref}")

    def test_heading_to_vec_matches_radians_to_vec(self):
        """heading_to_vec ≡ core_math.radians_to_vec (同一个方向向量约定)."""
        from tshub.tshub_env3d.core.export.blender_export import heading_to_vec
        from tshub.tshub_env3d.core.utils.core_math import radians_to_vec
        for deg in HEADINGS:
            mine = heading_to_vec(deg)
            ref = radians_to_vec(math.radians(deg))
            self.assertAlmostEqual(mine[0], float(ref[0]), places=9, msg=f"deg={deg}")
            self.assertAlmostEqual(mine[1], float(ref[1]), places=9, msg=f"deg={deg}")

    def test_front_bumper_to_center_matches_Pose(self):
        """front_bumper_to_center ≡ Pose.from_front_bumper 的车辆中心位置."""
        import numpy as np
        from tshub.tshub_env3d.core.export.blender_export import (
            front_bumper_to_center, sumo_heading_to_ccw_deg,
        )
        from tshub.tshub_env3d.core.utils.coordinates import Heading, Pose
        cases = [((100.0, 200.0), 0.0, 4.5), ((0.0, 0.0), 90.0, 5.0),
                 ((-13.5, 7.25), 217.0, 12.0), ((1557.0, 989.0), 359.0, 0.0)]
        for bumper_xy, sumo_deg, length in cases:
            mine = front_bumper_to_center(bumper_xy, sumo_heading_to_ccw_deg(sumo_deg), length)
            ref = Pose.from_front_bumper(
                front_bumper_position=np.array(bumper_xy),
                heading=Heading.from_sumo(sumo_deg),
                length=length,
            )
            self.assertAlmostEqual(mine[0], float(ref.position[0]), places=6,
                                   msg=f"{bumper_xy} {sumo_deg}° L={length}")
            self.assertAlmostEqual(mine[1], float(ref.position[1]), places=6,
                                   msg=f"{bumper_xy} {sumo_deg}° L={length}")


if __name__ == '__main__':
    unittest.main()
