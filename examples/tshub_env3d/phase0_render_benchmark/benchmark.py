'''
@Author: WANG Maonan
@Date: 2026-07-10 00:00:00
@Description: Phase 0 —— tshub_env3d (Panda 后端) 渲染基准 + 冒烟测试.

作用: 在动任何重构之前, 建立一条可复现的基线, 让后续每个重构阶段都能验证
「性能是否改善 / 画面是否保持不变」.

它做三件事:
1. 分段计时: 每个 step 拆成 SUMO 前进 (tshub_env.step) 与 渲染读回 (tshub_render.sync),
   报告 mean / median / p95 与 FPS.
2. 相机数量扫描: 对同一辆车挂 1/2/4/6 个相机, 观察渲染耗时随相机数如何增长
   —— 若明显超线性, 即坐实了 wait_for_ram_image 里 O(N^2) 的重复 renderFrame.
3. 视觉回归基准: 每个配置保存首帧/末帧 PNG 到 _outputs/<config>/, 重构后再跑一次对比即可.

复用 single_junction 的场景与 sumocfg (不重复放资产).

用法 (需 tshub 环境: SUMO_HOME + DISPLAY):
  python examples/tshub_env3d/phase0_render_benchmark/benchmark.py
  python .../benchmark.py --config vehicle_6cam        # 只跑某个配置
  python .../benchmark.py --steps 80 --warmup 25        # 自定步数

输出:
  _outputs/<config>/<element>/<sensor_type>/{first,last}.png   # 视觉回归
  _outputs/report.json  +  终端表格                            # 性能报告

注: Panda 关闭时 ShowBase 会退出进程, 故每个配置在独立子进程中跑 (与 render_single_junction 一致).
'''
import os
import sys
import csv
import json
import time
import shutil
import random
import subprocess
from statistics import mean, median

import cv2
import numpy as np
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.scene import SEG_ID_TO_COLOR

path_convert = get_abs_path(__file__)

# 复用 single_junction 的场景 (不重复放资产)
_SJ = path_convert("../single_junction")
_phase0_scene_dir = path_convert("./_scene/glb")
SCENARIO_GLB_DIR = _phase0_scene_dir
SUMOCFG = os.path.join(_SJ, "sumo_net/single_junction.sumocfg")
OUT_DIR = path_convert("./_outputs")
REQUIRED_SCENE_FILES = ("map.glb", "ground.glb", "road_lines.glb", "lane_lines.glb")
RENDER_PRESET = "720P_SQUARE"

# 挂在同一辆车上、逐步增加相机数量的配置 (用于暴露相机数量对渲染耗时的影响)
_VEH_ID = 'E0__0__taxi.0'  # 与 render_single_junction 一致
_VEH_SENSORS = ['front_rgb', 'back_rgb', 'front_left_rgb', 'front_right_rgb',
                'back_left_rgb', 'back_right_rgb']
_DRONE_INIT = {'drone_1': {  # 悬停在路口上方的无人机 (与 render_single_junction 一致)
    'aircraft_type': 'drone', 'action_type': 'stationary',
    'position': (1557, 989, 80), 'speed': 0, 'heading': (1, 0, 0),
    'communication_range': 100, 'if_sumo_visualization': False,
}}

