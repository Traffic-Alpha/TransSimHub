'''
@Author: WANG Maonan
@Date: 2026-08-17
@Description: Build the YMT tshub3d static scene from prepared SUMO net/poly files.

Pipeline:
  1) sumo_network/map.net.xml + sumo_network/add/map.poly.xml -> 3d_assets/scene.json
  2) Blender build_scene.py -> 3d_assets/*.glb
  3) Blender build_blend.py -> 3d_assets/scene.blend

Building footprints and height/levels params are read only from the prepared
map.poly.xml.

Usage:
  python examples/tshub_env3d/ymt_area/build_static_scene.py
  python examples/tshub_env3d/ymt_area/build_static_scene.py --skip-blend
'''
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.scene import export_scene_geometry

path_convert = get_abs_path(__file__)
ROOT = path_convert("./")
NET_FILE = path_convert("./sumo_network/map.net.xml")
POLY_FILE = path_convert("./sumo_network/add/map.poly.xml")
# 生成的文件
SCENE_DIR = path_convert("./3d_assets")
SCENE_JSON = os.path.join(SCENE_DIR, "scene.json")
SCENE_BLEND = os.path.join(SCENE_DIR, "scene.blend")
# 本地 blender 渲染脚本路径
REPO_ROOT = path_convert("../../..")
BUILD_SCENE_SCRIPT = os.path.join(REPO_ROOT, "tshub/tshub_env3d/scene/blender/build_scene.py")
BUILD_BLEND_SCRIPT = os.path.join(REPO_ROOT, "tshub/tshub_env3d/scene/blender/build_blend.py")
DEFAULT_BLENDER = "/home/wmn/blender/blender"
REQUIRED_SCENE_FILES = ("map.glb", "ground.glb", "road_lines.glb", "lane_lines.glb", "buildings.glb")
GENERATED_GLB_FILES = (*REQUIRED_SCENE_FILES, "vegetation.glb", "props.glb")


def find_blender() -> str:
    env_blender = os.environ.get("BLENDER")
    if env_blender:
        if not os.path.exists(env_blender):
            raise FileNotFoundError(f"BLENDER points to a missing executable: {env_blender}")
        return env_blender
    if os.path.exists(DEFAULT_BLENDER):
        return DEFAULT_BLENDER
    blender = shutil.which("blender")
    if blender:
        return blender
    raise FileNotFoundError(
        "Blender is required to build the YMT scene. "
        "Install Blender or set BLENDER=/path/to/blender."
    )


def remove_old_glbs() -> None:
    os.makedirs(SCENE_DIR, exist_ok=True)
    for name in GENERATED_GLB_FILES:
        path = os.path.join(SCENE_DIR, name)
        if os.path.exists(path):
            os.remove(path)


def run_blender(cmd: list, done_token: str) -> None:
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith(("[assembly]", "BUILD_DONE", "BLEND_DONE")):
            print(line)
    if result.returncode != 0 or done_token not in result.stdout:
        print(result.stdout[-3000:])
        print(result.stderr[-3000:])
        raise RuntimeError(f"Blender command failed: {' '.join(cmd[:4])}")


def build_static_scene(skip_blend: bool = False,
                       building_level_height: float = 3.2, style: str = "day",
                       samples: int = 64, resolution: str = "1280x720",
                       engine: str = "CYCLES") -> str:
    os.makedirs(SCENE_DIR, exist_ok=True)

    export_scene_geometry(
        NET_FILE,
        SCENE_JSON,
        buildings_poly=POLY_FILE,
        building_level_height=building_level_height,
    )
    remove_old_glbs()

    blender = find_blender()
    run_blender(
        [
            blender, "--background",
            "--python", BUILD_SCENE_SCRIPT,
            "--",
            SCENE_JSON,
            SCENE_DIR,
        ],
        "BUILD_DONE",
    )

    missing = [
        name for name in REQUIRED_SCENE_FILES
        if not os.path.exists(os.path.join(SCENE_DIR, name))
    ]
    if missing:
        raise RuntimeError(
            f"Blender scene generation did not produce required files: {', '.join(missing)}"
        )

    if not skip_blend:
        run_blender(
            [
                blender, "--background",
                "--python", BUILD_BLEND_SCRIPT,
                "--",
                SCENE_DIR,
                SCENE_BLEND,
                "--style", style,
                "--samples", str(samples),
                "--resolution", resolution,
                "--engine", engine,
            ],
            "BLEND_DONE",
        )

    print(f"YMT glb -> {SCENE_DIR}")
    if not skip_blend:
        print(f"YMT blend -> {SCENE_BLEND}")
    return SCENE_DIR


def parse_args():
    parser = argparse.ArgumentParser(description="Build YMT tshub3d static scene from prepared SUMO net/poly.")
    parser.add_argument("--skip-blend", action="store_true", help="Only build glb files.")
    parser.add_argument("--building-level-height", type=float, default=3.2,
                        help="Metres per OSM building:levels.")
    parser.add_argument("--style", default="day", help="Blender light style for scene.blend.")
    parser.add_argument("--samples", type=int, default=64, help="Cycles samples for scene.blend.")
    parser.add_argument("--resolution", default="1280x720", help="Blend render resolution, e.g. 1280x720.")
    parser.add_argument("--engine", default="CYCLES", help="Blender render engine.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_static_scene(
        skip_blend=args.skip_blend,
        building_level_height=args.building_level_height,
        style=args.style,
        samples=args.samples,
        resolution=args.resolution,
        engine=args.engine,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
