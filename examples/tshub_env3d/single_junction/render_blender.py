'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: single_junction 的 Blender/Cycles 高精度离线渲染.

与 render_panda3d.py 的分工: Panda 是在线后端 (每步出图, 快而糙),
这里是离线后端 (Cycles 路径追踪, 慢而真). 两者共用同一套相机 rig 与语义类别.

────────────────────────── 前置 ──────────────────────────
静态场景**只需生成一次**, 由 build_static_scene.py 完成 (产出 3d_assets/*.glb
与 3d_assets/scene.blend). 本脚本不再生成场景, 直接复用那个 .blend:

    python examples/tshub_env3d/single_junction/build_static_scene.py   # 只跑一次

还需要 SUMO_HOME; Blender 默认 /home/wmn/blender/blender, 或用环境变量 BLENDER 指定.

────────────────────────── 用法 ──────────────────────────
  # 默认: 一次仿真挂齐三类相机, 渲 day/clear
  python examples/tshub_env3d/single_junction/render_blender.py

  # 扫描打光 x 天气 (逗号分隔, 复用同一份剧集与同一个 .blend)
  python .../render_blender.py --style day,golden,dusk --weather clear,rain
  python ./render_blender.py --style day,golden,dusk --weather clear,rain,fog --passes rgb,seg,depth

  # 只出某一个通道 (通道之间互相独立, 不写 rgb 就不会渲 rgb)
  python .../render_blender.py --passes seg
  python .../render_blender.py --passes depth

  # 出多个通道: 默认**每个通道各起一次 Blender**, 比一次跑多个通道快 (见下)
  python .../render_blender.py --passes rgb,seg,depth

参数:
  --style      day | noon | golden | dusk | overcast   (默认 day)     支持逗号分隔
  --weather    clear | fog | rain                      (默认 clear)   支持逗号分隔
  --passes     rgb | seg | depth 的任意组合            (默认 rgb)     支持逗号分隔
  --fused-passes                       多通道挤在同一次 Blender 里渲 (默认分开跑, 见下)
  --steps      仿真步数 (默认 100)      --every  每隔几步渲一帧 (默认 1)
  --samples    Cycles 采样数 (默认 64) --resolution  默认 720x720
  --export-only / --render-only        只导出剧集 / 跳过导出直接渲
  --force-export                       强制重导剧集 (默认: 参数没变就复用)

────────────────────── 为什么通道要分开跑 ──────────────────────
实测 (101 帧 x 1 个路口 BEV 相机, 1022x1022, samples=8, Cycles GPU/4090):
    rgb  143.1s | seg  47.7s | 分开跑合计 190.8s
    `--passes rgb,seg` 挤在一次里跑: 302.9s —— 贵 59%
rgb 与 seg 交替渲染时, 每次渲染看到的 material_override 都不一样, Cycles 的
use_persistent_data 缓存每渲一次就失效一次, 两个通道都要付全量场景重导出;
Blender 启动 + 加载 scene.blend 只要约 1.5s, 分开跑那点开销可以忽略.
所以这里默认按通道分次调用 Blender; --fused-passes 保留旧行为 (便于对照).

────────────────────────── 相机 ──────────────────────────
一次仿真同时挂三类载体的相机 (与 Panda 侧一致, 不再每个视角跑一遍仿真):
  路口 (tls)      J3 的 4 个地面机位 + 1 个全路口俯视
  车辆 (vehicle)  E0__0__taxi.0 的前视 + 车载 BEV (该车驶离后自然不再出图)
  无人机 (aircraft) 悬停在路口正上方 (1545.5, 1009.8, 32m), 不飞行: 俯视 + 外部跟拍

────────────────────────── 产物 ──────────────────────────
  _blender/episode/           剧集 JSON (中间产物, 与打光/天气无关, 只导出一次)
  _outputs/blender/<style>_<weather>/<element_id>/<sensor 基名>_{rgb,seg,depth}/<帧>.{png,exr}
    seg   : 彩色标签图 (core.seg_color_to_label 可转 label-id)
    depth : 32 位 EXR, 单位米 (cv2.imread(..., IMREAD_UNCHANGED)[:,:,0], 需 OPENCV_IO_ENABLE_OPENEXR=1)
  element_id 本身就区分了视角: J3_* = 路口, E0__0__taxi.0 = 车辆, drone_1 = 无人机.

剧集只跟仿真有关, 打光/天气只在渲染时生效, 所以:
  · 一次运行里扫多个组合 -> 仿真只跑一次;
  · **换个天气重新执行脚本 -> 也不会重跑仿真** —— 导出时会写一份参数指纹
    (_blender/episode/signature.json), 下次参数没变就直接复用.
    改了 --steps 或相机配置才会自动重导; 想强制重导用 --force-export.
@LastEditTime: 2026-08-18
'''
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path
from pathlib import Path

from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env.tshub_env import TshubEnvironment
from tshub.tshub_env3d.core import build_frame, build_tls_rigs
from tshub.tshub_env3d.core.export import BlenderEpisodeExporter

path_convert = get_abs_path(__file__)
SCENARIO_GLB_DIR = path_convert("./3d_assets")          # build_static_scene.py 的产物
SCENE_BLEND = os.path.join(SCENARIO_GLB_DIR, "scene.blend")
EPISODE_DIR = path_convert("./_blender/episode")        # 中间产物
SIGNATURE_NAME = "signature.json"                       # 剧集的参数指纹, 用于跨次运行复用
OUT_ROOT = path_convert("./_outputs/blender")           # 渲染结果

REPO_ROOT = path_convert("../../..")
RENDER_SCRIPT = os.path.join(REPO_ROOT, "tshub/tshub_env3d/renderers/blender/render_episode.py")
DEFAULT_BLENDER = "/home/wmn/blender/blender"

# 无人机: 悬停在路口正上方 (与 render_panda3d.py 一致, 不飞行)
AIRCRAFT_CENTER = (1545.5, 1009.8) # 路口中心 (= build_tls_rigs 给 J3_bev 算出的停车线质心)
AIRCRAFT_ALTITUDE = 32.0

# 三类载体的相机, 合并成一份 sensor_config 一次挂齐
CAMERAS = {
    'tls': {'J3': {
        'sensor_types': ['junction_front_rgb', 'junction_bev_rgb'],
        'tls_camera_height': 9,
    }},
    'vehicle': {'E0__0__taxi.0': {
        'sensor_types': ['front_rgb', 'bev_rgb'],
    }},
    'aircraft': {'drone_1': {
        'sensor_types': ['aircraft_rgb'],
    }},
}
AIRCRAFT_INITS = {'drone_1': {
    'aircraft_type': 'drone', 'action_type': 'stationary',
    'position': (AIRCRAFT_CENTER[0], AIRCRAFT_CENTER[1], AIRCRAFT_ALTITUDE),
    'speed': 0, 'heading': (0, 1, 0),
    'communication_range': 100, 'if_sumo_visualization': False,
}}


def _episode_signature(steps: int) -> dict:
    """决定剧集内容的所有输入 —— 只要这些没变, 剧集就是同一份 (仿真是确定性的)."""
    return {
        'steps': steps,
        'sumo_seed': '7',
        'cameras': CAMERAS,
        'aircraft_inits': AIRCRAFT_INITS,
    }


def episode_is_reusable(steps: int) -> bool:
    """已有剧集是否可直接复用 (打光/天气不影响剧集, 换天气不必重跑仿真)."""
    manifest = os.path.join(EPISODE_DIR, 'manifest.json')
    signature = os.path.join(EPISODE_DIR, SIGNATURE_NAME)
    if not (os.path.exists(manifest) and os.path.exists(signature)):
        return False
    try:
        saved = json.loads(Path(signature).read_text())
    except Exception:
        return False
    # 经 JSON 往返再比, 避免 tuple/list 之类的表示差异造成误判
    return saved == json.loads(json.dumps(_episode_signature(steps), sort_keys=True))


# ------------------------------------------------------------------ #
# 1. 导出剧集 (纯 SUMO, 不启动任何渲染后端; 与打光/天气无关)
# ------------------------------------------------------------------ #
def export_episode(steps: int, resolution, samples: int) -> str:
    set_logger(path_convert('./'), terminal_log_level='ERROR')
    random.seed(7)
    env = TshubEnvironment(
        sumo_cfg=path_convert("./sumo_net/single_junction.sumocfg"),
        is_map_builder_initialized=False,
        is_vehicle_builder_initialized=True,
        is_aircraft_builder_initialized=True,
        is_traffic_light_builder_initialized=True,
        is_person_builder_initialized=False,
        tls_ids=['J3'],
        aircraft_inits=AIRCRAFT_INITS,
        vehicle_action_type='lane_continuous_speed',
        use_gui=False, is_libsumo=True,
        num_seconds=120, collision_action="warn", sumo_seed='7',
    )
    exporter = BlenderEpisodeExporter(
        episode_dir=EPISODE_DIR,
        scenario_glb_dir=SCENARIO_GLB_DIR,
        sensor_config=CAMERAS,
        resolution=resolution, samples=samples,
    )
    states = env.reset()
    exporter.reset(tls_rigs=build_tls_rigs(states, CAMERAS))
    for _ in range(steps):
        actions = {
            'vehicle': dict(),
            'tls': {'J3': random.randint(0, 3)},
            'aircraft': {aid: (0, 0) for aid in AIRCRAFT_INITS}, # stationary, 动作被忽略
        }
        states, _, _, done = env.step(actions)
        exporter.add_frame(build_frame(states))
        if done:
            break
    env._close_simulation()
    manifest = exporter.close()
    # 记下这份剧集是用什么参数跑出来的, 下次同参数直接复用 (剧集与打光/天气无关)
    Path(os.path.join(EPISODE_DIR, SIGNATURE_NAME)).write_text(
        json.dumps(_episode_signature(steps), sort_keys=True))
    print(f"[export] {manifest}")
    return EPISODE_DIR


# ------------------------------------------------------------------ #
# 2. 渲染 (在 build_static_scene.py 生成的 scene.blend 里跑)
# ------------------------------------------------------------------ #
def find_blender() -> str:
    env_blender = os.environ.get("BLENDER")
    if env_blender:
        if not os.path.exists(env_blender):
            raise FileNotFoundError(f"BLENDER 指向的可执行文件不存在: {env_blender}")
        return env_blender
    if os.path.exists(DEFAULT_BLENDER):
        return DEFAULT_BLENDER
    blender = shutil.which("blender")
    if blender:
        return blender
    raise FileNotFoundError("需要 Blender, 请安装或用 BLENDER=/path/to/blender 指定.")


def render_combo(style: str, weather: str, frames: str, samples: int,
                 resolution, passes: list, fused: bool = False) -> str:
    """渲染一个 (打光, 天气) 组合; 复用同一份剧集与同一个 scene.blend.

    默认每个通道各起一次 Blender (rgb/seg/depth 混在一次里渲会让 Cycles 的
    持久化缓存反复失效, 见文件头的实测); --fused-passes 则一次跑完所有通道.
    """
    out_dir = os.path.join(OUT_ROOT, f"{style}_{weather}")
    groups = [passes] if fused else [[p] for p in passes]
    for group in groups:
        cmd = [
            find_blender(), "--background", SCENE_BLEND, "--python", RENDER_SCRIPT, "--",
            EPISODE_DIR, out_dir,
            "--style", style,
            "--samples", str(samples),
            "--resolution", f"{resolution[0]}x{resolution[1]}",
            "--passes", ",".join(group),
        ]
        if weather != 'clear':
            cmd += ["--weather", weather]
        if frames:
            cmd += ["--frames", frames]
        _run(cmd, "RENDER_DONE")
    return out_dir


def _run(cmd: list, done_token: str) -> None:
    """跑 Blender 子进程, 只回显关键日志 (Blender 后台输出很啰嗦)."""
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith(('[assembly]', '[render]', '[weather]', done_token)):
            print(line)
    if result.returncode != 0 or done_token not in result.stdout:
        print(result.stdout[-3000:])
        print(result.stderr[-3000:])
        raise RuntimeError(f"Blender 执行失败: {' '.join(cmd[:4])}")


# ------------------------------------------------------------------ #
def _parse():
    argv = sys.argv[1:]
    opts = {
        'steps': 100, 'every': 20, 'samples': 64, 'resolution': '720x720',
        'style': 'day', 'weather': 'clear', 'passes': 'rgb',
        'export_only': False, 'render_only': False, 'force_export': False,
        'fused_passes': False,
    }
    i = 0
    while i < len(argv):
        key = argv[i].lstrip('-').replace('-', '_')
        if key in ('export_only', 'render_only', 'force_export', 'fused_passes'):
            opts[key] = True; i += 1
        elif key in opts:
            opts[key] = argv[i + 1]; i += 2
        else:
            i += 1
    for k in ('steps', 'every', 'samples'):
        opts[k] = int(opts[k])
    return opts


def _as_list(value):
    return [v.strip() for v in str(value).split(',') if v.strip()]


VALID_PASSES = ('rgb', 'seg', 'depth')


if __name__ == '__main__':
    opts = _parse()
    passes = list(dict.fromkeys(_as_list(opts['passes'])))
    unknown = [p for p in passes if p not in VALID_PASSES]
    if unknown or not passes:
        sys.exit(f"--passes 只能是 {'/'.join(VALID_PASSES)} 的组合, 收到: {opts['passes']!r}")
    if not os.path.exists(SCENE_BLEND):
        sys.exit(
            f"缺少场景文件: {SCENE_BLEND}\n"
            "静态场景只需生成一次, 请先运行:\n"
            "  python examples/tshub_env3d/single_junction/build_static_scene.py"
        )

    resolution = [int(v) for v in opts['resolution'].lower().split('x')]

    # 剧集与打光/天气无关 -> 参数没变就直接复用 (换天气重跑时不必再跑一遍 SUMO)
    if opts['render_only']:
        if not os.path.exists(os.path.join(EPISODE_DIR, 'manifest.json')):
            sys.exit(f"--render-only 需要已导出的剧集, 但没找到 {EPISODE_DIR}/manifest.json")
        print(f"[export] --render-only: 直接使用 {EPISODE_DIR}")
    elif not opts['force_export'] and episode_is_reusable(opts['steps']):
        print(f"[export] 复用已有剧集 (参数未变): {EPISODE_DIR}")
    else:
        export_episode(opts['steps'], resolution, opts['samples'])
    if opts['export_only']:
        sys.exit(0)

    combos = [(s, w) for s in _as_list(opts['style']) for w in _as_list(opts['weather'])]
    for style, weather in combos:
        print(f"=== style={style} / weather={weather} / passes={','.join(passes)}"
              f"{' (fused)' if opts['fused_passes'] else ''} ===")
        out_dir = render_combo(style, weather, f"::{opts['every']}",
                               opts['samples'], resolution, passes,
                               fused=opts['fused_passes'])
        print(f"[done] {style}_{weather} -> {out_dir}")
    print(f"done. 见 {OUT_ROOT}/<style>_<weather>/")
