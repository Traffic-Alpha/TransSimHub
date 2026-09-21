'''
@Author: WANG Maonan
@Date: 2026-08-17
@Description: Build the single_junction tshub3d static scene.

Pipeline:
  1) SUMO net.xml -> _blender/scene.json
  2) Blender build_scene.py -> 3d_assets/*.glb
  3) Blender build_blend.py -> 3d_assets/scene.blend  (渲染直接复用它, 只需生成一次)

Usage:
  python examples/tshub_env3d/single_junction/build_static_scene.py
  python examples/tshub_env3d/single_junction/build_static_scene.py --skip-blend
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
NET_FILE = path_convert("./sumo_net/single_junction.net.xml")

# 存储场景 3D 资源
GLB_DIR = path_convert("./3d_assets")
SCENE_JSON = os.path.join(GLB_DIR, "scene.json")
SCENE_BLEND = os.path.join(GLB_DIR, "scene.blend")

# 构建本地脚本路径
REPO_ROOT = path_convert("../../..")
BUILD_SCENE_SCRIPT = os.path.join(REPO_ROOT, "tshub/tshub_env3d/scene/blender/build_scene.py")
BUILD_BLEND_SCRIPT = os.path.join(REPO_ROOT, "tshub/tshub_env3d/scene/blender/build_blend.py")
DEFAULT_BLENDER = "/home/wmn/blender/blender"
REQUIRED_SCENE_FILES = ("map.glb", "ground.glb", "road_lines.glb", "lane_lines.glb")
GENERATED_GLB_FILES = (*REQUIRED_SCENE_FILES, "buildings.glb", "vegetation.glb", "props.glb")


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
        "Blender is required to build tshub3d static scenes. "
        "Install Blender or set BLENDER=/path/to/blender."
    )


def remove_old_glbs() -> None:
    os.makedirs(GLB_DIR, exist_ok=True)
    for name in GENERATED_GLB_FILES:
        path = os.path.join(GLB_DIR, name)
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


def build_static_scene(skip_blend: bool = False, style: str = "day",
                       samples: int = 64, resolution: str = "1280x720",
                       engine: str = "CYCLES") -> str:
    os.makedirs(GLB_DIR, exist_ok=True)
    export_scene_geometry(NET_FILE, SCENE_JSON)

    remove_old_glbs()
    blender = find_blender()
    run_blender(
        [
            blender, "--background",
            "--python", BUILD_SCENE_SCRIPT,
            "--",
            SCENE_JSON,
            GLB_DIR,
        ],
        "BUILD_DONE",
    )

    missing = [
        name for name in REQUIRED_SCENE_FILES
        if not os.path.exists(os.path.join(GLB_DIR, name))
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
                GLB_DIR,
                SCENE_BLEND,
                "--style", style,
                "--samples", str(samples),
                "--resolution", resolution,
                "--engine", engine,
            ],
            "BLEND_DONE",
        )

    print(f"single_junction glb -> {GLB_DIR}")
    if not skip_blend:
        print(f"single_junction blend -> {SCENE_BLEND}")
    return GLB_DIR


def parse_args():
    parser = argparse.ArgumentParser(description="Build single_junction tshub3d static scene.")
    parser.add_argument("--skip-blend", action="store_true", help="Only build glb files.")
    parser.add_argument("--style", default="day", help="Blender light style for scene.blend.")
    parser.add_argument("--samples", type=int, default=64, help="Cycles samples for scene.blend.")
    parser.add_argument("--resolution", default="1280x720", help="Blend render resolution, e.g. 1280x720.")
    parser.add_argument("--engine", default="CYCLES", help="Blender render engine.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_static_scene(
        skip_blend=args.skip_blend,
        style=args.style,
        samples=args.samples,
        resolution=args.resolution,
        engine=args.engine,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
