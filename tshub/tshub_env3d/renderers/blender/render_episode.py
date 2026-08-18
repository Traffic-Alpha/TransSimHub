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
        [--weather clear|fog|rain] [--passes rgb,seg,depth] \
        [--vehicle-yaw-offset 0] [--save-blend dbg.blend]

输出: <out_dir>/<element_id>/<sensor 基名>_{rgb,seg,depth}/<frame_index>.{png,png,exr}
      rgb   : Cycles 出图 (含天气)
      seg   : 语义分割彩色图 (调色板同 core.sensors.seg_classes, 用 seg_color_to_label 转 label id)
      depth : 32 位单层 EXR, 单通道, 单位为米 (不归一化; 天空等未命中处为极大值)
@LastEditTime: 2026-08-15
'''
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


def render_frame(frame_data: dict, out_dir: str, veh_lib, air_lib,
                 camera_filter: str = None, overlay: dict = None,
                 passes=('rgb',)) -> int:
    """摆好本帧的动态物体与相机, 逐相机逐通道出图, 返回出图数量."""
    scene = bpy.context.scene
    if overlay: # 雨丝逐帧重新生成
        weather_fx.set_overlay_frame(frame_data['index'], overlay,
                                     (scene.render.resolution_x, scene.render.resolution_y))
    veh_lib.sync(frame_data.get('vehicles', {}), assembly.VEHICLES_COLLECTION)
    air_lib.sync(frame_data.get('aircraft', {}), assembly.AIRCRAFT_COLLECTION)

    specs = select_cameras(frame_data.get('cameras', []), camera_filter)
    cameras = assembly.sync_cameras(specs)
    assembly.remove_cameras(keep_names={spec['name'] for spec in specs})
    if 'seg' in passes: # 车辆每帧增删, 类别颜色要重新贴
        render_passes.assign_seg_colors()

    index = frame_data['index']
    written = 0
    for spec, cam in cameras:
        scene.camera = cam
        # 1. RGB (depth 在这次渲染里顺带由合成器写出, 不额外渲一遍)
        rgb_dir = pass_dir(out_dir, spec, 'rgb')
        os.makedirs(rgb_dir, exist_ok=True)
        scene.render.filepath = os.path.join(rgb_dir, f'{index:04d}.png')
        bpy.ops.render.render(write_still=True)
        written += 1

        # 2. 语义分割 (1-sample 自发光渲染, 不受天气/色调映射影响)
        if 'seg' in passes:
            seg_dir = pass_dir(out_dir, spec, 'seg')
            os.makedirs(seg_dir, exist_ok=True)
            with render_passes.seg_mode():
                scene.render.filepath = os.path.join(seg_dir, f'{index:04d}.png')
                bpy.ops.render.render(write_still=True)
            written += 1

        # 3. 深度 (1-sample, 输出 32 位单层 EXR, 单位米)
        if 'depth' in passes:
            depth_dir = pass_dir(out_dir, spec, 'depth')
            os.makedirs(depth_dir, exist_ok=True)
            with render_passes.depth_mode():
                scene.render.filepath = os.path.join(depth_dir, f'{index:04d}.exr')
                bpy.ops.render.render(write_still=True)
            written += 1
    return written


def main() -> None:
    episode_dir, out_dir, opts = parse_args()
    manifest = json.loads(open(os.path.join(episode_dir, 'manifest.json')).read())
    scene = bpy.context.scene

    check_static_scene()
    # GPU 设置存在用户偏好里 (不随 .blend 保存), 每次渲染都要重新指定
    if scene.render.engine == 'CYCLES':
        scene.cycles.device = 'GPU' if assembly.setup_gpu() else 'CPU'
    # 仅在显式指定时覆盖 .blend 内的设置 (尊重手工微调过的场景)
    if opts['samples'] and scene.render.engine == 'CYCLES':
        scene.cycles.samples = int(opts['samples'])
    if opts['resolution']:
        width, height = (int(v) for v in str(opts['resolution']).lower().split('x'))
        scene.render.resolution_x, scene.render.resolution_y = width, height
    # 天气: 改材质 (湿路面/积雪) + 合成器 (深度雾 + 雨雪叠加), 并给出光照修正
    weather_name = opts['weather'] or 'clear'
    overlay_cfg = weather_fx.overlay_config(weather_name)
    light_overrides = weather_fx.apply_weather(
        weather_name,
        resolution=(scene.render.resolution_x, scene.render.resolution_y),
    )
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

    # 输出通道: rgb 总是产出; seg / depth 各自再渲一遍 (都只要 1 个样本, 很便宜)
    passes = tuple(p.strip() for p in str(opts['passes']).split(',') if p.strip())
    print(f'[render] passes: {", ".join(passes)}')

    veh_lib = assembly.ModelLibrary(manifest['vehicles_dir'],
                                    yaw_offset_deg=float(opts['vehicle_yaw_offset']))
    air_lib = assembly.ModelLibrary(manifest['aircraft_dir'])

    frame_files = manifest['frames']
    indices = parse_frame_range(opts['frames'], len(frame_files))
    total_images = 0
    started = time.perf_counter()
    for i in indices:
        frame_data = json.loads(open(os.path.join(episode_dir, frame_files[i])).read())
        frame_started = time.perf_counter()
        count = render_frame(frame_data, out_dir, veh_lib, air_lib,
                             opts['cameras'], overlay_cfg, passes)
        total_images += count
        print(f'[render] frame {i:04d}: {count} images, '
              f'{len(frame_data.get("vehicles", {}))} vehicles, '
              f'{time.perf_counter() - frame_started:.1f}s')
        if opts['save_blend'] and i == indices[0]: # 落一份含车辆/相机的 .blend, 便于排查位姿
            blend_path = os.path.abspath(opts['save_blend'])
            os.makedirs(os.path.dirname(blend_path), exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=blend_path)
            print(f'[render] saved blend -> {blend_path}')

    elapsed = time.perf_counter() - started
    samples = scene.cycles.samples if scene.render.engine == 'CYCLES' else '-'
    print(f'RENDER_DONE: {total_images} images in {elapsed:.1f}s ({len(indices)} frames, '
          f'samples={samples}, {scene.render.resolution_x}x{scene.render.resolution_y}) -> {out_dir}')


if __name__ == '__main__':
    main()
