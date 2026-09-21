'''
@Author: WANG Maonan
@Date: 2026-08-19
@Description: 把 single_junction 的各类渲染结果拼成一张总览图, 用于文档展示.

这是个**一次性的出图脚本**: 它只读 _outputs/ 下已经渲好的图片, 不重新渲染.
所以先把两条渲染路径各跑一遍:

    python examples/tshub_env3d/single_junction/render_panda3d.py
    python examples/tshub_env3d/single_junction/render_blender.py \
        --style day,golden,dusk --weather clear,fog,rain --passes rgb,seg,depth

用法:
    python examples/tshub_env3d/single_junction/make_showcase.py
    python .../make_showcase.py --tile 360 --out /tmp/showcase.png

输出 (默认): examples/tshub_env3d/single_junction/showcase.png
四个板块 (图内文字用英文): 相机布置 / 输出通道 / 打光与天气 / 两个后端对比.
缺图的格子会画成占位块并在终端提示, 不会中断.
'''
import os
import sys

os.environ.setdefault('OPENCV_IO_ENABLE_OPENEXR', '1') # 必须在 import cv2 之前

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from show_depth_result import load_depth, colorize  # noqa: E402  复用深度上色

# 所有 Blender 格子都取同一帧, 这样"同一时刻、不同相机/不同通道/不同天气"才是可比的.
# (Panda 那几格是另一次仿真, 帧号体系不同, 取最后一帧.)
FRAME = "0020"

PANDA = os.path.join(HERE, "_outputs", "panda")
BLENDER = os.path.join(HERE, "_outputs", "blender")
DEFAULT_OUT = os.path.join(HERE, "showcase.png")

BG = (24, 24, 24)          # 背景 (BGR)
HEADER_BG = (48, 40, 34)

# 文字统一走 PIL + TrueType: 抗锯齿比 cv2 的 Hershey 字体好, 且万一标签要写中文也不会变 ???.
_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
]
_font_cache = {}


def _font(size: int):
    if size not in _font_cache:
        for path in _FONT_CANDIDATES:
            if os.path.exists(path):
                _font_cache[size] = ImageFont.truetype(path, size)
                break
        else:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def draw_text(img, text: str, xy, size: int, color) -> None:
    """在 BGR 图上原地写字 (支持中文). color 为 BGR."""
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    ImageDraw.Draw(pil).text(xy, text, font=_font(size), fill=tuple(reversed(color)))
    img[:] = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


def _pick(directory: str, frame: str = None):
    """取目录下的某一帧; frame 为空则取最后一帧. 找不到返回 None."""
    if not os.path.isdir(directory):
        return None
    files = sorted(f for f in os.listdir(directory) if f.endswith(('.png', '.exr')))
    if not files:
        return None
    if frame:
        hit = [f for f in files if f.startswith(frame)]
        if hit:
            return os.path.join(directory, hit[0])
    return os.path.join(directory, files[-1])


