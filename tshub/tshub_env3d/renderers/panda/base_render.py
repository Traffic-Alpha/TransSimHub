'''
@Author: WANG Maonan
@Date: 2024-07-03 23:21:22
@Description: Panda 渲染后端用到的配置枚举 (调试级别 / 渲染后端字面量).
渲染后端的接口契约见 tshub_env3d.scene.RendererBackend; 具体实现见 tshub_render.TSHubRenderer.
@LastEditTime: 2026-07-10
'''
from enum import IntEnum
from typing import Literal

BACKEND_LITERALS = Literal[
    "pandagl",      # 使用 OpenGL 渲染
    "pandadx9",     # 使用 DirectX 9 渲染
    "pandagles",    # 使用 OpenGL ES 渲染，适用于较旧的移动设备
    "pandagles2",   # 使用 OpenGL ES 2 渲染，适用于较新的移动设备
    "p3headlessgl", # 使用一个不渲染图形的 OpenGL 上下文，适用于服务器端渲染或无头渲染
] # 只能是以上几种作为选择


class DEBUG_MODE(IntEnum):
    """The rendering debug information level.
    """
    SPAM = 1
    DEBUG = 2
    INFO = 3
    WARNING = 4
    ERROR = 5
