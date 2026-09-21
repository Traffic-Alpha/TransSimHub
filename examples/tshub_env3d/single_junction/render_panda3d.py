'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: single_junction 的 Panda3D 在线渲染总览 —— 一条命令看遍各种视角与天空.

这是 Panda 后端 (实时, 每步返回传感器图像) 的演示入口。离线高精度渲染见同目录
render_blender.py; 静态场景由 build_static_scene.py 生成 (必须先跑)。

────────────────────────── 用法 ──────────────────────────
前置: 设好 SUMO_HOME 与 DISPLAY (离屏渲染也需要一个可用的 GL 上下文)。

  # 默认: 2 种天空各跑一次仿真, 每次同时渲 3 个视角
  python examples/tshub_env3d/single_junction/render_panda3d.py

  # 指定视角 / 天空
  python .../render_panda3d.py --view aircraft --sky dust

  # 只要某几个组合 (逗号分隔)
  python .../render_panda3d.py --sky dust --view junction,aircraft --steps 40

参数:
  --view   junction | vehicle | aircraft   (默认: 三个都渲)   支持逗号分隔
  --sky    day | dust                      (默认: 两种都渲)  支持逗号分隔
  --steps  仿真步数                         (默认: 200)

────────────────────────── 三个视角 ──────────────────────────
  junction  相机挂在信号灯上: 4 个路口地面机位 + 1 个全路口俯视 (共 5 台)
  vehicle   相机挂在指定车辆 (E0__0__taxi.0) 上: 前视 + 车载 BEV
            该车不是全程存在, 出发前/驶离后这一视角不出图, 属正常
  aircraft  无人机**悬停在路口正上方** (1545.5, 1009.8, 32m), 不飞行:
            俯视 + 外部跟拍
每个视角都同时出 RGB 与 Seg (语义分割) 两种模态。

────────────────────────── 天空风格 ──────────────────────────
--sky 不只是换天空贴图, 它**同时改变打光** (见 scene_loader.SKY_STYLES):
  day   天空偏蓝, 主光中性略暖
  dust  天空沙黄, 主光变暖变弱、太阳压低 (路面/车辆整体偏暖)

────────────────────────── 输出 ──────────────────────────
  _outputs/panda/<sky>/<view>/<element_id>/<sensor_type>/<step>.png
  seg 图会用调色板上色后再存 (原始输出是单通道 label-id)。

──────────────────── 三个视角一次跑完, 只有天空分进程 ────────────────────
三个视角只是「挂在不同载体上的相机」, 同一个环境可以同时挂 tls + vehicle +
aircraft 的相机, 所以**一次仿真就能把三个视角全渲出来** (省掉重复的场景加载
与 SUMO 启动: 实测每种天空 14.5s -> 7.5s)。返回的 sensor_data 按 sensor_type
反查 rig 的 carrier, 再分回各自的视角目录。

