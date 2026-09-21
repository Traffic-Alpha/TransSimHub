'''
@Author: WANG Maonan
@Date: 2026-08-18
@Description: 把 Blender 渲出的深度图 (EXR, 单位米) 转成能直接看的伪彩图.

深度通道是 32 位单层 EXR, 存的是**真实米数**(不归一化), 天空/未命中处是极大值 ——
直接用看图软件打开是一片白, 所以需要这个脚本: 按距离上色, 并把 RGB 放在旁边对照.

前置: 先渲出 depth 通道
    python examples/tshub_env3d/single_junction/render_blender.py --passes rgb,seg,depth

用法:
    python examples/tshub_env3d/single_junction/show_depth_result.py            # 全部
    python .../show_depth_result.py --combo golden_fog                          # 只看某个打光/天气
    python .../show_depth_result.py --camera junction_front --frame 0020        # 只看某个相机/某帧
    python .../show_depth_result.py --max-depth 120                             # 固定色标上限(便于跨帧比较)

输出: _outputs/depth_vis/<combo>/<element>/<sensor>/<帧>.png
      左 = RGB (若有), 右 = 伪彩深度 (近=红, 远=蓝, 天空=黑) + 色标
'''
import os
import sys

os.environ.setdefault('OPENCV_IO_ENABLE_OPENEXR', '1') # 必须在 import cv2 之前设置

import cv2
import numpy as np

# 只依赖 cv2 + numpy: 纯看图工具, 不需要 SUMO / tshub 环境
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.join(HERE, "_outputs", "blender")
VIS_ROOT = os.path.join(HERE, "_outputs", "depth_vis")
MISS = 1e6 # 大于此值视为「没打到东西」(天空), Blender 会给一个极大值


def load_depth(exr_path: str):
    """读 EXR -> (深度(米) 二维数组, 命中掩码)."""
    img = cv2.imread(exr_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(f"读不出 EXR: {exr_path} (OpenCV 需要 OPENCV_IO_ENABLE_OPENEXR=1)")
    depth = img[:, :, 0] if img.ndim == 3 else img # 三个通道值相同, 取一个
    return depth, depth < MISS


def colorize(depth, hit, lo: float = None, hi: float = None):
    """深度 -> 伪彩. 近处红、远处蓝, 未命中(天空)黑."""
    if hit.any():
        lo = float(np.percentile(depth[hit], 1)) if lo is None else lo
        hi = float(np.percentile(depth[hit], 99)) if hi is None else hi
    else:
        lo, hi = 0.0, 1.0
    if hi - lo < 1e-6:
        hi = lo + 1e-6
    norm = np.clip((depth - lo) / (hi - lo), 0, 1)
    # TURBO 是 0=蓝 -> 1=红, 这里反过来让「近=红, 远=蓝」符合直觉
    vis = cv2.applyColorMap(((1 - norm) * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    vis[~hit] = 0 # 天空涂黑
    return vis, lo, hi


def add_colorbar(vis, lo: float, hi: float):
    """底部加一条色标, 标出两端对应的米数."""
    h, w = vis.shape[:2]
    bar_h = max(24, h // 20)
    ramp = np.linspace(1, 0, w, dtype=np.float32)          # 左=近, 右=远
    bar = cv2.applyColorMap((ramp * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    bar = np.repeat(bar.reshape(1, w, 3), bar_h, axis=0)
    cv2.putText(bar, f"{lo:.0f}m", (6, bar_h - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    label = f"{hi:.0f}m"
    (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.putText(bar, label, (w - tw - 6, bar_h - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return np.vstack([vis, bar])


def rgb_beside(exr_path: str):
    """找同一相机同一帧的 RGB 图 (<sensor>_depth -> <sensor>_rgb), 没有就返回 None."""
    sensor_dir, name = os.path.split(exr_path)
    rgb_dir = sensor_dir.replace('_depth', '_rgb')
    rgb_path = os.path.join(rgb_dir, name.replace('.exr', '.png'))
    return cv2.imread(rgb_path) if os.path.exists(rgb_path) else None


def visualize(exr_path: str, lo: float = None, hi: float = None) -> str:
    depth, hit = load_depth(exr_path)
    vis, lo_used, hi_used = colorize(depth, hit, lo, hi)
    vis = add_colorbar(vis, lo_used, hi_used)

    rgb = rgb_beside(exr_path)
    if rgb is not None: # 高度对齐后左右拼接
        scale = vis.shape[0] / rgb.shape[0]
        rgb = cv2.resize(rgb, (int(rgb.shape[1] * scale), vis.shape[0]))
        vis = np.hstack([rgb, vis])

    out_path = os.path.join(VIS_ROOT, os.path.relpath(exr_path, SRC_ROOT)).replace('.exr', '.png')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, vis)

    rel = os.path.relpath(exr_path, SRC_ROOT)
    if hit.any():
        d = depth[hit]
        print(f"  {rel:58s} {d.min():6.1f} ~ {d.max():7.1f} m (中位 {np.median(d):6.1f}), "
              f"命中 {100 * hit.mean():5.1f}%")
    else:
        print(f"  {rel:58s} 全部未命中 (整幅都是天空?)")
    return out_path


def _parse():
    argv = sys.argv[1:]
    opts = {'combo': None, 'camera': None, 'frame': None, 'max_depth': None, 'min_depth': None}
    i = 0
    while i < len(argv):
        key = argv[i].lstrip('-').replace('-', '_')
        if key in opts:
            opts[key] = argv[i + 1]; i += 2
        else:
            i += 1
    return opts


if __name__ == '__main__':
    opts = _parse()
    if not os.path.isdir(SRC_ROOT):
        sys.exit(f"没有渲染结果: {SRC_ROOT}\n"
                 "请先运行: python examples/tshub_env3d/single_junction/render_blender.py --passes rgb,seg,depth")

    targets = []
    for root, _dirs, files in os.walk(SRC_ROOT):
        for name in sorted(files):
            if not name.endswith('.exr'):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, SRC_ROOT)
            if opts['combo'] and not rel.startswith(opts['combo'] + os.sep):
                continue
            if opts['camera'] and opts['camera'] not in rel:
                continue
            if opts['frame'] and not name.startswith(opts['frame']):
                continue
            targets.append(path)

    if not targets:
        sys.exit("按当前筛选条件没有找到 depth 文件 (.exr); 确认渲染时带了 --passes ...,depth")

    lo = float(opts['min_depth']) if opts['min_depth'] else None
    hi = float(opts['max_depth']) if opts['max_depth'] else None
    print(f"共 {len(targets)} 张深度图 (色标: {'固定 ' + str(hi) + 'm' if hi else '每张自动按 1~99 分位'})")
    for path in targets:
        visualize(path, lo, hi)
    print(f"done. 见 {VIS_ROOT}/")
