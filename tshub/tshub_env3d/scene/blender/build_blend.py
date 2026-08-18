'''
@Author: WANG Maonan
@Date: 2026-08-15
@Description: Stage A —— 由静态场景 glb 自动生成可复用的 .blend (在 Blender 内运行).

一个场景 (路网) 只需要生成一次 .blend: 里面包含静态场景 (路面/车道线/建筑/绿化)、
世界环境与打光、渲染设置. 之后所有仿真剧集都在这个 .blend 上渲染 (Stage B,
render_episode.py), 不必重复导入.

生成的 .blend 是普通 Blender 文件, 可以直接用 GUI 打开手工微调 (换材质、加灯光、
调曝光), 存盘后 Stage B 会沿用你的修改 —— 自动化与手调不冲突.

用法 (在仓库根目录):
    /home/wmn/blender/blender --background --python \
        tshub/tshub_env3d/scene/blender/build_blend.py -- \
        <glb_dir> <out.blend> [--style day|dusk|noon] [--samples 64] \
        [--resolution 1280x720] [--engine CYCLES]
@LastEditTime: 2026-08-15
'''
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) # 供 blender 直接 --python 调用
import scene_assembly as assembly # noqa: E402


def parse_args():
    argv = sys.argv
    argv = argv[argv.index('--') + 1:] if '--' in argv else []
    opts = {'style': 'day', 'samples': '64', 'resolution': '1280x720', 'engine': 'CYCLES',
            'view_transform': 'AgX', 'look': 'Punchy'}
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
        raise SystemExit('usage: ... -- <glb_dir> <out.blend> [options]')
    return positional[0], positional[1], opts


def build_blend(glb_dir: str, out_blend: str, style: str = 'day',
                samples: int = 64, resolution=(1280, 720),
                engine: str = 'CYCLES', view_transform: str = 'AgX',
                look: str = 'Punchy') -> str:
    """装配静态场景 + 打光 + 渲染设置, 存成 .blend."""
    assembly.clear_scene()
    assembly.import_static_scene(glb_dir)
    assembly.setup_world(style)
    assembly.setup_render(resolution=resolution, samples=samples, engine=engine,
                          view_transform=view_transform, look=look)

    out_blend = os.path.abspath(out_blend)
    os.makedirs(os.path.dirname(out_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    print(f'BLEND_DONE: {out_blend} (glb_dir={glb_dir}, style={style}, '
          f'samples={samples}, {resolution[0]}x{resolution[1]}, engine={engine})')
    return out_blend


if __name__ == '__main__':
    glb_dir, out_blend, opts = parse_args()
    build_blend(
        glb_dir=glb_dir,
        out_blend=out_blend,
        style=opts['style'],
        samples=int(opts['samples']),
        resolution=[int(v) for v in opts['resolution'].lower().split('x')],
        engine=opts['engine'],
        view_transform=opts['view_transform'],
        look=opts['look'],
    )
