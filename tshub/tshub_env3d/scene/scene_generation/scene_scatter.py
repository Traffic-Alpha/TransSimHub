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
      "trees":     [{"pos": [x, y], "yaw": rad, "scale": s}, ...],
      "humans":    [{"pos": [x, y], "yaw": rad}, ...],
      "buildings": [{"pos": [x, y], "yaw": rad, "size": [w, d] | null,
                     "height": h | null}, ...],
    }
'''
import math
import random

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union


# Placement style (metres).  Offsets are measured outward from the road edge.
SCATTER_STYLE = {
    "trees": {
        "offset": 3.6, "spacing": 11.0, "scale": (0.85, 1.20),  # street trees
        "green_spacing": 8.0,                                   # trees in OSM greens
        "band_inner": 2.5, "band_outer": 22.0, "band_spacing": 11.0,  # trees between buildings
    },
    # pedestrians gather in small groups (not evenly spaced, else they read as trees)
    "humans": {"offset": 1.5, "cluster_gap": (16.0, 44.0), "group": (1, 4),
               "along_jitter": 1.8, "perp_jitter": 0.7},
    # no-OSM only: a realistic street frontage — buildings sit on a consistent
    # setback line, well spaced (gaps/side-yards between them), aligned facing the
    # street.  Density stays low (like a real block), not a scattered blob.
    "buildings": {"setback": 13.0, "spacing": 27.0, "keep_prob": 0.82,
                  "setback_jitter": 2.0, "yaw_jitter": 0.08, "scale": (1.4, 2.0)},
}

# Keep node counts (and Panda load time) sane on large OSM maps.
MAX_TREES = 1500
MAX_HUMANS = 350


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


def _tree(rng, x, y, style):
    lo, hi = style["trees"]["scale"]
    return {"pos": [x, y], "yaw": rng.uniform(0, math.tau), "scale": rng.uniform(lo, hi)}


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


def _trees_in_greens(green_polys, bbox, style, rng):
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
                trees.append(_tree(rng, x, y, style))
                placed += 1
    return trees


def _street_trees(road_union, bbox, style, rng):
    """Evenly spaced trees right along the curb."""
    trees = []
    ring = _line_ring(road_union, style["trees"]["offset"])
    for line in _line_components(ring):
        for x, y, ang in _walk_line(line, style["trees"]["spacing"], phase=rng.random()):
            if _in_bbox(x, y, bbox):
                trees.append(_tree(rng, x, y, style))
    return trees


def _band_trees(road_union, bbox, style, rng):
    """Trees scattered through the roadside band, i.e. filling gaps between buildings."""
    ts = style["trees"]
    band = road_union.buffer(ts["band_outer"]).difference(road_union.buffer(ts["band_inner"]))
    if band.is_empty:
        return []
    cell = ts["band_spacing"] * ts["band_spacing"]
    minx, miny, maxx, maxy = band.bounds
    target = min(int(band.area / cell), MAX_TREES)
    trees, placed, attempts = [], 0, target * 6
    for _ in range(attempts):
        if placed >= target:
            break
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if _in_bbox(x, y, bbox) and band.contains(Point(x, y)):
            trees.append(_tree(rng, x, y, style))
            placed += 1
    return trees


def _clustered_humans(road_union, bbox, style, rng):
    """People gather in small groups along the sidewalk (not evenly spaced)."""
    hs = style["humans"]
    gap_lo, gap_hi = hs["cluster_gap"]
    grp_lo, grp_hi = hs["group"]
    humans = []
    ring = _line_ring(road_union, hs["offset"])
    for line in _line_components(ring):
        length = line.length
        d = rng.uniform(0, gap_hi)
        while d < length:
            here = line.interpolate(d)
            ahead = line.interpolate(min(d + 0.5, length))
            ang = math.atan2(ahead.y - here.y, ahead.x - here.x)
            nx, ny = -math.sin(ang), math.cos(ang)  # toward the verge
            facing = ang + (0.0 if rng.random() < 0.5 else math.pi)
            for _ in range(rng.randint(grp_lo, grp_hi)):
                t = rng.uniform(-hs["along_jitter"], hs["along_jitter"])
                p = rng.uniform(-hs["perp_jitter"], hs["perp_jitter"])
                x = here.x + math.cos(ang) * t + nx * p
                y = here.y + math.sin(ang) * t + ny * p
                if _in_bbox(x, y, bbox):
                    humans.append({"pos": [x, y], "yaw": facing + rng.uniform(-0.3, 0.3)})
            d += rng.uniform(gap_lo, gap_hi)
    return humans


def _tree_and_human_placements(road_union, green_polys, bbox, style, seed):
    rng = random.Random(seed)
    trees = _street_trees(road_union, bbox, style, rng)
    trees.extend(_trees_in_greens(green_polys, bbox, style, rng))  # OSM parks/forests
    trees.extend(_band_trees(road_union, bbox, style, rng))        # between buildings
    humans = _clustered_humans(road_union, bbox, style, rng)

    if len(trees) > MAX_TREES:
        trees = rng.sample(trees, MAX_TREES)
    if len(humans) > MAX_HUMANS:
        humans = rng.sample(humans, MAX_HUMANS)
    return trees, humans


def _building_placements(road_union, bbox, style, seed):
    """No-OSM only: a realistic street frontage of building models.

    Buildings sit on a consistent setback line, evenly spaced with gaps between
    them, aligned facing the street (small natural jitter only).  When OSM
    footprints exist they are extruded by build_scene, not placed here.
    """
    rng = random.Random(seed + 7)
    bs = style["buildings"]
    lo, hi = bs["scale"]
    placed = []
    ring = _line_ring(road_union, bs["setback"])
    for line in _line_components(ring):
        for x, y, ang in _walk_line(line, bs["spacing"], phase=rng.random()):
            if rng.random() > bs["keep_prob"]:  # occasional empty lot
                continue
            # tiny in/out variation around the frontage line (keeps it natural, not rigid)
            nx, ny = -math.sin(ang), math.cos(ang)
            j = rng.uniform(-bs["setback_jitter"], bs["setback_jitter"])
            bx, by = x + nx * j, y + ny * j
            if not _in_bbox(bx, by, bbox, margin=3.0):
                continue
            yaw = ang + math.pi / 2 + rng.uniform(-bs["yaw_jitter"], bs["yaw_jitter"])
            placed.append({"pos": [bx, by], "yaw": yaw, "size": None, "height": None,
                           "scale": rng.uniform(lo, hi)})
    return placed


def build_scatter(road_polys, buildings, greens, bbox, seed=0, style=None):
    """Return the ``scatter`` dict of prop placements for the scene JSON.

    ``buildings`` (OSM footprints) are NOT placed here when present — build_scene
    extrudes them directly, so ``scatter['buildings']`` is only the no-OSM model
    fallback.  ``greens`` (OSM park/forest footprints) seed in-area trees.
    """
    style = style or SCATTER_STYLE
    road_union = _road_union(road_polys)
    green_polys = _green_polygons(greens, road_union)
    trees, humans = _tree_and_human_placements(road_union, green_polys, bbox, style, seed)
    building_sites = [] if buildings else _building_placements(road_union, bbox, style, seed)
    return {"trees": trees, "humans": humans, "buildings": building_sites}
