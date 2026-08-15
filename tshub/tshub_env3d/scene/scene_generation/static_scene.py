'''
@Author: WANG Maonan
@Date: 2026-07-10
@Description: Static scene geometry helpers for SUMO net -> renderer-ready JSON.

This module keeps the static asset extraction format in one place.  Stage 1
uses tshub/sumolib/shapely to extract roads, lane markings, apron and optional
buildings; Stage 2 (Blender) consumes the returned plain JSON data to write GLB
files.  Keeping this logic separate makes the legacy direct-GLB path optional.
'''
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from shapely.ops import unary_union

from .scene_generation_utils.geometry import triangulate_polygon
from .scene_scatter import build_scatter


def polygon_to_mesh(poly, precision: int = 4):
    """Convert a shapely polygon, including holes, to JSON-safe vertices/faces."""
    verts: List[list] = []
    faces: List[list] = []
    index = {}
    for tri in triangulate_polygon(poly):
        face = []
        for x, y in list(tri.exterior.coords)[:3]:
            key = (round(float(x), precision), round(float(y), precision))
            if key not in index:
                index[key] = len(verts)
                verts.append([float(x), float(y)])
            face.append(index[key])
        if len(set(face)) == 3:
            faces.append(face)
    return verts, faces


def polylines_to_json(lines):
    """Convert line point tuples from sumolib into JSON-safe lists."""
    return [[[float(p[0]), float(p[1])] for p in line] for line in lines]


def _point_back_from_end(shape, distance_back: float):
    """Return a point and heading on a lane shape, measured backward from the end."""
    remaining = distance_back
    for idx in range(len(shape) - 1, 0, -1):
        x1, y1 = shape[idx]
        x0, y0 = shape[idx - 1]
        dx, dy = x1 - x0, y1 - y0
        seg_len = math.hypot(dx, dy)
        if seg_len < 1e-6:
            continue
        if remaining <= seg_len:
            t = (seg_len - remaining) / seg_len
            return (
                [float(x0 + dx * t), float(y0 + dy * t)],
                float(math.atan2(dy, dx)),
            )
        remaining -= seg_len

    x0, y0 = shape[0]
    x1, y1 = shape[1]
    return [float(x0), float(y0)], float(math.atan2(y1 - y0, x1 - x0))


def _movement_direction_to_turn(direction: str) -> str:
    """Map SUMO/tshub movement direction codes to renderer-facing names."""
    return {
        "s": "straight",
        "l": "left",
        "L": "left",
        "r": "right",
        "R": "right",
        "t": "uturn",
        "T": "uturn",
    }.get(direction, "unknown")


def extract_lane_turn_markings(sumo_net, base_distance: float = 9.0) -> list:
    """Extract lane-level turn arrows from SUMO/tshub movement directions.

    Direction codes are the same movement codes used by tshub traffic-light
    helpers (s/l/r/t).  This function only places those existing semantics near
    the end of the incoming lane for visualization.
    """
    turn_order = {"right": 0, "straight": 1, "left": 2, "uturn": 3, "unknown": 4}
    markings = []

    for edge in sumo_net._graph.getEdges():
        if edge.getFunction() == "internal":
            continue

        for lane in edge.getLanes():
            shape = lane.getShape()
            if len(shape) < 2:
                continue

            movement_pairs = [
                (direction, _movement_direction_to_turn(direction))
                for direction in {conn.getDirection() for conn in lane.getOutgoing()}
            ]
            movement_pairs = [
                (direction, turn)
                for direction, turn in movement_pairs
                if turn != "unknown"
            ]
            movement_pairs = sorted(
                movement_pairs,
                key=lambda item: turn_order.get(item[1], turn_order["unknown"]),
            )
            if not movement_pairs:
                continue

            center, heading = _point_back_from_end(shape, base_distance)
            directions = [direction for direction, _turn in movement_pairs]
            turns = [turn for _direction, turn in movement_pairs]
            markings.append(
                {
                    "lane_id": lane.getID(),
                    "movement_direction": "+".join(directions),
                    "movement_directions": directions,
                    "turn": "+".join(turns),
                    "turns": turns,
                    "center": center,
                    "heading": heading,
                    "lane_width": float(lane.getWidth()),
                }
            )
    return markings


def parse_building_heights(heights_csv: str) -> dict:
    """Read building id -> height from a CSV with columns name,cx,cy,sx,sy,sz,yaw."""
    heights = {}
    for line in Path(heights_csv).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 6:
            try:
                heights[parts[0]] = float(parts[5])
            except ValueError:
                pass
    return heights


