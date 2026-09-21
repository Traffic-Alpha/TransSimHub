'''
@Author: WANG Maonan
@Date: 2026-07-11
@Description: City-builder prop placement (Stage 1, shapely).

Decides WHERE roadside props go and writes plain positions/orientations into the
scene JSON; Blender (Stage 2) only instances asset templates at these transforms.
Keeping the geometry logic here (shapely has the road polygons) gives clean
"along the road" lines and OSM-aware building placement, and lets Blender share
one mesh per asset so the exported GLB stays small.

Output schema (added to scene data under ``scatter``):
    {
      "trees":     [{"asset": "asset_name", "pos": [x, y], "yaw": rad, "scale": s}, ...],
      "buildings": [{"pos": [x, y], "yaw": rad, "size": [w, d] | null,
                     "height": h | null}, ...],
      "props":     [{"asset": "asset_name", "pos": [x, y], "yaw": rad, "scale": s}, ...],
    }
'''
import math
import random

from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import nearest_points, unary_union
from shapely.prepared import prep


# Placement style (metres).  Offsets are measured outward from the road edge.
SCATTER_STYLE = {
    "trees": {
        "assets": ("stylized_common_tree_3", "stylized_common_tree_5", "stylized_pine_5"),
        "offset": 5.8, "spacing": 9.0, "scale": (0.80, 1.10),  # street trees
        # trees in OSM greens: 只种 (inner, outer) 这条离路面的带, 抖动网格排布
        "green_spacing": 8.0, "green_band": (9.0, 25.0),
    },
    # no-OSM only: buildings form short continuous street-frontage blocks.
    # Asset frontage is the local X width in metres; local -Y is the window facade.
    "buildings": {
        "setback": 14.5, "block_gap": (18.0, 35.0), "cluster_size": (3, 5),
        "building_gap": (0.8, 1.8), "block_keep_prob": 0.9,
        "setback_jitter": 0.45, "yaw_jitter": 0.035, "scale": (0.70, 0.80),
        "clearance": 0.8, "junction_clearance": 8.0,  # 离路口面 (node polygon) 的距离
        "max_per_100m": 2.6, "max_total_cap": 350,
        "assets": (
            ("c5640_building_01", 18.55, 11.51),
            ("c5640_building_02", 19.60, 13.46),
            ("c5640_building_04", 10.17, 6.69),
            ("c5640_building_11", 12.04, 7.05),
        ),
    },
    "props": {
        # Street lights are regular infrastructure: denser and close to the curb.
        "streetlight": {"asset": "c5640_streetlight_08", "offset": 1.8, "spacing": 28.0,
                        "keep_prob": 0.95, "along_jitter": 0.7, "perp_jitter": 0.25,
                        "scale": (0.95, 1.05), "yaw_offset": math.pi, "face_road": True},
        # Benches are occasional sidewalk furniture: sparser and farther from the curb.
        "bench": {"asset": "c5640_bench_02", "offset": 3.0, "spacing": 32.0,
                  "keep_prob": 0.75, "along_jitter": 1.7, "perp_jitter": 0.45,
                  "scale": (0.90, 1.00), "yaw_offset": 0.0},
    },
}

# Keep node counts (and Panda load time) sane on large OSM maps.
MAX_TREES = 1500
MAX_PROPS = 500


def _decimate(items, limit):
    """超过上限时按固定步长均匀抽稀.

    随机抽样 (rng.sample) 会把沿路等间距的行道树撕成忽疏忽密的一串, 看上去就是
    "树没有沿着路种"; 固定步长则是整体变稀, 间距仍然均匀.
    """
    if len(items) <= limit:
        return items
    step = len(items) / limit
    return [items[int(i * step)] for i in range(limit)]


def _road_union(road_polys):
    """One (multi)polygon covering all drivable surface."""
    return unary_union([poly.buffer(0) for poly, _meta in road_polys])


