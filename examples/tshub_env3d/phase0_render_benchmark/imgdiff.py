'''对比 _outputs 与 _baseline_outputs 的同名图, 报告平均绝对像素差 (0=完全一致).
用于重构后的视觉回归: 应为 pixel-identical 的改动 diff≈0; MSAA 等有意改动 diff 小且集中在边缘.
'''
import os, sys
import numpy as np
import cv2

base_dir = os.path.join(os.path.dirname(__file__), '_baseline_outputs')
new_dir = os.path.join(os.path.dirname(__file__), '_outputs')

rows = []
for root, _, files in os.walk(base_dir):
    for fn in files:
        if not fn.endswith('.png'):
            continue
        rel = os.path.relpath(os.path.join(root, fn), base_dir)
        p_new = os.path.join(new_dir, rel)
        if not os.path.exists(p_new):
            rows.append((rel, 'MISSING', 0))
            continue
        a = cv2.imread(os.path.join(base_dir, rel)).astype(np.float32)
        b = cv2.imread(p_new).astype(np.float32)
        if a.shape != b.shape:
            rows.append((rel, f'SHAPE {a.shape}!={b.shape}', 0))
            continue
        mad = float(np.mean(np.abs(a - b)))
        pct = float(np.mean(np.abs(a - b) > 2) * 100)  # 差异>2 的像素占比
        rows.append((rel, f'MAD={mad:6.3f}', pct))

rows.sort(key=lambda r: r[0])
print(f"{'image':<60}{'diff':>16}{'%px>2':>8}")
print('-' * 84)
for rel, d, pct in rows:
    print(f"{rel:<60}{d:>16}{pct:>7.2f}%")
mads = [float(d.split('=')[1]) for _, d, _ in rows if d.startswith('MAD')]
if mads:
    print(f"\n平均 MAD={np.mean(mads):.3f}  最大 MAD={np.max(mads):.3f}  (0=逐像素一致)")