def _poly_param_height(poly):
    """Read an OSM `<param key="height">` (metres) off a building poly, if present."""
    for param in poly.findall('param'):
        if param.get('key') == 'height':
            try:
                return float(param.get('value'))
            except (TypeError, ValueError):
                return None
    return None


def parse_buildings(poly_xml: str, heights: dict, default_height: float = 12.0) -> list:
    """Read SUMO building polygons and attach a height for each footprint.

    Height priority: the poly's own OSM ``<param key="height">`` (real per-building
    level height), then the id->height CSV, then ``default_height``.
    """
    tree = ET.parse(poly_xml)
    buildings = []
    for poly in tree.getroot().iter('poly'):
        if poly.get('type') != 'building':
            continue
        pts = poly.get('shape', '').split()
        footprint = [[float(c) for c in p.split(',')[:2]] for p in pts if ',' in p]
        if len(footprint) < 3:
            continue
        height = _poly_param_height(poly)
        if height is None:
            height = heights.get(poly.get('id'), default_height)
        buildings.append({'footprint': footprint, 'height': float(height)})
    return buildings


# OSM/polyconvert poly types that are vegetated ground (trees scattered inside).
GREEN_TYPES = {
    'natural', 'forest', 'wood', 'grass', 'meadow', 'scrub', 'park', 'leisure',
    'garden', 'farmland', 'orchard', 'greenfield', 'recreation_ground',
}


def parse_green_areas(poly_xml: str) -> list:
    """Read SUMO green polygons (parks/forests/natural) as footprints for trees."""
    tree = ET.parse(poly_xml)
    greens = []
    for poly in tree.getroot().iter('poly'):
        poly_type = (poly.get('type') or '').split('.')[0]
        if poly_type not in GREEN_TYPES:
            continue
        pts = poly.get('shape', '').split()
        ring = [[float(c) for c in p.split(',')[:2]] for p in pts if ',' in p]
        if len(ring) >= 3:
            greens.append(ring)
    return greens


def build_static_scene_data(
    sumo_net,
    buildings_poly: str = None,
    heights_csv: str = None,
    apron_width: float = 5.0,
) -> dict:
    """Build the plain-data static scene consumed by Blender build_scene.py.

    Args:
        sumo_net: SumoNet3D instance.
        buildings_poly: Optional SUMO buildings.poly.xml path.
        heights_csv: Optional building-height CSV path.
        apron_width: Hardscape apron expansion around roads, in meters.
    """
    road_polys = sumo_net._compute_road_polygons()
    lane_dividers, edge_borders = sumo_net._compute_traffic_dividers()
    bbox = sumo_net.bounding_box

    roads = []
    for poly, _metadata in road_polys:
        verts, faces = polygon_to_mesh(poly)
        if verts and faces:
            roads.append({'vertices': verts, 'faces': faces})

    apron = []
    try:
        road_union = unary_union([p.buffer(0) for p, _ in road_polys])
        road_union = road_union.buffer(apron_width).simplify(0.3)
        geoms = road_union.geoms if road_union.geom_type == 'MultiPolygon' else [road_union]
        for geom in geoms:
            verts, faces = polygon_to_mesh(geom)
            if verts and faces:
                apron.append({'vertices': verts, 'faces': faces})
    except Exception as exc:
        print(f"WARN: apron generation failed, skipped ({exc})")

    bbox_list = [bbox.min_pt.x, bbox.min_pt.y, bbox.max_pt.x, bbox.max_pt.y]
    data = {
        'bbox': bbox_list,
        'roads': roads,
        'apron': apron,
        'lane_dividers': polylines_to_json(lane_dividers),
        'edge_borders': polylines_to_json(edge_borders),
        'turn_markings': extract_lane_turn_markings(sumo_net),
        'buildings': [],
    }
    greens = []
    if buildings_poly:
        heights = parse_building_heights(heights_csv) if heights_csv else {}
        data['buildings'] = parse_buildings(buildings_poly, heights)
        greens = parse_green_areas(buildings_poly)

    # city-builder prop placement.  Buildings: extruded from OSM footprints when
    # present (see build_scene), otherwise decorative models along the road.
    # Trees: inside OSM green areas + along the street; humans: on the verge.
    data['scatter'] = build_scatter(road_polys, data['buildings'], greens, bbox_list)
    return data


def write_static_scene_json(data: dict, out_json: str) -> str:
    """Write static scene data as compact JSON and return the output path."""
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(data))
    return out_json
