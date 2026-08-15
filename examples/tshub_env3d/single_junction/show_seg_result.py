'''
@Author: WANG Maonan
@Date: 2026-07-10
@Description: 语义分割结果可视化 —— 跑一对 rgb + seg 传感器, 把 seg 的单通道 label-id
反上色成彩色, 与 rgb 并排存图, 并另存一张类别调色板图例.

用法 (需 SUMO_HOME 与 DISPLAY):
  python examples/tshub_env3d/single_junction/show_seg_result.py                 # junction_bev + vehicle 两个视角
  python examples/tshub_env3d/single_junction/show_seg_result.py --view junction_bev
输出: _seg_vis/<view>/{NNN.png(左rgb|右seg), _legend.png}

注: Panda 关闭时 ShowBase 会退出进程, 故每个视角在独立子进程中跑.
'''
import os
import sys
import random
import subprocess

import cv2
import numpy as np
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env3d.tshub_env3d import Tshub3DEnvironment
from tshub.tshub_env3d.scene import seg_label_to_color, SEG_CLASSES

path_convert = get_abs_path(__file__)
# 与 Phase 0 benchmark 用同一套场景 (city-builder 风格 + 车道箭头, 由 build_static_scene.py 生成)
SCENE = path_convert("../phase0_render_benchmark/_scene/glb")
RENDER_PRESET = "720P_SQUARE"  # 与 benchmark 一致 (720x720 方形)
OUT = path_convert("./_seg_vis")

# 视角 -> (传感器配置, 载体 element_id, rgb/seg 传感器名, 是否需要飞行器)
VIEWS = {
    'junction_bev': {
        'sensor_config': {'tls': {'J3': {
            'sensor_types': ['junction_bev_rgb', 'junction_bev_seg'], 'junction_bev_height': 70}}},
        'element': 'J3_bev', 'rgb': 'junction_bev_rgb', 'seg': 'junction_bev_seg',
    },
    'vehicle': {
        'sensor_config': {'vehicle': {'E0__0__taxi.0': {
            'sensor_types': ['front_rgb', 'front_seg']}}},
        'element': 'E0__0__taxi.0', 'rgb': 'front_rgb', 'seg': 'front_seg',
    },
}


def make_legend() -> np.ndarray:
    """生成类别调色板图例 (RGB, H×W×3)."""
    rows = len(SEG_CLASSES)
    img = np.full((rows * 30 + 12, 260, 3), 30, np.uint8)  # 深色底
    for i, (name, color) in enumerate(SEG_CLASSES):
        y = 8 + i * 30
        img[y:y + 22, 8:40] = color  # 颜色块 (RGB)
        cv2.putText(img, f"{i}  {name}", (48, y + 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (235, 235, 235), 1, cv2.LINE_AA)
    return img


def run_one(view: str) -> None:
    set_logger(path_convert('./'), terminal_log_level='ERROR')
    random.seed(7)
    cfg = VIEWS[view]
    _missing = [f for f in ("map.glb", "ground.glb", "lane_lines.glb")
                if not os.path.exists(os.path.join(SCENE, f))]
    if _missing:
        sys.exit(f"缺少场景文件 {_missing} @ {SCENE}\n"
                 "请先运行: python examples/tshub_env3d/phase0_render_benchmark/build_static_scene.py")
    out_dir = os.path.join(OUT, view)
    os.makedirs(out_dir, exist_ok=True)
    # 图例先存 (env.close 会 sys.exit)
    cv2.imwrite(os.path.join(out_dir, "_legend.png"), make_legend()[:, :, ::-1])

    env = Tshub3DEnvironment(
        sumo_cfg=path_convert("./sumo_net/single_junction.sumocfg"),
        scenario_glb_dir=SCENE, renderer='panda',
        is_map_builder_initialized=False, is_vehicle_builder_initialized=True,
        is_aircraft_builder_initialized=False, is_traffic_light_builder_initialized=True,
        tls_ids=['J3'], vehicle_action_type='lane_continuous_speed',
        use_gui=False, num_seconds=300, collision_action="warn", sumo_seed='7',
        preset=RENDER_PRESET, render_mode="offscreen", rendering_backend="pandagl",
        sensor_config=cfg['sensor_config'],
    )
    env.reset()
    saved = 0
    for i in range(80):
        _, _, _, done, sensor_data = env.step(
            {'vehicle': dict(), 'tls': {'J3': random.randint(0, 3)}})
        cams = (sensor_data or {}).get(cfg['element'])
        if not cams:
            continue
        rgb, seg = cams.get(cfg['rgb']), cams.get(cfg['seg'])
        if rgb is None or seg is None:
            continue
        seg_rgb = seg_label_to_color(seg)             # (H,W) label -> (H,W,3) 彩色
        comp = np.concatenate([rgb, seg_rgb], axis=1) # 左 rgb | 右 seg
        cv2.imwrite(os.path.join(out_dir, f"{i:03d}.png"), comp[:, :, ::-1])  # RGB->BGR
        saved += 1
        if saved >= 20 or done:
            break
    print(f"[{view}] 存了 {saved} 张对比图 -> {out_dir} (含 _legend.png)")
    sys.stdout.flush()
    try:
        env.close()
    except SystemExit:
        pass


if __name__ == '__main__':
    argv = sys.argv[1:]
    view = argv[argv.index('--view') + 1] if '--view' in argv else None
    if '--_worker' in argv:
        run_one(argv[argv.index('--_worker') + 1])
    elif view:
        subprocess.run([sys.executable, __file__, '--_worker', view], check=False)
    else:
        for v in VIEWS:  # 每个视角一个子进程 (Panda 关闭会退出进程)
            print(f"=== {v} ===")
            subprocess.run([sys.executable, __file__, '--_worker', v], check=False)
        print(f"done. 见 {OUT}/<view>/")
