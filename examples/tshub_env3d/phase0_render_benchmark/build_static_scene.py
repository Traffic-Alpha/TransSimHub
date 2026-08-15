'''
@Author: WANG Maonan
@Date: 2026-07-10
@Description: Build the static GLB scene used by phase0_render_benchmark.

This script intentionally exposes no visual style options.  tshub3d uses a
single city-builder style for Panda3D static assets.

Usage:
  python examples/tshub_env3d/phase0_render_benchmark/build_static_scene.py
'''
import os
import shutil
import subprocess
import sys

from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.scene.scene_generation import export_scene_geometry


path_convert = get_abs_path(__file__)
ROOT = path_convert("./")
SINGLE_JUNCTION = path_convert("../single_junction")
NET_FILE = os.path.join(SINGLE_JUNCTION, "sumo_net/single_junction.net.xml")
SCENE_DIR = os.path.join(ROOT, "_scene")
SCENE_JSON = os.path.join(SCENE_DIR, "scene.json")
GLB_DIR = os.path.join(SCENE_DIR, "glb")
BLENDER_SCRIPT = path_convert("../../../tshub/tshub_env3d/scene/scene_generation/blender/build_scene.py")
DEFAULT_BLENDER = "/home/wmn/blender/blender"
REQUIRED_SCENE_FILES = ("map.glb", "ground.glb", "road_lines.glb", "lane_lines.glb")


def _find_blender():
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
        "Blender is required to build tshub3d static scenes. "
        "Install Blender or set BLENDER=/path/to/blender."
    )


def main():
    os.makedirs(SCENE_DIR, exist_ok=True)
    export_scene_geometry(NET_FILE, SCENE_JSON)
    os.makedirs(GLB_DIR, exist_ok=True)
    for name in (*REQUIRED_SCENE_FILES, "buildings.glb", "vegetation.glb"):
        path = os.path.join(GLB_DIR, name)
        if os.path.exists(path):
            os.remove(path)

    blender = _find_blender()
    subprocess.run(
        [
            blender, "--background",
            "--python", BLENDER_SCRIPT,
            "--",
            SCENE_JSON,
            GLB_DIR,
        ],
        check=True,
    )
    missing = [
        name for name in REQUIRED_SCENE_FILES
        if not os.path.exists(os.path.join(GLB_DIR, name))
    ]
    if missing:
        raise RuntimeError(
            f"Blender scene generation did not produce required files: {', '.join(missing)}"
        )
    print(f"phase0 static scene -> {GLB_DIR}")


if __name__ == "__main__":
    sys.exit(main())