CONFIGS = {
    # --- 计时: 车载 1/2/4/6 相机 (同车同场景, 只变相机数) ---
    'vehicle_1cam': {'carrier': 'vehicle', 'id': _VEH_ID, 'sensors': _VEH_SENSORS[:1]},
    'vehicle_2cam': {'carrier': 'vehicle', 'id': _VEH_ID, 'sensors': _VEH_SENSORS[:2]},
    'vehicle_4cam': {'carrier': 'vehicle', 'id': _VEH_ID, 'sensors': _VEH_SENSORS[:4]},
    'vehicle_6cam': {'carrier': 'vehicle', 'id': _VEH_ID, 'sensors': _VEH_SENSORS[:6]},
    'junction': {'carrier': 'tls', 'id': 'J3',
                 'sensors': ['junction_front_rgb'], 'tls_camera_height': 9},
    # --- 回归: 覆盖全部相机类型 + rgb/seg 两种模态 ---
    'vehicle_all': {'carrier': 'vehicle', 'id': _VEH_ID,
                    'sensors': ['front_rgb', 'front_left_rgb', 'front_right_rgb',
                                'back_rgb', 'back_left_rgb', 'back_right_rgb',
                                'bev_rgb', 'front_seg', 'bev_seg']},
    'junction_all': {'carrier': 'tls', 'id': 'J3', 'tls_camera_height': 9,
                     'sensors': ['junction_front_rgb', 'junction_back_rgb', 'junction_front_seg']},
    'aircraft_all': {'carrier': 'aircraft', 'id': 'drone_1', 'aircraft_inits': _DRONE_INIT,
                     'sensors': ['aircraft_rgb', 'aircraft_front_rgb', 'aircraft_chase_rgb',
                                 'aircraft_seg']},
    'junction_bev': {'carrier': 'tls', 'id': 'J3', 'junction_bev_height': 60,
                     'sensors': ['junction_bev_rgb', 'junction_bev_seg']},
}


def _pctl(values, q):
    """简单的分位数 (无 numpy 依赖)."""
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((len(s) - 1) * q))))
    return s[k]


def _build_sensor_config(cfg):
    carrier, cid = cfg['carrier'], cfg['id']
    entry = {'sensor_types': cfg['sensors']}
    if carrier == 'tls':
        entry['tls_camera_height'] = cfg.get('tls_camera_height', 9)
        if 'junction_bev_height' in cfg:
            entry['junction_bev_height'] = cfg['junction_bev_height']
    return {carrier: {cid: entry}}


