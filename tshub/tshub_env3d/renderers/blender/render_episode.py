'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: Stage B —— 在已有 .blend 内渲染一段仿真剧集 (在 Blender 内运行).

前置: Stage A (build_blend.py) 生成的场景 .blend —— 静态场景/打光/渲染设置都在里面
(也可以是你用 GUI 手工微调过的版本). 本脚本只负责「动的部分」: 每一仿真步按剧集
JSON 摆好车辆与飞行器、放好相机, 然后逐相机出图.

剧集数据由 tshub 侧的 core.export.BlenderEpisodeExporter 导出, 因此本脚本不依赖
tshub / SUMO / Panda3D, 只读 JSON.

用法 (在仓库根目录):
    /home/wmn/blender/blender --background <scene.blend> --python \
        tshub/tshub_env3d/renderers/blender/render_episode.py -- \
        <episode_dir> <out_dir> [--frames 0:40:5] [--samples 64] \
        [--resolution 1280x720] [--cameras front_rgb,bev_rgb] [--style day] \
        [--weather clear|fog|rain] [--passes rgb|seg|depth (可逗号分隔)] \
        [--vehicle-yaw-offset 0] [--save-blend dbg.blend]

--passes 里的每个通道都是独立的: 只写 `--passes seg` 就只出 seg, 不会顺带渲 rgb.

**多通道优先分多次进程跑, 而不是一次跑多个通道** (每次 --passes 只给一个通道):
实测 (101 帧 x 1 相机, 1022x1022, samples=8, Cycles GPU):
    rgb 143.1s + seg 47.7s = 190.8s   vs   `--passes rgb,seg` 一次跑 302.9s (贵 59%)
原因是 rgb 与 seg 交替渲染时, 每次渲染看到的 material_override 状态都不同,
use_persistent_data 的缓存每渲一次就失效一次, 两个通道都要付全量场景重导出的代价
(单独测过: 只渲 rgb 但每帧照常切换 seg 状态, 只慢 2%, 所以贵的不是切换本身).
Blender 启动 + 加载 scene.blend 约 1.5s, 相比之下可以忽略.

**降噪跑在 GPU 上**: Blender 出厂默认让 OpenImageDenoise 跑 CPU, 且该默认值不随
.blend 保存, 所以和 GPU 设备一样必须在渲染时重新指定 (还必须赶在第一次 render()
之前, 因为 use_persistent_data 会把降噪设备锁进 Cycles session). 实测 60 帧剧集
(4090, 1274x1274, samples=8): 2.10s/帧 -> 0.685s/帧. 详见
scene_assembly.setup_denoiser.
examples/tshub_env3d/single_junction/render_blender.py 默认就是这么调度的.

输出: <out_dir>/<element_id>/<sensor 基名>_{rgb,seg,depth}/<frame_index>.{png,png,exr}
      rgb   : Cycles 出图 (含天气)
      seg   : 语义分割彩色图 (调色板同 core.sensors.seg_classes, 用 seg_color_to_label 转 label id)
      depth : 32 位单层 EXR, 单通道, 单位为米 (不归一化; 天空等未命中处为极大值)
