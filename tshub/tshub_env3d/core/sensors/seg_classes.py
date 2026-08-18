'''
@Author: WANG Maonan
@Date: 2026-07-10
@Description: 渲染器无关的语义分割类别定义 (id / 名称 / 调色板颜色) + 颜色<->label 转换.

配色参考 CARLA / Cityscapes 驾驶场景分割的标准调色板 (低饱和), 方便直接对接
mmsegmentation / Cityscapes 风格的训练流程. seg 传感器输出单通道 label-id 图 (H,W uint8),
本模块的 SEG_CLASSES 同时给出 id<->名称<->颜色 的映射 (色板), 供可视化/反查.
'''
import numpy as np

# (类别名, RGB 颜色) —— 列表下标即 class id (0 = unlabeled/背景)
SEG_CLASSES = [
    ('unlabeled', (0,   0,   0)),
    ('road',      (128, 64,  128)),  # 路面 (road_map)
    ('lane',      (157, 234, 50)),   # 车道分隔线 (lane_lines)
    ('road_edge', (180, 165, 180)),  # 道路边界线/路缘 (road_lines); CARLA GuardRail 色
    ('building',  (70,  70,  70)),
    ('ground',    (145, 170, 100)),  # 草地/地面 (CARLA terrain 标准色)
    ('sky',       (70,  130, 180)),
    ('vehicle',   (0,   0,   142)),
    ('aircraft',  (170, 120, 50)),   # 无标准类, 取 CARLA Dynamic 色 (动态目标代理)
    ('pole',      (153, 153, 153)),  # 路灯/杆状街道设施; CARLA/Cityscapes Pole 色
]

SEG_NAME_TO_ID = {name: i for i, (name, _) in enumerate(SEG_CLASSES)}
SEG_ID_TO_NAME = {i: name for i, (name, _) in enumerate(SEG_CLASSES)}
SEG_ID_TO_COLOR = {i: color for i, (_, color) in enumerate(SEG_CLASSES)}
SEG_NAME_TO_COLOR = {name: color for name, color in SEG_CLASSES}
# 供渲染后端使用的「语义类 -> 归一化 RGBA (0~1)」颜色 (不含 unlabeled)
SEG_RENDER_COLORS = {
    name: (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0, 1.0)
    for name, c in SEG_CLASSES if name != 'unlabeled'
}


def seg_label_to_color(label: np.ndarray) -> np.ndarray:
    """把单通道 label-id 图 (H,W) 反上色成 RGB 彩色图 (H,W,3, uint8), 用于可视化.

    是 seg_color_to_label 的逆操作 (按 SEG_CLASSES 调色板把每个 id 映射回颜色).
    """
    color = np.zeros((*label.shape[:2], 3), dtype=np.uint8)
    for i, (_, c) in enumerate(SEG_CLASSES):
        color[label == i] = c
    return color


def seg_color_to_label(rgb_image: np.ndarray) -> np.ndarray:
    """把 seg 相机渲染出的纯色分割图 (H,W,3, RGB) 转成单通道 label-id 图 (H,W, uint8).

    seg 相机关闭了 MSAA, 每个像素恰为某个类别的调色板纯色, 故按颜色精确反查即可.
    未匹配到任何类别的像素 (理论上不应出现) 保持 0 (unlabeled).
    """
    r, g, b = rgb_image[:, :, 0], rgb_image[:, :, 1], rgb_image[:, :, 2]
    label = np.zeros(rgb_image.shape[:2], dtype=np.uint8)
    for i, (_, color) in enumerate(SEG_CLASSES):
        if i == 0:  # unlabeled 就是默认 0, 不用匹配
            continue
        label[(r == color[0]) & (g == color[1]) & (b == color[2])] = i
    return label
