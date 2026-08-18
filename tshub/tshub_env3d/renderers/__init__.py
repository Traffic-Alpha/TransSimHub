'''
@Description: 渲染后端集合. 每个后端实现 core.RendererBackend.

当前在线后端只有 Panda3D (实时, 供 loop 内感知). 离线写实渲染 (Blender/Cycles)
是独立的离线路径, 不走这个 create_renderer 工厂.

通过 create_renderer 按名称选择后端; 采用懒加载, 只在选用某后端时才 import 其依赖.
'''
from ..core import RendererBackend

AVAILABLE_RENDERERS = ('panda',)


def create_renderer(renderer: str = 'panda', **kwargs) -> RendererBackend:
    """根据名称创建渲染后端.

    Args:
        renderer (str): 渲染后端名称, 见 AVAILABLE_RENDERERS. Defaults to 'panda'.
        **kwargs: 传给具体后端构造函数的参数 (各后端按需取用, 多余的会被忽略).
    """
    if renderer == 'panda':
        from .panda.tshub_render import TSHubRenderer
        return TSHubRenderer(**kwargs)
    raise ValueError(
        f"Unknown renderer '{renderer}', choose from {AVAILABLE_RENDERERS}."
    )
