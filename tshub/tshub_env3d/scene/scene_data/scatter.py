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


# Placement style (metres).  Offsets are measured outward from the road edge.
SCATTER_STYLE = {
    "trees": {
        "assets": ("stylized_common_tree_3", "stylized_common_tree_5", "stylized_pine_5"),
        "offset": 5.8, "spacing": 9.0, "scale": (0.80, 1.10),  # street trees
        "green_spacing": 8.0,                                   # trees in OSM greens
    },
    # no-OSM only: buildings form short continuous street-frontage blocks.
    # Asset frontage is the local X width in metres; local -Y is the window facade.
    "buildings": {
        "setback": 14.5, "block_gap": (18.0, 35.0), "cluster_size": (3, 5),
        "building_gap": (0.8, 1.8), "block_keep_prob": 0.9,
        "setback_jitter": 0.45, "yaw_jitter": 0.035, "scale": (0.70, 0.80),
        "clearance": 0.8, "junction_clearance": 26.0,
        "max_per_100m": 2.6, "min_total": 12, "max_total_cap": 350,
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


def _road_union(road_polys):
    """One (multi)polygon covering all drivable surface."""
    return unary_union([poly.buffer(0) for poly, _meta in road_polys])


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


def _trees_in_greens(green_polys, bbox, style, rng, asset):
    """Scatter trees inside OSM green areas (parks/forests), density by area."""
    spacing = style["trees"]["green_spacing"]
    cell = spacing * spacing
    trees = []
    for poly in green_polys:
        minx, miny, maxx, maxy = poly.bounds
        target = min(int(poly.area / cell), 300)
        placed, attempts = 0, target * 6
        for _ in range(attempts):
            if placed >= target:
                break
            x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
            if _in_bbox(x, y, bbox) and poly.contains(Point(x, y)):
                trees.append(_tree(rng, x, y, style, asset))
                placed += 1
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
    trees.extend(_trees_in_greens(green_polys, bbox, style, rng, tree_asset))  # OSM parks/forests
    if len(trees) > MAX_TREES:
        trees = rng.sample(trees, MAX_TREES)
    return trees


def _building_footprint(x, y, yaw, frontage, depth):
    """Approximate a building's rotated ground footprint."""
    footprint = box(-frontage * 0.5, -depth * 0.5, frontage * 0.5, depth * 0.5)
    footprint = affinity.rotate(footprint, math.degrees(yaw), origin=(0.0, 0.0))
    return affinity.translate(footprint, x, y)


def _quadrant_key(x, y, bbox):
    cx = (bbox[0] + bbox[2]) * 0.5
    cy = (bbox[1] + bbox[3]) * 0.5
    return ("R" if x >= cx else "L") + ("T" if y >= cy else "B")


def _building_placements(road_union, bbox, style, seed):
    """No-OSM only: a realistic street frontage of building models.

    Buildings sit on a consistent setback line in short connected blocks, with
    larger gaps between blocks.  When OSM footprints exist they are extruded by
    build_scene, not placed here.
    C5640 ordinary buildings use their local -Y side as the main window facade,
    so yaw is chosen such that local -Y points toward the nearest road surface.
    """
    rng = random.Random(seed + 7)
    bs = style["buildings"]
    lo, hi = bs["scale"]
    placed, footprints = [], []
    quadrant_counts = {}
    ring = _line_ring(road_union, bs["setback"])
    lines = list(_line_components(ring))
    frontage_length = sum(line.length for line in lines)
    max_buildings = int(round(frontage_length * bs["max_per_100m"] / 100.0))
    max_buildings = max(bs["min_total"], min(max_buildings, bs["max_total_cap"]))
    max_per_quadrant = max(1, int(math.ceil(max_buildings / 4.0)))
    gap_lo, gap_hi = bs["building_gap"]
    block_gap_lo, block_gap_hi = bs["block_gap"]
    cluster_lo, cluster_hi = bs["cluster_size"]
    clearance = bs["clearance"]
    center_x = (bbox[0] + bbox[2]) * 0.5
    center_y = (bbox[1] + bbox[3]) * 0.5
    junction_clearance = bs.get("junction_clearance", 0.0)
    for line in lines:
        length = line.length
        d = rng.uniform(0.0, block_gap_hi)
        while d < length:
            if rng.random() > bs["block_keep_prob"]:
                d += rng.uniform(block_gap_lo, block_gap_hi)
                continue
            asset, native_frontage, native_depth = rng.choice(bs["assets"])
            for _ in range(rng.randint(cluster_lo, cluster_hi)):
                if len(placed) >= max_buildings:
                    return placed
                scale = rng.uniform(lo, hi)
                frontage = native_frontage * scale
                depth = native_depth * scale
                center_d = d + frontage * 0.5
                if center_d >= length:
                    break
                here = line.interpolate(center_d)
                ahead = line.interpolate(min(center_d + 0.5, length))
                ang = math.atan2(ahead.y - here.y, ahead.x - here.x)
                nx, ny = -math.sin(ang), math.cos(ang)
                j = rng.uniform(-bs["setback_jitter"], bs["setback_jitter"])
                bx, by = here.x + nx * j, here.y + ny * j
                if not _in_bbox(bx, by, bbox, margin=3.0):
                    d += frontage + rng.uniform(gap_lo, gap_hi)
                    continue
                if junction_clearance and math.hypot(bx - center_x, by - center_y) < junction_clearance:
                    d += frontage + rng.uniform(gap_lo, gap_hi)
                    continue
                _building_pt, road_pt = nearest_points(Point(bx, by), road_union)
                road_ang = math.atan2(road_pt.y - by, road_pt.x - bx)
                yaw = road_ang + math.pi / 2 + rng.uniform(-bs["yaw_jitter"], bs["yaw_jitter"])
                quadrant = _quadrant_key(bx, by, bbox)
                if quadrant_counts.get(quadrant, 0) >= max_per_quadrant:
                    d += frontage + rng.uniform(gap_lo, gap_hi)
                    continue
                footprint = _building_footprint(bx, by, yaw, frontage, depth)
                padded = footprint.buffer(clearance)
                if any(padded.intersects(existing) for existing in footprints):
                    d += frontage + rng.uniform(gap_lo, gap_hi)
                    continue
                placed.append({"asset": asset, "pos": [bx, by], "yaw": yaw,
                               "size": None, "height": None, "scale": scale})
                footprints.append(footprint)
                quadrant_counts[quadrant] = quadrant_counts.get(quadrant, 0) + 1
                d += frontage + rng.uniform(gap_lo, gap_hi)
            d += rng.uniform(block_gap_lo, block_gap_hi)
    return placed


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
    if len(props) > MAX_PROPS:
        props = rng.sample(props, MAX_PROPS)
    return props


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
    building_sites = [] if buildings else _building_placements(road_union, bbox, style, seed) # 如果 OSM 有建筑就不再随机放置建筑物
    props = _prop_placements(road_union, bbox, style, seed)
    return {"trees": trees, "buildings": building_sites, "props": props}
