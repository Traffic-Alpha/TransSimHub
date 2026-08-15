'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 油麻地 (YMT) 无人机穿城 —— 地面车辆行驶, 无人机在城市中飞行, 用机载相机逐帧渲染.
机载相机同时输出俯视 (aircraft_all) 与前下斜视 FPV (aircraft_front_*, 穿梭于建筑之间).

场景 (道路 + 建筑 + 树木 + 路边行人) 由 scene_generation 流水线自动构建到 ./scene_env:
从 SUMO net 提取道路/车道线, 按 OSM footprint 挤出真实尺寸+真实层高 (<param height>)
的 city-builder 多色建筑, 并沿路/公园放置树木、路边成组行人. 首次运行 (或 --rebuild)
会自动执行两步:
  1) scene_export : map.net.xml + buildings.poly.xml -> scene_env/scene.json
  2) Blender build_scene.py : scene.json -> scene_env/*.glb (map/ground/road_lines/
     lane_lines/buildings/vegetation/humans)
需要 Blender (默认 /home/wmn/blender/blender, 或用环境变量 BLENDER 指定).

运行 (需 SUMO_HOME 与 DISPLAY):
  python examples/tshub_env3d/yaumatei_drone/render_ymt_drone.py            # Panda 后端
  python examples/tshub_env3d/yaumatei_drone/render_ymt_drone.py --rebuild # 强制重建场景
输出: _outputs_drone/<renderer>/<sensor_type>/<step>.png (*_all=RGB, *_vehicle=mask)

无人机用 horizontal_movement 沿东西向道路走廊匀速穿城 (高度处于建筑之间), 机载相机
同时俯视与前下斜视; SUMO 跑车辆与默认信号灯, 画面里能看到车辆移动 + 无人机穿行的位移感.
@LastEditTime: 2026-07-11 00:00:00
'''
import os
import sys
import shutil
import subprocess

import cv2
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.scene.scene_generation import export_scene_geometry

path_convert = get_abs_path(__file__)
SCENARIO_GLB_DIR = path_convert("./scene_env")
OUT_DIR = path_convert("./_outputs_drone")
NET_FILE = path_convert("./map.net.xml")
BUILDINGS_POLY = path_convert("./buildings.poly.xml")  # OSM 建筑轮廓 (含 <param height>)
SCENE_JSON = os.path.join(SCENARIO_GLB_DIR, "scene.json")
BLENDER_SCRIPT = path_convert("../../../tshub/tshub_env3d/scene/scene_generation/blender/build_scene.py")
DEFAULT_BLENDER = "/home/wmn/blender/blender"


def _find_blender() -> str:
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
        "Blender is required to build the YMT scene. Install Blender or set BLENDER=/path/to/blender."
    )


def build_ymt_scene() -> None:
    """用 scene_generation 流水线从 SUMO net + OSM 建筑构建静态场景 glb (两步)."""
    os.makedirs(SCENARIO_GLB_DIR, exist_ok=True)
    export_scene_geometry(NET_FILE, SCENE_JSON, buildings_poly=BUILDINGS_POLY)
    subprocess.run(
        [_find_blender(), "--background", "--python", BLENDER_SCRIPT,
         "--", SCENE_JSON, SCENARIO_GLB_DIR],
        check=True,
    )
    print(f"YMT scene built -> {SCENARIO_GLB_DIR}")

# 无人机: 沿东西向道路走廊 (y~694) 向东匀速飞行, 高度处于建筑之间 (FPV 穿梭感)
DRONE_INITS = {
    'drone_1': {
        'aircraft_type': 'drone', 'action_type': 'horizontal_movement',
        'position': (500.0, 694.0, 80.0), 'speed': 0.0, 'heading': (1, 0, 0),
        'communication_range': 100, 'if_sumo_visualization': False,
    }
}
WARMUP = 60  # 先让 SUMO 跑一会, 车辆变多后再开始采集
N_STEPS = 30
DRONE_ACTION = (22, 0)  # (speed, heading_index): heading_index=0 -> 0° 正东, 沿道路走廊
# 机载相机: 俯视 + 前下斜视 FPV + 外部跟拍 + FPV mask
DRONE_SENSORS = ['aircraft_rgb', 'aircraft_front_rgb', 'aircraft_chase_rgb', 'aircraft_front_seg']


def render_with(renderer: str) -> None:
    set_logger(path_convert('./'), terminal_log_level='ERROR')
    env = Tshub3DEnvironment(
        sumo_cfg=path_convert("./env.sumocfg"),
        scenario_glb_dir=SCENARIO_GLB_DIR,
        renderer=renderer, sky='day',
        is_map_builder_initialized=False,
        is_vehicle_builder_initialized=True,        # 地面车辆
        is_aircraft_builder_initialized=True,        # 无人机
        is_traffic_light_builder_initialized=False,  # 信号灯交给 SUMO 默认配时
        aircraft_inits=DRONE_INITS,
        vehicle_action_type='lane',
        use_gui=False, num_seconds=400, collision_action="warn",
        preset="720P", render_mode="offscreen",
        sensor_config={'aircraft': {'drone_1': {'sensor_types': DRONE_SENSORS}}},
    )
    env.reset()
    # 预热: 无人机悬停, 让 SUMO 多跑一会积累车辆
    for _ in range(WARMUP):
        env.step({'vehicle': dict(), 'aircraft': {'drone_1': (0, 0)}})
    out = os.path.join(OUT_DIR, renderer)
    for i in range(N_STEPS):
        _, _, _, done, sensor_data = env.step(
            {'vehicle': dict(), 'aircraft': {'drone_1': DRONE_ACTION}}
        )
        for element_id, cameras in sensor_data.items():
            for sensor_type, image in cameras.items():
                d = os.path.join(out, sensor_type)
                os.makedirs(d, exist_ok=True)
                cv2.imwrite(os.path.join(d, f"{i:02d}.png"), image[:, :, ::-1])
        if done:
            break
    env.close()
    print(f"[{renderer}] drone fly-through saved -> {out}")


if __name__ == '__main__':
    if '--renderer' in sys.argv:
        i = sys.argv.index('--renderer')
        if i + 1 < len(sys.argv) and sys.argv[i + 1] != '--_worker':
            renderers = [sys.argv[i + 1]]
        else:
            renderers = None
    else:
        renderers = None

    if '--_worker' in sys.argv:
        render_with(sys.argv[sys.argv.index('--_worker') + 1])
    else:
        # 首次运行 (或 --rebuild) 用 scene_generation 流水线自动构建场景 glb
        if '--rebuild' in sys.argv or not os.path.exists(os.path.join(SCENARIO_GLB_DIR, "map.glb")):
            build_ymt_scene()
        for r in (renderers or ['panda']):
            print(f"=== {r} ===")
            subprocess.run([sys.executable, __file__, '--_worker', r], check=False)
        print(f"done. 见 {OUT_DIR}/<renderer>/")