def _junction_union(road_polys):
    """路口面 (SUMO node 多边形) 的并集; 车道面的 metadata 里带 lane_id, 路口面没有."""
    polys = [poly.buffer(0) for poly, meta in road_polys if "lane_id" not in meta]
    return unary_union(polys) if polys else None


def _line_components(geom):
    """Yield each LineString from a boundary (LineString / MultiLineString)."""
    if geom.is_empty:
        return
    if geom.geom_type == "MultiLineString":
        yield from geom.geoms
    elif geom.geom_type == "LineString":
        yield geom


def _walk_line(line, spacing, phase=0.0):
    """Yield (x, y, tangent_angle) sampled every ``spacing`` along a line."""
    length = line.length
    if length < spacing:
        return
    distance = phase * spacing
    while distance <= length:
        here = line.interpolate(distance)
        ahead = line.interpolate(min(distance + 0.5, length))
        yield here.x, here.y, math.atan2(ahead.y - here.y, ahead.x - here.x)
        distance += spacing


def _in_bbox(x, y, bbox, margin=1.0):
    return (bbox[0] + margin) <= x <= (bbox[2] - margin) and \
           (bbox[1] + margin) <= y <= (bbox[3] - margin)


def _line_ring(road_union, offset):
    """The offset curve lining the roads at ``offset`` metres outside the edge."""
    return road_union.buffer(offset).boundary


def _tree(rng, x, y, style, asset):
    lo, hi = style["trees"]["scale"]
    return {"asset": asset, "pos": [x, y], "yaw": rng.uniform(0, math.tau),
            "scale": rng.uniform(lo, hi)}


def _green_polygons(greens, road_union):
    """Valid green polygons with the road surface cut out (no trees on roads)."""
    polys = []
    for ring in greens:
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty or poly.area < 6.0:
            continue
        clipped = poly.difference(road_union)
        if not clipped.is_empty:
            polys.append(clipped)
    return polys


def _trees_in_greens(green_polys, road_union, bbox, style, rng, asset):
    """OSM 绿地里的树: 只种**靠路的一条带**, 并按抖动网格排布.

    两个刻意的限制, 都是为了让绿化跟着道路走:
    - 只取绿地与 road_union 的 (inner, outer) 环形缓冲带相交的部分 —— 远离道路
      的大片林地在场景里既看不见又拖慢加载, 内圈让开则是留给行道树;
    - 抖动网格 (jittered grid) 代替纯随机撒点 —— 随机撒点会明显聚团, 局部一坨树,
      网格保证间距均匀, 加上抖动又不至于像果园一样死板.
    """
    spacing = style["trees"]["green_spacing"]
    inner, outer = style["trees"]["green_band"]
    band = road_union.buffer(outer).difference(road_union.buffer(inner))
    jitter = spacing * 0.35
    trees = []
    for poly in green_polys:
        area = poly.intersection(band)
        if area.is_empty:
            continue
        keep = prep(area)
        minx, miny, maxx, maxy = area.bounds
        for col in range(int((maxx - minx) / spacing) + 1):
            for row in range(int((maxy - miny) / spacing) + 1):
                x = minx + (col + 0.5) * spacing + rng.uniform(-jitter, jitter)
                y = miny + (row + 0.5) * spacing + rng.uniform(-jitter, jitter)
                if _in_bbox(x, y, bbox) and keep.contains(Point(x, y)):
                    trees.append(_tree(rng, x, y, style, asset))
    return trees


def _street_trees(road_union, bbox, style, rng, asset):
    """Evenly spaced trees right along the curb."""
    trees = []
    ring = _line_ring(road_union, style["trees"]["offset"])
    for line in _line_components(ring):
        for x, y, ang in _walk_line(line, style["trees"]["spacing"], phase=rng.random()):
            if _in_bbox(x, y, bbox):
                trees.append(_tree(rng, x, y, style, asset))
    return trees


