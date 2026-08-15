'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: single_junction 渲染总览 —— 一键查看不同渲染效果.

覆盖矩阵: 三种视角 (junction / vehicle / aircraft) × RGB 输出. 后端: Panda3D.

用法 (需 SUMO_HOME 与 DISPLAY):
  # 渲染全部组合 (推荐):
  python examples/tshub_env3d/single_junction/render_single_junction.py
  # 指定视角:
  python .../render_single_junction.py --view aircraft
输出: _outputs/<renderer>/<view>/<element>/<sensor_type>/<step>.png

场景目录复用 phase0_render_benchmark 生成的 city-builder 静态场景;
若未生成则直接报错, 避免悄悄回退到旧样式资产.

注: panda 关闭时 ShowBase 会退出进程, 故每个 (后端,视角) 组合在独立子进程中渲染.
@LastEditTime: 2026-06-01 00:00:00
'''
import os
import sys
import time
import math
import random
import subprocess

import cv2
import numpy as np
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.scene import SEG_ID_TO_COLOR

path_convert = get_abs_path(__file__)
SCENARIO_GLB_DIR = path_convert("../phase0_render_benchmark/_scene/glb")
OUT_DIR = path_convert("./_outputs")
REQUIRED_SCENE_FILES = ("map.glb", "ground.glb", "road_lines.glb", "lane_lines.glb")
AIRCRAFT_ORBIT_CENTER = (1557.0, 989.0)
AIRCRAFT_ORBIT_RADIUS = 45.0
AIRCRAFT_ORBIT_SPEED = 8.0
AIRCRAFT_ORBIT_ALTITUDE = 32.0

# 每个视角: 挂哪些传感器 (RGB + SEG), 是否需要飞行器
VIEWS = {
    'junction': {
        'sensor_config': {'tls': {'J3': {
            'sensor_types': ['junction_front_rgb', 'junction_front_seg', 'junction_bev_rgb', 'junction_bev_seg'],
            'tls_camera_height': 9,
        }}},
        'aircraft_inits': None,
    },
    'vehicle': {
        'sensor_config': {'vehicle': {'E0__0__taxi.0': {
            'sensor_types': ['front_rgb', 'front_seg', 'bev_rgb', 'bev_seg'],
        }}},
        'aircraft_inits': None,
    },
    'aircraft': {
        'sensor_config': {'aircraft': {'drone_1': {
            'sensor_types': ['aircraft_rgb', 'aircraft_chase_rgb', 'aircraft_seg'],
        }}},
        'aircraft_inits': {'drone_1': {
            'aircraft_type': 'drone', 'action_type': 'horizontal_movement',
            'position': (AIRCRAFT_ORBIT_CENTER[0] + AIRCRAFT_ORBIT_RADIUS,
                         AIRCRAFT_ORBIT_CENTER[1], AIRCRAFT_ORBIT_ALTITUDE),
            'speed': AIRCRAFT_ORBIT_SPEED, 'heading': (0, 1, 0),
            'communication_range': 100, 'if_sumo_visualization': False,
        }},
    },
}


def render_one(renderer: str, view: str, sky: str = 'day', steps: int = 40) -> None:
    set_logger(path_convert('./'), terminal_log_level='ERROR')
    random.seed(7)
    cfg = VIEWS[view]
    env = Tshub3DEnvironment(
        sumo_cfg=path_convert("./sumo_net/single_junction.sumocfg"),
        scenario_glb_dir=SCENARIO_GLB_DIR,
        renderer=renderer,
        sky=sky,
        is_map_builder_initialized=False,
        is_vehicle_builder_initialized=True,
        is_aircraft_builder_initialized=cfg['aircraft_inits'] is not None,
        is_traffic_light_builder_initialized=True,
        tls_ids=['J3'],
        aircraft_inits=cfg['aircraft_inits'],
        vehicle_action_type='lane_continuous_speed',
        use_gui=False, is_libsumo=True,
        num_seconds=120, collision_action="warn", sumo_seed='7',
        preset="720P_SQUARE", render_mode="offscreen", rendering_backend="pandagl",
        sensor_config=cfg['sensor_config'],
    )
    states = env.reset()
    out = os.path.join(OUT_DIR, renderer, sky, view)
    saved = 0
    start = time.perf_counter()
    for i in range(steps):
        actions = {'vehicle': dict(), 'tls': {'J3': random.randint(0, 3)}}
        if cfg['aircraft_inits']:
            actions['aircraft'] = _orbit_aircraft_actions(states, cfg['aircraft_inits'])
        states, _, _, done, sensor_data = env.step(actions)
        for element_id, cameras in sensor_data.items():
            for sensor_type, image in cameras.items():
                d = os.path.join(out, element_id, sensor_type)
                os.makedirs(d, exist_ok=True)
                _save_image(os.path.join(d, f"{i}.png"), image)
                saved += 1
        if done:
            break
    elapsed = time.perf_counter() - start
    print(f"[{renderer}/{view}] saved {saved} images in {elapsed:.2f}s "
          f"({steps / elapsed:.2f} step/s) -> {out}")
    try:
        env.close()
    except SystemExit:
        pass


def _save_image(path: str, image) -> None:
    if image.ndim == 2:
        color = np.zeros((*image.shape, 3), np.uint8)
        for label_id, rgb in SEG_ID_TO_COLOR.items():
            color[image == label_id] = rgb
        cv2.imwrite(path, color[:, :, ::-1])
        return
    cv2.imwrite(path, image[:, :, ::-1])


def _orbit_aircraft_actions(states, aircraft_inits):
    """让 aircraft 以 8 方向离散动作绕路口飞行."""
    aircraft_states = states.get('aircraft', {}) if states else {}
    actions = {}
    for aid, init_info in aircraft_inits.items():
        aircraft_info = aircraft_states.get(aid, init_info)
        x, y, _ = aircraft_info['position']
        heading_index = _orbit_heading_index(
            position=(x, y),
            center=AIRCRAFT_ORBIT_CENTER,
            radius=AIRCRAFT_ORBIT_RADIUS,
        )
        actions[aid] = (AIRCRAFT_ORBIT_SPEED, heading_index)
    return actions


def _orbit_heading_index(position, center, radius):
    """计算最接近圆形绕飞切向的 horizontal_movement heading index."""
    dx = position[0] - center[0]
    dy = position[1] - center[1]
    dist = max(math.hypot(dx, dy), 1e-6)
    radial_x, radial_y = dx / dist, dy / dist

    # 逆时针切向 + 半径修正: 半径过大则向内, 过小则向外。
    tangent_x, tangent_y = -radial_y, radial_x
    radial_error = (dist - radius) / radius
    correction = max(-0.75, min(0.75, radial_error))
    vx = tangent_x - correction * radial_x
    vy = tangent_y - correction * radial_y

    angle_deg = math.degrees(math.atan2(vy, vx)) % 360
    return int(round(angle_deg / 45.0)) % 8


def _parse():
    argv = sys.argv[1:]
    renderer = view = None
    sky = 'day'
    steps = 200
    worker = False
    i = 0
    while i < len(argv):
        if argv[i] == '--_worker':
            worker, renderer, view, sky, steps = True, argv[i + 1], argv[i + 2], argv[i + 3], int(argv[i + 4]); i += 5
        elif argv[i] == '--renderer':
            renderer = argv[i + 1]; i += 2
        elif argv[i] == '--view':
            view = argv[i + 1]; i += 2
        elif argv[i] == '--sky':
            sky = argv[i + 1]; i += 2
        elif argv[i] == '--steps':
            steps = int(argv[i + 1]); i += 2
        else:
            i += 1
    return worker, renderer, view, sky, steps


if __name__ == '__main__':
    worker, renderer, view, sky, steps = _parse()
    if worker: # 子进程: 渲染单个组合
        render_one(renderer, view, sky, steps)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
    else: # 主进程: 按需对组合各开一个子进程 (相互隔离)
        missing_scene_files = [
            name for name in REQUIRED_SCENE_FILES
            if not os.path.exists(os.path.join(SCENARIO_GLB_DIR, name))
        ]
        if missing_scene_files:
            sys.exit(
                f"single_junction 静态场景未生成完整: {SCENARIO_GLB_DIR}\n"
                f"缺失文件: {', '.join(missing_scene_files)}\n"
                "请先运行: python examples/tshub_env3d/phase0_render_benchmark/build_static_scene.py"
            )
        renderers = [renderer] if renderer else ['panda']
        views = [view] if view else ['junction', 'vehicle', 'aircraft']
        failures = []
        for r in renderers:
            for v in views:
                print(f"=== {r} / {v} / sky={sky} ===")
                result = subprocess.run(
                    [sys.executable, __file__, '--_worker', r, v, sky, str(steps)],
                    check=False,
                )
                if result.returncode != 0:
                    failures.append(f"{r}/{v}")
        if failures:
            sys.exit(f"渲染失败: {', '.join(failures)}")
        print(f"done. 见 {OUT_DIR}/<renderer>/{sky}/<view>/")
