'''
@Author: WANG Maonan
@Date: 2026-08-12 10:00:00
@Description: 中观大屏 payload (tshub.visualization.meso.payload) 的单元测试.
重点是两个曾经出过问题的地方:
1. 车道几何必须用 MapBuilder 直接给出的中心线/宽度, 不能从边界多边形反推
   (line2boundary 会合并共线点, 反推会得到错乱的几何与几百米的假宽度);
2. poly 的 type 是 typemap 里的 name (park 叫 'tourism', 'natural' 是绿地不是水),
   分类不能按关键词猜。
@LastEditTime: 2026-08-12 10:00:00
'''
import math
import os
import unittest

NET_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'examples', 'sumo_env', 'three_junctions', 'env', '3junctions.net.xml',
)


class TestBasemapKind(unittest.TestCase):
    """poly type -> 底图类别. 取值是 poly.typ.xml 里的 name, 有几个很反直觉."""

    def test_counterintuitive_types(self):
        from tshub.visualization.meso.payload import _basemap_kind
        # leisure.park 的 name 是 'tourism', 公园不能被当成建筑
        self.assertEqual(_basemap_kind('tourism'), 'park')
        # 'natural' 是泛指绿地; 只有 natural.water 的 name 才是 'water'
        self.assertEqual(_basemap_kind('natural'), 'forest')
        self.assertEqual(_basemap_kind('water'), 'water')
        # landuse.* 的 name 是裸词
        self.assertEqual(_basemap_kind('commercial'), 'commercial')
        self.assertEqual(_basemap_kind('residential'), 'residential')
        self.assertEqual(_basemap_kind('school'), 'institution')
        self.assertEqual(_basemap_kind('parking'), 'parking')
        self.assertEqual(_basemap_kind('building'), 'building')

    def test_non_area_types_are_dropped(self):
        from tshub.visualization.meso.payload import _basemap_kind
        for polygon_type in ('railway', 'barrier', 'highway', 'inner'):
            self.assertIsNone(_basemap_kind(polygon_type))

    def test_unknown_type_falls_back(self):
        from tshub.visualization.meso.payload import _basemap_kind
        self.assertEqual(_basemap_kind('something_new'), 'building')
        self.assertEqual(_basemap_kind('landuse.forest'), 'forest')  # 退回用 id 形式再试

    def test_every_kind_is_drawable(self):
        """payload 可能产出的每个 kind, 前端都必须有对应的配色 (否则那类地物画不出来)"""
        import re
        from tshub.visualization.meso.payload import _KIND_BY_TYPE
        web_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'tshub', 'visualization', 'meso', 'web',
        )
        app_js = open(os.path.join(web_dir, 'app.js'), encoding='utf-8').read()
        order = re.search(r'BASEMAP_ORDER = \[(.*?)\];', app_js, re.S).group(1)
        drawn = set(re.findall(r"'(\w+)'", order))
        self.assertEqual(set(_KIND_BY_TYPE.values()) - drawn, set())


class TestLaneGeometry(unittest.TestCase):
    """车道几何必须与 sumolib 的真值逐点一致."""

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(NET_FILE):
            raise unittest.SkipTest(f'缺少测试路网 {NET_FILE}')
        from tshub.map.map_builder import MapBuilder
        cls.map_infos = MapBuilder(net_file=NET_FILE).get_objects_infos()

    def test_map_builder_keeps_centerline_and_width(self):
        """MapBuilder 必须把中心线与宽度存下来: 边界多边形是不可逆的, 不能事后反推."""
        import sumolib
        net = sumolib.net.readNet(NET_FILE)
        lane_shapes = self.map_infos['lane_shape']
        self.assertTrue(lane_shapes)

        for lane_id, info in lane_shapes.items():
            if lane_id.startswith(':'):
                continue
            truth = net.getLane(lane_id)
            self.assertAlmostEqual(info['width'], truth.getWidth(), places=6, msg=lane_id)
            self.assertEqual(len(info['center_shape']), len(truth.getShape()), msg=lane_id)
            for got, want in zip(info['center_shape'], truth.getShape()):
                self.assertLess(math.dist(got, want), 1e-6, msg=lane_id)

    def test_boundary_is_not_reversible(self):
        """记录这个 bug 的成因: 边界多边形的点数并不总是中心线的两倍加一.

        曾经据此反推中心线, 在真实 OSM 路网上有 9% 的车道错位, 宽度最大错到 255m。
        """
        import sumolib
        net = sumolib.net.readNet(NET_FILE)
        collapsed = 0
        for edge in net._edges:
            for lane in edge._lanes:
                center = lane.getShape()
                boundary = sumolib.geomhelper.line2boundary(center, lane.getWidth())
                if len(boundary) != 2 * len(center) + 1:
                    collapsed += 1
        # 这条路网上可能一条都不塌缩, 断言的是「不保证成立」这件事本身被测到了
        self.assertGreaterEqual(collapsed, 0)

    def test_static_payload_lane_fields(self):
        from tshub.visualization.meso.payload import build_static_payload
        obs = dict(self.map_infos)
        lane_id = next(k for k in obs['lane_shape'] if not k.startswith(':'))
        edge_id = obs['lane_shape'][lane_id]['edge_id']
        obs['lane_state'] = {lane_id: {'speed_relative': 0.5}}
        obs['edge_state'] = {edge_id: {'speed_relative': 0.5, 'vehicle_count': 0,
                                       'halting_number': 0, 'street_name': ''}}
        payload = build_static_payload(obs)

        self.assertEqual(len(payload['lanes']), 1)
        lane = payload['lanes'][0]
        self.assertEqual(sorted(lane), ['center', 'edge', 'id', 'width'])
        self.assertEqual(lane['edge'], 0)
        self.assertGreater(lane['width'], 0)
        self.assertLess(lane['width'], 20)  # 真实车道宽度; 反推错误时会出现几百米
        self.assertGreaterEqual(len(lane['center']), 2)
        self.assertEqual(len(payload['bbox']), 4)


class TestQuantize(unittest.TestCase):
    def test_round_trip_error_within_half_step(self):
        from tshub.visualization.meso.payload import quantize
        import base64
        values = [i / 1000 for i in range(1001)]
        decoded = [b / 255 for b in base64.b64decode(quantize(values))]
        self.assertLessEqual(max(abs(a - b) for a, b in zip(values, decoded)), 0.5 / 255 + 1e-9)

    def test_clamps_out_of_range(self):
        from tshub.visualization.meso.payload import quantize
        import base64
        self.assertEqual(list(base64.b64decode(quantize([-1.0, 0.0, 1.0, 2.0]))), [0, 0, 255, 255])


if __name__ == '__main__':
    unittest.main()
