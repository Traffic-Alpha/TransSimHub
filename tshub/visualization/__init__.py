'''
@Author: WANG Maonan
@Date: 2023-11-12 16:19:00
@Description: TransSimHub 的可视化, 按「可视化范围」分层:
- micro: 局部视角 (跟车 / 路口), 画到单车粒度, 无头且不需要 GPU;
- meso : 全网中观大屏 (浏览器), 只看路段/车道的拥堵, 不到车辆粒度.
另外 tshub.tshub_env3d 提供 3D 传感器图像 (车载 / 路口 / UAV 相机).
@LastEditTime: 2026-08-12 10:00:00
'''
