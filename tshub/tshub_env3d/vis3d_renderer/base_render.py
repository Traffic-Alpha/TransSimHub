'''
@Author: WANG Maonan
@Date: 2024-07-03 23:21:22
@Description: 3D 场景渲染, 主要逻辑为:
1. tshub env 在 step 之后, state 会包含当前场景所有的信息
2. BaseRender 根据当前的信息, 来渲染场景, 包括
    - 添加 node
    - 更新 node
    - 删除 node
@LastEditTime: 2024-07-08 23:35:31
'''
import numpy as np
from enum import IntEnum
from typing import Literal, Union
from dataclasses import dataclass
from abc import ABCMeta, abstractmethod

from ..vis3d_utils.coordinates import Pose

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
    """The base class for rendering

    Returns:
        BaseRender:
    """
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
        """Initialize this renderer."""
        raise NotImplementedError

    # ---------------------------- #
    # Step 2, 3D 场景的信息交互和渲染
    # ---------------------------- #
    @abstractmethod
    def render(self):
        """Render the scene graph of the simulation.
        """
        raise NotImplementedError

    @abstractmethod
    def sync(self, sim_frame):
        """Update the current state of the vehicles within the renderer.
        """
        raise NotImplementedError

    @abstractmethod
    def step(self):
        """对 TSHub 渲染一个步骤.
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        """Reset the render back to initialized state.
        """
        raise NotImplementedError

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


    # @abstractmethod
    # def teardown(self):
    #     """Clean up internal resources."""
    #     raise NotImplementedError

    # @abstractmethod
    # def destroy(self):
    #     """Destroy the renderer. Cleans up all remaining renderer resources."""
    #     raise NotImplementedError