@LastEditTime: 2026-08-19
'''
import contextlib
import hashlib
import json
import os
import sys
import time

import bpy

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE) # 供 blender 直接 --python 调用 (weather / render_passes 在同目录)
# 场景装配库属于「生成」那一侧 (scene/blender/), 渲染时复用它来放相机与实例化车辆
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', 'scene', 'blender')))
import scene_assembly as assembly # noqa: E402
import weather as weather_fx # noqa: E402
import render_passes # noqa: E402


# 通道 -> 进入该通道渲染状态的上下文管理器 (rgb 就是 .blend 里的原始状态, 不用切) 与输出扩展名
PASS_MODES = {'rgb': None, 'seg': render_passes.seg_mode, 'depth': render_passes.depth_mode}
PASS_EXT = {'rgb': 'png', 'seg': 'png', 'depth': 'exr'}


def parse_args():
    argv = sys.argv
    argv = argv[argv.index('--') + 1:] if '--' in argv else []
    opts = {
        'frames': None, 'samples': None, 'resolution': None,
        'save_blend': None, 'vehicle_yaw_offset': '0', 'exposure': None,
        'view_transform': None, 'look': None, 'style': None, 'cameras': None,
        'weather': None, 'passes': 'rgb',
    }
    positional = []
    i = 0
    while i < len(argv):
        key = argv[i].lstrip('-').replace('-', '_')
        if argv[i].startswith('--') and key in opts:
            opts[key] = argv[i + 1]
            i += 2
        else:
            positional.append(argv[i])
            i += 1
    if len(positional) < 2:
        raise SystemExit('usage: ... -- <episode_dir> <out_dir> [options]')
    return positional[0], positional[1], opts


def parse_passes(spec: str) -> tuple:
    """'rgb,seg' -> ('rgb', 'seg'); 通道之间互相独立, 只写 seg 就只出 seg."""
    passes = tuple(dict.fromkeys(p.strip() for p in str(spec).split(',') if p.strip()))
    unknown = [p for p in passes if p not in PASS_MODES]
    if unknown or not passes:
        raise SystemExit(f'--passes 只能是 {"/".join(PASS_MODES)} 的组合, 收到: {spec!r}')
    return passes


def parse_frame_range(spec: str, total: int) -> list:
    """'start:stop:step' (各段可省略) -> 帧序号列表."""
    if not spec:
        return list(range(total))
    parts = (spec.split(':') + ['', '', ''])[:3]
    start = int(parts[0]) if parts[0] else 0
    stop = int(parts[1]) if parts[1] else total
    step = int(parts[2]) if parts[2] else 1
    return list(range(start, min(stop, total), step))


def check_static_scene() -> None:
    """确认当前 .blend 里确实有静态场景 (Stage A 的产物)."""
    layers = [name for name in assembly.STATIC_LAYERS if bpy.data.collections.get(name)]
    if not layers:
        print('[render] 警告: 当前 .blend 内没有静态场景 collection, '
              '请先用 build_blend.py 生成场景 .blend 并以 `blender -b <scene.blend>` 打开.')
    else:
        print(f'[render] 静态场景: {", ".join(layers)}')


def select_cameras(specs: list, wanted: str) -> list:
    """按逗号分隔的名字过滤相机 (可写 sensor_type / element_id / 完整相机名)."""
    if not wanted:
        return specs
    keys = {k.strip() for k in wanted.split(',') if k.strip()}
    return [s for s in specs
            if keys & {s['sensor_type'], s['element_id'], s['name']}]


def pass_dir(out_dir: str, spec: dict, modality: str) -> str:
    """输出目录: <out>/<element>/<sensor 基名>_<modality>/ (与 Panda 的传感器命名一致)."""
    sensor_type = spec['sensor_type']
    base = sensor_type[:-4] if sensor_type.endswith('_rgb') else sensor_type
    return os.path.join(out_dir, spec['element_id'], f'{base}_{modality}')


def _render_cameras(cameras, out_dir: str, index: int, modality: str, ext: str = 'png') -> int:
    """把当前渲染状态下的所有相机各渲一张 (状态由调用方用 seg_mode/depth_mode 事先切好)."""
    scene = bpy.context.scene
    for spec, cam in cameras:
        target_dir = pass_dir(out_dir, spec, modality)
        os.makedirs(target_dir, exist_ok=True)
        scene.camera = cam
        scene.render.filepath = os.path.join(target_dir, f'{index:04d}.{ext}')
        bpy.ops.render.render(write_still=True)
    return len(cameras)


def render_frame(frame_data: dict, out_dir: str, veh_lib, air_lib,
                 camera_filter: str = None, overlay: dict = None,
                 passes=('rgb',), mode_hoisted: bool = False) -> int:
    """摆好本帧的动态物体与相机, 逐通道出图, 返回出图数量.

    **按通道分组, 不要按相机分组**: seg/depth 要切 material_override 与合成器,
    按相机循环的话每帧要切 2x相机数 次, 按通道分组只切 2 次.
    实测 5 相机 x 3 通道 (1280x720/24spp): 17.0s -> 12.1s 每帧.

    mode_hoisted: 整段只渲一个非 rgb 通道时, 调用方已经把该通道的状态切在循环外面了
    (见 main), 这里就不再逐帧进出上下文 —— 全程状态不变, 缓存也不用逐帧重建.
    """
    scene = bpy.context.scene
    if overlay and 'rgb' in passes: # 雨丝逐帧重新生成 (只有 rgb 会带天气; seg/depth 关合成器)
        weather_fx.set_overlay_frame(frame_data['index'], overlay,
                                     (scene.render.resolution_x, scene.render.resolution_y))
    veh_lib.sync(frame_data.get('vehicles', {}), assembly.VEHICLES_COLLECTION)
    air_lib.sync(frame_data.get('aircraft', {}), assembly.AIRCRAFT_COLLECTION)

    specs = select_cameras(frame_data.get('cameras', []), camera_filter)
    cameras = assembly.sync_cameras(specs)
    assembly.remove_cameras(keep_names={spec['name'] for spec in specs})
    if 'seg' in passes: # 车辆每帧增删, 类别颜色要重新贴 (静态部分只在首帧着色)
        render_passes.assign_seg_colors()

    index = frame_data['index']
    written = 0
    for name in passes:
        mode = PASS_MODES[name]
        with contextlib.ExitStack() as stack:
            if mode is not None and not mode_hoisted:
                stack.enter_context(mode())
            written += _render_cameras(cameras, out_dir, index, name, ext=PASS_EXT[name])
    return written


def main() -> None:
    episode_dir, out_dir, opts = parse_args()
    manifest = json.loads(open(os.path.join(episode_dir, 'manifest.json')).read())
    scene = bpy.context.scene

    check_static_scene()
    # GPU 与降噪设备都存在用户偏好里 (不随 .blend 保存), 每次渲染都要重新指定.
    # 降噪必须在第一次 render() 之前设好: 下面开了 use_persistent_data, Cycles
    # session 跨帧复用, 降噪设备在 session 建好那一刻就定死了.
    if scene.render.engine == 'CYCLES':
        scene.cycles.device = 'GPU' if assembly.setup_gpu() else 'CPU'
        assembly.setup_denoiser()
    # 静态场景不变: 让 Cycles 跨渲染复用已导出的场景与 BVH (老 .blend 里可能没存这个标志).
    # 这是本流水线最大的一笔加速: 每帧要渲 相机数 x 通道数 次, 场景越大收益越大.
    scene.render.use_persistent_data = True
    # 仅在显式指定时覆盖 .blend 内的设置 (尊重手工微调过的场景)
    if opts['samples'] and scene.render.engine == 'CYCLES':
        scene.cycles.samples = int(opts['samples'])
    if opts['resolution']:
        width, height = (int(v) for v in str(opts['resolution']).lower().split('x'))
        scene.render.resolution_x, scene.render.resolution_y = width, height
    # 天气: 改材质 (湿路面/积雪) + 合成器 (深度雾 + 雨雪叠加), 并给出光照修正
    weather_name = opts['weather'] or 'clear'
    # 雨向是 episode 级随机量: 同一 episode 内固定，跨 episode 变化；使用稳定
    # SHA-256 而不是 Python hash()，保证不同进程/机器和重复渲染结果一致。
    episode_key = manifest.get('episode_id') or os.path.basename(os.path.abspath(episode_dir))
    episode_seed = int.from_bytes(
        hashlib.sha256(f'{episode_key}:{weather_name}'.encode('utf-8')).digest()[:8],
        'big',
    )
    overlay_cfg = weather_fx.overlay_config(weather_name, seed=episode_seed)
    light_overrides = weather_fx.apply_weather(
        weather_name,
        resolution=(scene.render.resolution_x, scene.render.resolution_y),
        seed=episode_seed,
    )
    if overlay_cfg:
        print(f'[weather] episode={episode_key} seed={episode_seed} '
              f'angle={overlay_cfg.get("angle", 0.0):.1f} deg')
    if opts['style'] or light_overrides: # 快速试打光 (会连带设置该风格的曝光)
        base_style = opts['style'] or manifest.get('style', 'day')
        assembly.setup_world({**assembly.resolve_style(base_style), **light_overrides})
    if opts['exposure'] is not None: # 显式曝光优先于风格自带的曝光
        scene.view_settings.exposure = float(opts['exposure'])
    if opts['view_transform'] or opts['look']: # 快速试色调, 定下来后写回 build_blend
        assembly.set_color_management(
            opts['view_transform'] or scene.view_settings.view_transform,
            opts['look'] or scene.view_settings.look,
        )

    # 输出通道: 各自独立渲一遍 (seg / depth 都只要 1 个样本, 单看很便宜);
    # 一次只渲一个通道时, 把通道状态提到整段之外, 全程不再动场景 (见文件头的实测)
    passes = parse_passes(opts['passes'])
    hoist_mode = len(passes) == 1 and PASS_MODES[passes[0]] is not None
    print(f'[render] passes: {", ".join(passes)}' + (' (整段单通道)' if hoist_mode else ''))

    veh_lib = assembly.ModelLibrary(manifest['vehicles_dir'],
                                    yaw_offset_deg=float(opts['vehicle_yaw_offset']))
    air_lib = assembly.ModelLibrary(manifest['aircraft_dir'])

    frame_files = manifest['frames']
    indices = parse_frame_range(opts['frames'], len(frame_files))
    total_images = 0
    started = time.perf_counter()
    with contextlib.ExitStack() as stack:
        if hoist_mode: # 通道状态切一次, 整段共用 (逐帧进出的话缓存每帧都要重建)
            stack.enter_context(PASS_MODES[passes[0]]())
        for i in indices:
            frame_data = json.loads(open(os.path.join(episode_dir, frame_files[i])).read())
            frame_started = time.perf_counter()
            count = render_frame(frame_data, out_dir, veh_lib, air_lib,
                                 opts['cameras'], overlay_cfg, passes,
                                 mode_hoisted=hoist_mode)
            total_images += count
            print(f'[render] frame {i:04d}: {count} images, '
                  f'{len(frame_data.get("vehicles", {}))} vehicles, '
                  f'{time.perf_counter() - frame_started:.1f}s')
            if opts['save_blend'] and i == indices[0]: # 落一份含车辆/相机的 .blend, 便于排查位姿
                blend_path = os.path.abspath(opts['save_blend'])
                os.makedirs(os.path.dirname(blend_path) or '.', exist_ok=True)
                bpy.ops.wm.save_as_mainfile(filepath=blend_path)
                print(f'[render] saved blend -> {blend_path}')

    elapsed = time.perf_counter() - started
    # samples 只对 rgb 有意义 (seg/depth 各自的模式里恒为 1 sample)
    samples = scene.cycles.samples if scene.render.engine == 'CYCLES' else '-'
    print(f'RENDER_DONE: {total_images} images in {elapsed:.1f}s ({len(indices)} frames, '
          f'passes={"+".join(passes)}, samples={samples}, '
          f'{scene.render.resolution_x}x{scene.render.resolution_y}) -> {out_dir}')


if __name__ == '__main__':
    main()