def run_config(name, steps, warmup):
    """在子进程中跑单个配置, 结果写入 _outputs/<name>/_metrics.json."""
    set_logger(path_convert('./'), terminal_log_level='ERROR')
    random.seed(7)
    cfg = CONFIGS[name]
    out_root = os.path.join(OUT_DIR, name)
    if os.path.isdir(out_root):
        shutil.rmtree(out_root)

    env = Tshub3DEnvironment(
        sumo_cfg=SUMOCFG,
        scenario_glb_dir=SCENARIO_GLB_DIR,
        renderer='panda',
        sky='day',
        is_map_builder_initialized=False,
        is_vehicle_builder_initialized=True,
        is_aircraft_builder_initialized=cfg.get('aircraft_inits') is not None,
        aircraft_inits=cfg.get('aircraft_inits'),
        is_traffic_light_builder_initialized=True,
        tls_ids=['J3'],
        vehicle_action_type='lane_continuous_speed',
        use_gui=False, is_libsumo=True,
        num_seconds=600, collision_action="warn", sumo_seed='7',
        preset=RENDER_PRESET, render_mode="offscreen", rendering_backend="pandagl",
        sensor_config=_build_sensor_config(cfg),
    )

    # --- 非侵入式分段计时: 包裹 tshub_env.step (SUMO) 与 tshub_render.sync (渲染读回) ---
    seg = {'sumo': 0.0, 'render': 0.0}
    _orig_sumo = env.tshub_env.step
    _orig_sync = env.tshub_render.sync

    def timed_sumo(*a, **k):
        t = time.perf_counter(); r = _orig_sumo(*a, **k); seg['sumo'] = time.perf_counter() - t; return r

    def timed_sync(*a, **k):
        t = time.perf_counter(); r = _orig_sync(*a, **k); seg['render'] = time.perf_counter() - t; return r

    env.tshub_env.step = timed_sumo
    env.tshub_render.sync = timed_sync

    env.reset()

    _air_inits = cfg.get('aircraft_inits')
    def _actions():
        a = {'vehicle': dict(), 'tls': {'J3': random.randint(0, 3)}}
        if _air_inits:
            a['aircraft'] = {aid: (0, 0) for aid in _air_inits}  # 悬停
        return a

    # 预热: 跑到目标载体的相机真正出现 (车辆需要先 spawn), 最多 warmup + 200 步
    n_cameras = 0
    for _ in range(warmup + 200):
        _, _, _, done, sensor_data = env.step(_actions())
        n_cameras = sum(len(cams) for cams in sensor_data.values())
        if n_cameras > 0:  # 载体已出现, 相机已挂载
            break
        if done:
            break

    # 正式计时: 每步记录 (total, sumo, render, 活跃相机数).
    # 注意: 车辆会中途离场, 之后的步没有相机 —— 若不加区分会污染中位数.
    # 因此只对「相机满载」(活跃相机数 == 峰值) 的步聚合计时.
    samples = []  # (total_ms, sumo_ms, render_ms, n_active)
    for i in range(steps):
        t0 = time.perf_counter()
        _, _, _, done, sensor_data = env.step(_actions())
        total = (time.perf_counter() - t0) * 1e3  # 计时窗口只包住 env.step
        n_active = sum(len(cams) for cams in sensor_data.values()) if sensor_data else 0
        samples.append((total, seg['sumo'] * 1e3, seg['render'] * 1e3, n_active))
        # 逐帧保存 (在计时窗口之外, 不污染时间). 按步号命名 -> 两次运行同种子可逐帧对齐比较.
        _save_frames(sensor_data, out_root, f"{i:04d}")
        if done:
            break

    peak = max((s[3] for s in samples), default=0)
    kept = [s for s in samples if s[3] == peak] if peak > 0 else samples
    n_cameras = peak
    t_total = [s[0] for s in kept]
    t_sumo = [s[1] for s in kept]
    t_render = [s[2] for s in kept]

    metrics = {
        'config': name,
        'n_cameras': n_cameras,
        'steps_measured': len(t_total),  # 满载 (峰值相机数) 的步数
        'steps_total': len(samples),     # 总步数 (含车辆离场后的空场景步)
        'sumo_ms': _stats(t_sumo),
        'render_ms': _stats(t_render),
        'total_ms': _stats(t_total),
        'fps': (1000.0 / mean(t_total)) if t_total else 0.0,
    }
    # 注意: 必须在 env.close() 之前写出 —— Panda 的 userExit() 会 sys.exit() 结束进程.
    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, '_metrics.json'), 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[{name}] cameras={n_cameras}  total={metrics['total_ms']['median']:.1f}ms "
          f"(sumo={metrics['sumo_ms']['median']:.1f} render={metrics['render_ms']['median']:.1f})  "
          f"fps={metrics['fps']:.1f}  [满载 {len(t_total)}/{len(samples)} 步]")
    sys.stdout.flush()

    try:
        env.close()  # Panda userExit() 会 sys.exit(), 属正常结束
    except SystemExit:
        pass


def _stats(v):
    return {
        'mean': round(mean(v), 2) if v else 0.0,
        'median': round(median(v), 2) if v else 0.0,
        'p95': round(_pctl(v, 0.95), 2),
        'max': round(max(v), 2) if v else 0.0,
    }


def _save_frames(sensor_data, out_root, tag):
    for element_id, cameras in (sensor_data or {}).items():
        for sensor_type, image in cameras.items():
            d = os.path.join(out_root, element_id, sensor_type)
            os.makedirs(d, exist_ok=True)
            if image.ndim == 2:  # seg label-id (H,W): 按调色板上色再存 (便于目视)
                color = np.zeros((*image.shape, 3), np.uint8)
                for _id, _c in SEG_ID_TO_COLOR.items():
                    color[image == _id] = _c  # RGB
                cv2.imwrite(os.path.join(d, f"{tag}.png"), color[:, :, ::-1])
            else:
                cv2.imwrite(os.path.join(d, f"{tag}.png"), image[:, :, ::-1])


