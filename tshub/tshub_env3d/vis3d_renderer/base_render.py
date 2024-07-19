'''
@Author: WANG Maonan
@Date: 2024-07-03 23:21:22
@Description: 3D 场景渲染, 主要逻辑为:
1. tshub env 在 step 之后, state 会包含当前场景所有的信息
2. BaseRender 根据当前的信息, 来渲染场景, 包括
    - 添加 node
    - 更新 node
    - 删除 node
@LastEditTime: 2024-07-13 23:56:56
'''
import numpy as np
from loguru import logger
from enum import IntEnum
from typing import Literal, Union
from dataclasses import dataclass
from abc import ABCMeta, abstractmethod

from ..vis3d_utils.coordinates import Pose
from ...utils.get_abs_path import get_abs_path

BACKEND_LITERALS = Literal[
    "pandagl",      # 使用 OpenGL 渲染
    "pandadx9",     # 使用 DirectX 9 渲染
    "pandagles",    # 使用 OpenGL ES 渲染，适用于较旧的移动设备
    "pandagles2",   # 使用 OpenGL ES 2 渲染，适用于较新的移动设备
    "p3headlessgl", # 使用一个不渲染图形的 OpenGL 上下文，适用于服务器端渲染或无头渲染
    "p3tinydisplay",# 使用 Panda3D 的 TinyDisplay 渲染器，一个非常基础的软件渲染后端
] # 只能是以上几种作为选择

class DEBUG_MODE(IntEnum):
    """The rendering debug information level.
    """
    SPAM = 1
    DEBUG = 2
    INFO = 3
    WARNING = 4
    ERROR = 5

class RendererNotSetUpWarning(UserWarning):
    """This occurs if a renderer is used without being set up.
    """

@dataclass(frozen=True)
class ShaderStepDependencyBase:
    """The base for shader dependencies.
    """
    
@dataclass(frozen=True)
class ShaderStepVariableDependency(ShaderStepDependencyBase):
    """The base for shader dependencies.
    """
    value: Union[int, float, bool, np.ndarray, list, tuple]
    script_variable_name: str

    def __post_init__(self):
        assert self.value, f"`{self.script_variable_name=}` cannot be None or empty."
        assert self.script_variable_name
        assert (
            0 < len(self.value) < 5
            if isinstance(self.value, (np.ndarray, list, tuple))
            else True
        )
        
@dataclass(frozen=True)
class ShaderStepBufferDependency(ShaderStepDependencyBase):
    """The base for shader dependencies.
    """
    buffer_id: str # TODO, 这里需要修改
    script_uniform_name: str

    def __post_init__(self):
        assert self.buffer_id, f"`{self.script_uniform_name=}` cannot be None or empty."
        assert self.script_uniform_name


@dataclass(frozen=True)
class ShaderStepCameraDependency(ShaderStepDependencyBase):
    """Forwards the texture from a given camera to the
    """
    camera_id: str
    script_variable_name: str

    def __post_init__(self):
        assert self.script_variable_name, "Variable name cannot be empty."
        assert (
            self.camera_id
        ), f"Camera id for {self.script_variable_name} cannot be None or empty."


class BaseRender(metaclass=ABCMeta):
    """The base class for rendering, 主要的功能是:
    1. setup -> 场景初始化, 包括路网, skybox 和 terrain
    2. 123
    3. 

    Returns:
        BaseRender:
    """
    def __init__(self) -> None:
        self._showbase_instance = None
        self.current_file_path = get_abs_path(__file__) # 文件路径转换

        self.map_center = None # 记录地图的中心位置
        self.map_radius = None

    @property
    @abstractmethod
    def id(self):
        """The id of the simulation rendered."""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_setup(self) -> bool:
        """If the renderer has been fully initialized."""
        raise NotImplementedError
    
    # ---------------- #
    # Step 1, 初始化场景
    # ---------------- #
    @abstractmethod
    def setup(self, scenario):
        """Initialize this renderer.
        """
        raise NotImplementedError


    # ---------------------------- #
    # Step 2, 3D 场景的信息交互和渲染
    # ---------------------------- #
    @abstractmethod
    def step(self):
        """对 TSHub 渲染一个步骤.
        """
        raise NotImplementedError


    # ---------------------------- #
    # Step 3, Gym Env Interface
    # ---------------------------- #
    @abstractmethod
    def reset(self):
        """Reset the render back to initialized state.
        """
        raise NotImplementedError

    @abstractmethod
    def teardown(self):
        """Clean up internal resources.
        """
        raise NotImplementedError

    @abstractmethod
    def destroy(self):
        """Destroy the renderer. Cleans up all remaining renderer resources.
        """
        raise NotImplementedError

    # ------------------- #
    # Other, 场景调试工具
    # ------------------- #
    @staticmethod
    def print_node_paths(nodepath, prefix='->') -> None:
        """定义一个递归函数来遍历和打印 node paths
        """
        logger.info(f'SIM: {prefix} {nodepath.getName()}')
        for child in nodepath.getChildren():
            BaseRender.print_node_paths(child, prefix + '  ')


    # @abstractmethod
    # def build_shader_step(
    #     self,
    #     name: str,
    #     fshader_path: Union[str, Path],
    #     dependencies: Collection[
    #         Union[ShaderStepCameraDependency, ShaderStepVariableDependency]
    #     ],
    #     priority: int,
    #     height: int,
    #     width: int,
    # ) -> None:
    #     """Generates a new shader camera."""
    #     raise NotImplementedError


    # @abstractmethod
    # def remove_buffer(self, buffer):
    #     """Remove the rendering buffer."""
    #     raise NotImplementedError