def tile(path: str, label: str, size: int):
    """读一张图 (png 或 depth exr) -> 方形缩略图 + 底部标签."""
    if path is None:
        img = np.full((size, size, 3), 60, np.uint8)
        draw_text(img, "N/A", (size // 2 - 20, size // 2 - 12), 20, (150, 150, 150))
    elif path.endswith('.exr'):
        depth, hit = load_depth(path)
        img, _lo, _hi = colorize(depth, hit)
        img = cv2.resize(img, (size, size))
    else:
        img = cv2.resize(cv2.imread(path), (size, size))

    bar = np.zeros((28, size, 3), np.uint8)
    draw_text(bar, label, (7, 5), 16, (235, 235, 235))
    return np.vstack([img, bar])


def section(title: str, cells, size: int, per_row: int = 6):
    """一个板块: 标题条 + 若干格子 (自动换行)."""
    header = np.full((34, size * min(per_row, len(cells)) + 2 * (min(per_row, len(cells)) - 1), 3),
                     HEADER_BG, np.uint8)
    draw_text(header, title, (9, 7), 19, (170, 220, 250))

    rows, missing = [], []
    for start in range(0, len(cells), per_row):
        chunk = cells[start:start + per_row]
        tiles = []
        for label, path in chunk:
            if path is None:
                missing.append(label)
            tiles.append(tile(path, label, size))
        row = tiles[0]
        for t in tiles[1:]:
            row = np.hstack([row, np.full((row.shape[0], 2, 3), BG, np.uint8), t])
        rows.append(row)

    width = max(r.shape[1] for r in rows)
    padded = [np.hstack([r, np.full((r.shape[0], width - r.shape[1], 3), BG, np.uint8)])
              if r.shape[1] < width else r for r in rows]
    if header.shape[1] < width:
        header = np.hstack([header, np.full((34, width - header.shape[1], 3), HEADER_BG, np.uint8)])
    body = padded[0]
    for r in padded[1:]:
        body = np.vstack([body, np.full((3, width, 3), BG, np.uint8), r])
    return np.vstack([header, body]), missing


def build(size: int):
    b = lambda combo, element, sensor, frame=None: _pick(
        os.path.join(BLENDER, combo, element, sensor), frame)
    p = lambda sky, view, element, sensor, frame=None: _pick(
        os.path.join(PANDA, sky, view, element, sensor), frame)

    sections, missing = [], []
    for title, cells, per_row in [
        # 1. 同一时刻, 不同载体上的相机
        ("(1) Camera rigs, grouped by carrier  [Blender, day / clear]", [
            ("Junction  approach A", b('day_clear', 'J3_2', 'junction_front_rgb', FRAME)),
            ("Junction  approach B", b('day_clear', 'J3_0', 'junction_front_rgb', FRAME)),
            ("Junction  BEV", b('day_clear', 'J3_bev', 'junction_bev_rgb', FRAME)),
            ("Vehicle  front", b('day_clear', 'E0__0__taxi.0', 'front_rgb', FRAME)),
            ("Vehicle  BEV", b('day_clear', 'E0__0__taxi.0', 'bev_rgb', FRAME)),
            ("Drone  top-down", b('day_clear', 'drone_1', 'aircraft_rgb', FRAME)),
        ], 6),
        # 2. 三个输出通道
        ("(2) Every camera emits three channels:  RGB / semantic seg (10 classes) / depth (metres, near = red)", [
            ("Junction  RGB", b('day_clear', 'J3_2', 'junction_front_rgb', FRAME)),
            ("Junction  Seg", b('day_clear', 'J3_2', 'junction_front_seg', FRAME)),
            ("Junction  Depth", b('day_clear', 'J3_2', 'junction_front_depth', FRAME)),
            ("Vehicle front  RGB", b('day_clear', 'E0__0__taxi.0', 'front_rgb', FRAME)),
            ("Vehicle front  Seg", b('day_clear', 'E0__0__taxi.0', 'front_seg', FRAME)),
            ("Vehicle front  Depth", b('day_clear', 'E0__0__taxi.0', 'front_depth', FRAME)),
        ], 6),
        # 3. 打光 x 天气
        ("(3) Lighting style x weather, same camera  [Blender / Cycles]", [
            ("day + clear", b('day_clear', 'J3_2', 'junction_front_rgb', FRAME)),
            ("golden + clear", b('golden_clear', 'J3_2', 'junction_front_rgb', FRAME)),
            ("dusk + clear", b('dusk_clear', 'J3_2', 'junction_front_rgb', FRAME)),
            ("day + fog", b('day_fog', 'J3_2', 'junction_front_rgb', FRAME)),
            ("day + rain", b('day_rain', 'J3_2', 'junction_front_rgb', FRAME)),
            ("dusk + rain", b('dusk_rain', 'J3_2', 'junction_front_rgb', FRAME)),
        ], 6),
        # 4. 两个后端
        ("(4) Two backends on the same camera:  Panda3D online (real-time, in the loop)  vs  Blender offline (Cycles)", [
            ("Panda3D  day  RGB", p('day', 'junction', 'J3_2', 'junction_front_rgb')),
            ("Panda3D  day  Seg", p('day', 'junction', 'J3_2', 'junction_front_seg')),
            ("Panda3D  dust  RGB", p('dust', 'junction', 'J3_2', 'junction_front_rgb')),
            ("Blender  day/clear  RGB", b('day_clear', 'J3_2', 'junction_front_rgb', FRAME)),
            ("Blender  day/clear  Seg", b('day_clear', 'J3_2', 'junction_front_seg', FRAME)),
            ("Blender  day/clear  Depth", b('day_clear', 'J3_2', 'junction_front_depth', FRAME)),
        ], 6),
    ]:
        block, miss = section(title, cells, size, per_row)
        sections.append(block)
        missing += miss

    width = max(s.shape[1] for s in sections)
    canvas = []
    for s in sections:
        if s.shape[1] < width:
            s = np.hstack([s, np.full((s.shape[0], width - s.shape[1], 3), BG, np.uint8)])
        canvas.append(s)
        canvas.append(np.full((10, width, 3), BG, np.uint8))
    return np.vstack(canvas[:-1]), missing


if __name__ == '__main__':
    argv = sys.argv[1:]
    size = int(argv[argv.index('--tile') + 1]) if '--tile' in argv else 300
    out = argv[argv.index('--out') + 1] if '--out' in argv else DEFAULT_OUT
    if not (os.path.isdir(PANDA) or os.path.isdir(BLENDER)):
        sys.exit(f"没有渲染结果, 先跑 render_panda3d.py / render_blender.py (期望目录: {PANDA}, {BLENDER})")

    image, missing = build(size)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    # 用 PIL 存: 无损 optimize 比 cv2.imwrite 小 ~15%. 不做调色板量化——
    # 256 色会把天空和 depth 的渐变压出色带, 而这张图正是要展示深度的.
    Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).save(out, optimize=True)
    if missing:
        print(f"缺图 {len(missing)} 张 (已用占位块): {', '.join(missing)}")
    print(f"总览图 {image.shape[1]}x{image.shape[0]} -> {out}")