def _aggregate_and_report():
    rows = []
    for name in CONFIGS:
        p = os.path.join(OUT_DIR, name, '_metrics.json')
        if os.path.exists(p):
            with open(p) as f:
                rows.append(json.load(f))
    if not rows:
        print("没有任何配置成功产出 metrics.")
        return

    # 终端表格
    print(f"\n==================== Phase 0 渲染基准 (Panda / {RENDER_PRESET} offscreen) ====================")
    hdr = f"{'config':<14}{'cams':>5}{'total_ms(med)':>15}{'sumo_ms':>10}{'render_ms':>11}{'render/cam':>12}{'fps':>8}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        cams = r['n_cameras'] or 1
        rpc = r['render_ms']['median'] / cams
        print(f"{r['config']:<14}{r['n_cameras']:>5}{r['total_ms']['median']:>15.1f}"
              f"{r['sumo_ms']['median']:>10.1f}{r['render_ms']['median']:>11.1f}"
              f"{rpc:>12.1f}{r['fps']:>8.1f}")
    print("\n提示: 若 render_ms 随 cams 明显超线性增长 (render/cam 递增), 即坐实 O(N^2) 重复 renderFrame.")

    report = {
        'meta': {
            'preset': RENDER_PRESET, 'render_mode': 'offscreen', 'renderer': 'panda',
            'rendering_backend': 'pandagl',
            'scenario_glb_dir': SCENARIO_GLB_DIR,
            'git_commit': _git_commit(),
        },
        'configs': rows,
    }
    with open(os.path.join(OUT_DIR, 'report.json'), 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n报告: {os.path.join(OUT_DIR, 'report.json')}   视觉回归图: {OUT_DIR}/<config>/")


def _git_commit():
    try:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                       cwd=path_convert('./')).decode().strip()
    except Exception:
        return 'unknown'


def _parse():
    argv = sys.argv[1:]
    config = None
    steps, warmup = 120, 20  # 100~200 步取中位数, 统计更稳 (少受 GC/调度抖动影响)
    worker = False
    i = 0
    while i < len(argv):
        if argv[i] == '--_worker':
            worker = True; config = argv[i + 1]; i += 2
        elif argv[i] == '--config':
            config = argv[i + 1]; i += 2
        elif argv[i] == '--steps':
            steps = int(argv[i + 1]); i += 2
        elif argv[i] == '--warmup':
            warmup = int(argv[i + 1]); i += 2
        else:
            i += 1
    return worker, config, steps, warmup


if __name__ == '__main__':
    worker, config, steps, warmup = _parse()
    if worker:  # 子进程: 跑单个配置
        run_config(config, steps, warmup)
    else:  # 主进程: 每个配置一个独立子进程 (Panda 关闭会退出进程)
        missing_scene_files = [
            name for name in REQUIRED_SCENE_FILES
            if not os.path.exists(os.path.join(SCENARIO_GLB_DIR, name))
        ]
        if missing_scene_files:
            sys.exit(
                f"phase0 静态场景未生成完整: {SCENARIO_GLB_DIR}\n"
                f"缺失文件: {', '.join(missing_scene_files)}\n"
                "请先运行: python examples/tshub_env3d/phase0_render_benchmark/build_static_scene.py"
            )
        names = [config] if config else list(CONFIGS)
        failures = []
        for name in names:
            print(f"=== 运行配置: {name} (steps={steps}, warmup={warmup}) ===")
            result = subprocess.run(
                [sys.executable, __file__, '--_worker', name, '--steps', str(steps), '--warmup', str(warmup)],
                check=False,
            )
            if result.returncode != 0:
                failures.append(name)
        if failures:
            sys.exit(f"配置运行失败: {', '.join(failures)}")
        _aggregate_and_report()
