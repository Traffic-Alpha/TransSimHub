'''
@Author: WANG Maonan
@Date: 2026-08-11 10:00:00
@Description: 中观交通大屏 (实时). 与 tshub_env / tshub_env3d 解耦, 只吃 obs 里的数据.
@LastEditTime: 2026-08-11 10:00:00
'''
from .server import DashboardServer
from .payload import build_static_payload, build_frame_payload, encode_image

__all__ = ['DashboardServer', 'build_static_payload', 'build_frame_payload', 'encode_image']