def _tree_placements(road_union, green_polys, bbox, style, seed):
    """沿街 + OSM 绿地内的树.

    整条街刻意只用**一个**树种 (asset 只抽一次): 行道树本来就是同一批栽的,
    混种反而显得杂乱。想要混种就把 rng.choice 挪到 _tree() 里逐棵抽。
    """
    rng = random.Random(seed)
    tree_asset = rng.choice(style["trees"]["assets"])
    trees = _street_trees(road_union, bbox, style, rng, tree_asset)
    trees.extend(_trees_in_greens(green_polys, road_union, bbox, style, rng, tree_asset))  # OSM parks/forests
    return _decimate(trees, MAX_TREES)


def _building_footprint(x, y, yaw, frontage, depth):
    """Approximate a building's rotated ground footprint."""
    footprint = box(-frontage * 0.5, -depth * 0.5, frontage * 0.5, depth * 0.5)
    footprint = affinity.rotate(footprint, math.degrees(yaw), origin=(0.0, 0.0))
    return affinity.translate(footprint, x, y)


def _building_blocks(line, bs, rng):
    """沿一条退线走一遍, 产出**成组**的候选楼: 每组是一段连续的临街立面 (block).

    返回 block 而不是散楼, 是为了后面抽稀时能整组丢弃 —— 街区内部保持连续,
    只是街区之间的空档变多, 这样才像一条街, 而不是零星散落的房子.
    """
    blocks = []
    length = line.length
    distance = rng.uniform(0.0, bs["block_gap"][1])
    while distance < length:
        if rng.random() > bs["block_keep_prob"]:
            distance += rng.uniform(*bs["block_gap"])
            continue
        asset, native_frontage, native_depth = rng.choice(bs["assets"])
        block = []
        for _ in range(rng.randint(*bs["cluster_size"])):
            scale = rng.uniform(*bs["scale"])
            frontage = native_frontage * scale
            center_d = distance + frontage * 0.5
            if center_d >= length:
                break
            here = line.interpolate(center_d)
            ahead = line.interpolate(min(center_d + 0.5, length))
            ang = math.atan2(ahead.y - here.y, ahead.x - here.x)
            nx, ny = -math.sin(ang), math.cos(ang)
            jitter = rng.uniform(-bs["setback_jitter"], bs["setback_jitter"])
            block.append({
                "asset": asset, "scale": scale,
                "x": here.x + nx * jitter, "y": here.y + ny * jitter,
                "frontage": frontage, "depth": native_depth * scale,
            })
            distance += frontage + rng.uniform(*bs["building_gap"])
        if block:
            blocks.append(block)
        distance += rng.uniform(*bs["block_gap"])
    return blocks


def _thin_blocks(blocks, quota):
    """把一条线上的候选楼抽稀到 quota 栋左右, 按 block 整组丢, 沿线均匀分布."""
    total = sum(len(block) for block in blocks)
    if total <= quota or not blocks:
        return blocks
    keep = max(1, int(round(len(blocks) * quota / total)))
    return _decimate(blocks, keep)


