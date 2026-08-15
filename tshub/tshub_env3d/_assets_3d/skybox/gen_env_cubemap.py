'''
按 SceneLoader.SKY_COLORS 的 horizon/zenith 渐变生成天空 cubemap (6 面), 供 simplepbr IBL
环境光照使用. 与可见的程序化 skybox 保持一致的颜色. 每种天空一个目录 env_<sky>/{0..5}.png.

Panda cube face 顺序: 0=+X 1=-X 2=+Y 3=-Y 4=+Z 5=-Z. tshub 场景 Z-up, 故 +Z(4)=天顶, -Z(5)=地面向下.

用法: python gen_env_cubemap.py   (改了 SKY_COLORS 后重跑)
'''
import os
import numpy as np
import cv2

HERE = os.path.dirname(__file__)
N = 128  # 每面分辨率

# 天空环境光颜色 (RGB 0~255). 注: 这是给 IBL 用的「光照」天空, 天顶取较亮 (正午头顶天空本就亮),
# 使朝上的面 (车顶/路面, 即 BEV 视角) 受光充足; 不必与可见 skybox 的渐变完全一致.
SKY = {
    'day':  {'horizon': (185, 205, 222), 'zenith': (205, 216, 230), 'ground': (150, 150, 150)},
    'dust': {'horizon': (205, 188, 160), 'zenith': (210, 205, 200), 'ground': (140, 130, 120)},
}


def _grad(top, bot):
    t = np.linspace(0, 1, N)[:, None]
    row = (np.array(top) * (1 - t) + np.array(bot) * t)
    return np.repeat(row[:, None, :], N, axis=1).astype(np.uint8)


def main():
    for sky, c in SKY.items():
        hor, zen, gnd = np.array(c['horizon']), np.array(c['zenith']), np.array(c['ground'])
        side = _grad(zen, hor)  # 侧面: 上=天顶, 下=地平线
        faces = {0: side, 1: side, 2: side, 3: side,
                 4: np.full((N, N, 3), zen, np.uint8),   # +Z 天顶
                 5: np.full((N, N, 3), gnd, np.uint8)}    # -Z 向下 (地面反照)
        d = os.path.join(HERE, f'env_{sky}')
        os.makedirs(d, exist_ok=True)
        for i, im in faces.items():
            cv2.imwrite(os.path.join(d, f'{i}.png'), im[:, :, ::-1])  # RGB->BGR
        print(f'env_{sky}/ 6 面已生成')


if __name__ == '__main__':
    main()