天空则**必须**分进程: 打光是在场景加载时定死的, 而 Panda3D 的 ShowBase 是
**进程级单例** —— 关掉它会直接结束进程, 一个进程里换不了第二套光。
所以主进程只做调度: 每种天空起一个子进程 (自己 + `--_worker views sky steps`),
子进程渲完 os._exit(0)。天空之间串行 (单机单卡并行意义不大, 日志也会交错)。
'''
import os
import sys
import time
import random
import subprocess

import cv2
import numpy as np
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.core import SEG_ID_TO_COLOR, get_camera_rig

path_convert = get_abs_path(__file__)
SCENARIO_GLB_DIR = path_convert("./3d_assets")
OUT_DIR = path_convert("./_outputs")
REQUIRED_SCENE_FILES = ("map.glb", "ground.glb", "road_lines.glb", "lane_lines.glb")

# 无人机: 悬停在路口正上方 (不飞行 —— 看的是俯视/跟拍画面, 移动只会让对比变难)
AIRCRAFT_CENTER = (1545.5, 1009.8) # 路口中心 (= build_tls_rigs 给 J3_bev 算出的停车线质心)
AIRCRAFT_ALTITUDE = 32.0

# 每个视角: 挂哪些传感器 (RGB + SEG), 是否需要飞行器
# 三个视角其实只是「挂在不同载体上的相机」, 可以合并进同一个环境一次跑完.
# carrier 用于把返回的 sensor_data 分回各自的视角目录 (通过 rig 反查, 见 _view_of).
VIEWS = {
    'junction': {
        'carrier': 'tls',
        'elements': {'J3': {
            'sensor_types': ['junction_front_rgb', 'junction_front_seg',
                             'junction_bev_rgb', 'junction_bev_seg'],
            'tls_camera_height': 9,
        }},
    },
    'vehicle': {
        'carrier': 'vehicle',
        'elements': {'E0__0__taxi.0': {
            'sensor_types': ['front_rgb', 'front_seg', 'bev_rgb', 'bev_seg'],
        }},
    },
    'aircraft': {
        'carrier': 'aircraft',
        'elements': {'drone_1': {
            'sensor_types': ['aircraft_rgb', 'aircraft_seg'],
        }},
        'aircraft_inits': {'drone_1': {
            'aircraft_type': 'drone', 'action_type': 'stationary',
            'position': (AIRCRAFT_CENTER[0], AIRCRAFT_CENTER[1], AIRCRAFT_ALTITUDE),
            'speed': 0, 'heading': (0, 1, 0),
            'communication_range': 100, 'if_sumo_visualization': False,
        }},
    },
}
CARRIER_TO_VIEW = {spec['carrier']: name for name, spec in VIEWS.items()}


def _merge_views(views):
    """把若干视角合并成一份 sensor_config (+ 需要的 aircraft_inits)."""
    sensor_config, aircraft_inits = {}, {}
    for name in views:
        spec = VIEWS[name]
        sensor_config.setdefault(spec['carrier'], {}).update(spec['elements'])
        aircraft_inits.update(spec.get('aircraft_inits', {}))
    return sensor_config, (aircraft_inits or None)


def _view_of(sensor_type: str) -> str:
    """由 sensor_type 反查它属于哪个视角 (rig 自带 carrier, 不用猜命名)."""
    return CARRIER_TO_VIEW[get_camera_rig(sensor_type).carrier]


def render_one(views, sky: str = 'day', steps: int = 40) -> None:
    """一次仿真同时渲染给定的所有视角 (它们只是挂在不同载体上的相机)."""
    set_logger(path_convert('./'), terminal_log_level='ERROR')
    random.seed(7)
    sensor_config, aircraft_inits = _merge_views(views)
    env = Tshub3DEnvironment(
        sumo_cfg=path_convert("./sumo_net/single_junction.sumocfg"),
        scenario_glb_dir=SCENARIO_GLB_DIR,
        renderer='panda',
        sky=sky,
        is_map_builder_initialized=False,
        is_vehicle_builder_initialized=True,
        is_aircraft_builder_initialized=aircraft_inits is not None,
        is_traffic_light_builder_initialized=True,
        tls_ids=['J3'],
        aircraft_inits=aircraft_inits,
        vehicle_action_type='lane_continuous_speed',
        use_gui=False, is_libsumo=True,
        num_seconds=120, collision_action="warn", sumo_seed='7',
        preset="720P_SQUARE", render_mode="offscreen", rendering_backend="pandagl",
        sensor_config=sensor_config,
    )
    states = env.reset()
    saved = 0
    start = time.perf_counter()
    for i in range(steps):
        actions = {'vehicle': dict(), 'tls': {'J3': random.randint(0, 3)}}
        if aircraft_inits: # stationary: 动作被忽略, 但接口要求每个 aircraft 都给一个
            actions['aircraft'] = {aid: (0, 0) for aid in aircraft_inits}
        states, _, _, done, sensor_data = env.step(actions)
        for element_id, cameras in sensor_data.items():
            for sensor_type, image in cameras.items():
                # 按视角分目录: 同一次仿真的输出仍然分开存放, 便于对比
                d = os.path.join(OUT_DIR, 'panda', sky, _view_of(sensor_type),
                                 element_id, sensor_type)
                os.makedirs(d, exist_ok=True)
                _save_image(os.path.join(d, f"{i}.png"), image)
                saved += 1
        if done:
            break
    elapsed = time.perf_counter() - start
    print(f"[sky={sky}] views={','.join(views)}: saved {saved} images in {elapsed:.2f}s "
          f"({steps / elapsed:.2f} step/s) -> {os.path.join(OUT_DIR, 'panda', sky)}")
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


def _parse():
    """解析命令行. `--view` / `--sky` 都支持逗号分隔的多值."""
    argv = sys.argv[1:]
    opts = {'view': None, 'sky': None, 'steps': 200}
    worker = None
    i = 0
    while i < len(argv):
        if argv[i] == '--_worker': # 内部用: 子进程渲染一种天空 (视角一次全渲)
            worker = (argv[i + 1], argv[i + 2], int(argv[i + 3])); i += 4
        elif argv[i].lstrip('-').replace('-', '_') in opts:
            key = argv[i].lstrip('-').replace('-', '_')
            opts[key] = argv[i + 1]; i += 2
        else:
            i += 1
    opts['steps'] = int(opts['steps'])
    return worker, opts


def _as_list(value, default):
    """'a,b' -> ['a','b']; None -> default."""
    if not value:
        return list(default)
    return [v.strip() for v in str(value).split(',') if v.strip()]


if __name__ == '__main__':
    worker, opts = _parse()
    if worker: # 子进程: 一种天空, 一次仿真渲完它的所有视角
        views, sky, steps = worker[0].split(','), worker[1], worker[2]
        render_one(views, sky, steps)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0) # Panda 的 ShowBase 关闭会走 userExit, 这里直接退避免噪声

    # 主进程: 只做调度. 视角不用分进程 (同一个环境挂不同载体的相机即可),
    # 只有天空必须分 —— 打光在场景加载时定死, 而 ShowBase 是进程级单例.
    missing_scene_files = [
        name for name in REQUIRED_SCENE_FILES
        if not os.path.exists(os.path.join(SCENARIO_GLB_DIR, name))
    ]
    if missing_scene_files:
        sys.exit(
            f"single_junction 静态场景未生成完整: {SCENARIO_GLB_DIR}\n"
            f"缺失文件: {', '.join(missing_scene_files)}\n"
            "请先运行: python examples/tshub_env3d/single_junction/build_static_scene.py"
        )

    views = _as_list(opts['view'], tuple(VIEWS))
    skies = _as_list(opts['sky'], ('day', 'dust'))
    unknown = set(views) - set(VIEWS)
    if unknown:
        sys.exit(f"未知视角: {', '.join(sorted(unknown))}; 可选: {', '.join(VIEWS)}")

    failures = []
    for sky in skies:
        print(f"=== sky={sky} (views: {', '.join(views)}) ===")
        result = subprocess.run(
            [sys.executable, __file__, '--_worker', ','.join(views), sky, str(opts['steps'])],
            check=False,
        )
        if result.returncode != 0:
            failures.append(sky)
    if failures:
        sys.exit(f"渲染失败: sky={', '.join(failures)}")
    print(f"done. 见 {OUT_DIR}/panda/<sky>/<view>/")