def _building_placements(road_union, junctions, bbox, style, seed):
    """No-OSM only: a realistic street frontage of building models.

    每条退线**各自**按自己的长度算名额 (max_per_100m) 再整组抽稀, 所以整张图的
    沿街密度是均匀的。以前是所有线共用一个全局名额、按走到的先后先到先得,
    名额一旦用完, 排在后面的线 (往往就是地图的某一侧或某几个街区) 一栋都分不到;
    再叠上一个按 bbox 象限的配额, 同一象限里先走到的那段又会把配额吃光 ——
    "某一侧建筑物很少" 就是这么来的.

    Buildings sit on a consistent setback line in short connected blocks, with
    larger gaps between blocks.  When OSM footprints exist they are extruded by
    build_scene, not placed here.
    C5640 ordinary buildings use their local -Y side as the main window facade,
    so yaw is chosen such that local -Y points toward the nearest road surface.
    """
    rng = random.Random(seed + 7)
    bs = style["buildings"]
    placed, footprints = [], []
    for line in _line_components(_line_ring(road_union, bs["setback"])):
        quota = max(1, int(round(line.length * bs["max_per_100m"] / 100.0)))
        for block in _thin_blocks(_building_blocks(line, bs, rng), quota):
            for cand in block:
                point = Point(cand["x"], cand["y"])
                if not _in_bbox(cand["x"], cand["y"], bbox, margin=3.0):
                    continue
                # 路口四角留空: 按到真实路口面的距离算, 不是到地图中心的距离
                if junctions is not None and junctions.distance(point) < bs["junction_clearance"]:
                    continue
                _building_pt, road_pt = nearest_points(point, road_union)
                road_ang = math.atan2(road_pt.y - cand["y"], road_pt.x - cand["x"])
                yaw = road_ang + math.pi / 2 + rng.uniform(-bs["yaw_jitter"], bs["yaw_jitter"])
                footprint = _building_footprint(cand["x"], cand["y"], yaw,
                                                cand["frontage"], cand["depth"])
                if any(footprint.buffer(bs["clearance"]).intersects(e) for e in footprints):
                    continue
                placed.append({"asset": cand["asset"], "pos": [cand["x"], cand["y"]],
                               "yaw": yaw, "size": None, "height": None,
                               "scale": cand["scale"]})
                footprints.append(footprint)
    return _decimate(placed, bs["max_total_cap"])


def _roadside_prop_placements(road_union, bbox, prop_style, rng):
    """One type of roadside furniture along curb/sidewalk lines."""
    lo, hi = prop_style["scale"]
    props = []
    ring = _line_ring(road_union, prop_style["offset"])
    for line in _line_components(ring):
        for x, y, ang in _walk_line(line, prop_style["spacing"], phase=rng.random()):
            if rng.random() > prop_style["keep_prob"]:
                continue
            nx, ny = -math.sin(ang), math.cos(ang)
            px = x + math.cos(ang) * rng.uniform(-prop_style["along_jitter"], prop_style["along_jitter"])
            py = y + math.sin(ang) * rng.uniform(-prop_style["along_jitter"], prop_style["along_jitter"])
            px += nx * rng.uniform(-prop_style["perp_jitter"], prop_style["perp_jitter"])
            py += ny * rng.uniform(-prop_style["perp_jitter"], prop_style["perp_jitter"])
            if _in_bbox(px, py, bbox):
                yaw = ang + prop_style["yaw_offset"]
                if prop_style.get("face_road"):
                    _prop_pt, road_pt = nearest_points(Point(px, py), road_union)
                    dx, dy = road_pt.x - px, road_pt.y - py
                    if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                        yaw = math.atan2(dy, dx) + prop_style["yaw_offset"]
                props.append({"asset": prop_style["asset"], "pos": [px, py],
                              "yaw": yaw + rng.uniform(-0.08, 0.08),
                              "scale": rng.uniform(lo, hi)})
    return props


def _prop_placements(road_union, bbox, style, seed):
    """Small roadside props with per-asset density and orientation."""
    rng = random.Random(seed + 13)
    props = []
    for prop_style in style["props"].values():
        props.extend(_roadside_prop_placements(road_union, bbox, prop_style, rng))
    return _decimate(props, MAX_PROPS)


def build_scatter(road_polys, buildings, greens, bbox, seed=0, style=None):
    """Return the ``scatter`` dict of prop placements for the scene JSON.

    ``buildings`` (OSM footprints) are NOT placed here when present — build_scene
    extrudes them directly, so ``scatter['buildings']`` is only the no-OSM model
    fallback.  ``greens`` (OSM park/forest footprints) seed in-area trees.
    """
    style = style or SCATTER_STYLE
    road_union = _road_union(road_polys)
    green_polys = _green_polygons(greens, road_union)
    trees = _tree_placements(road_union, green_polys, bbox, style, seed)
    # 如果 OSM 有建筑就不再随机放置建筑物
    building_sites = [] if buildings else _building_placements(
        road_union, _junction_union(road_polys), bbox, style, seed)
    props = _prop_placements(road_union, bbox, style, seed)
    return {"trees": trees, "buildings": building_sites, "props": props}
