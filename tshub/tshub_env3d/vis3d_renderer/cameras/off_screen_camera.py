'''
@Author: WANG Maonan
@Date: 2024-07-07 22:04:09
@Description: 创建 Off-Screen Camera, 在 Sensor 中会具体定义 Camera 的具体使用
@LastEditTime: 2024-07-09 18:03:13
'''
import numpy as np

from typing import Tuple
from loguru import logger
from dataclasses import dataclass
from abc import ABCMeta, abstractmethod

from panda3d.core import (
    GraphicsOutput,
    NodePath,
    Texture,
    Vec3,
    LQuaternionf
)

from ...vis3d_utils.coordinates import Pose

@dataclass
class OffscreenCamera(metaclass=ABCMeta):
    """A camera used for rendering images to a graphics buffer.
    """
    renderer: None

    @abstractmethod
    def wait_for_ram_image(self, img_format: str, retries=100):
        """Attempt to acquire a graphics buffer.
        """
        # Rarely, we see dropped frames where an image is not available
        # for our observation calculations.
        #
        # We've seen this happen fairly reliable when we are initializing
        # a multi-agent + multi-instance simulation.
        #
        # To deal with this, we can try to force a render and block until
        # we are fairly certain we have an image in ram to return to the user
        raise NotImplementedError

    @abstractmethod
    def update(self, *args, **kwargs):
        """Update the location of the camera.
        Args:
            pose:
                The pose of the camera target.
            height:
                The height of the camera above the camera target.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def image_dimensions(self) -> Tuple[int, int]:
        """The dimensions of the output camera image.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def position(self) -> Tuple[float, float, float]:
        """The position of the camera.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def heading(self) -> float:
        """The heading of this camera.
        """
        raise NotImplementedError

    @abstractmethod
    def teardown(self):
        """Clean up internal resources.
        """
        raise NotImplementedError
    
@dataclass
class _P3DCameraMixin:
    camera_np: NodePath
    buffer: GraphicsOutput
    tex: Texture

    def wait_for_ram_image(self, img_format: str, retries=100):
        """Attempt to acquire a graphics buffer.
        """
        # Rarely, we see dropped frames where an image is not available
        # for our observation calculations.
        #
        # We've seen this happen fairly reliable when we are initializing
        # a multi-agent + multi-instance simulation.
        #
        # To deal with this, we can try to force a render and block until
        # we are fairly certain we have an image in ram to return to the user
        for i in range(retries):
            if self.tex.mightHaveRamImage():
                break
            logger.debug(
                f"SIM: No image available (attempt {i}/{retries}), forcing a render"
            )
            region = self.buffer.getDisplayRegion(0)
            region.window.engine.renderFrame()

        assert self.tex.mightHaveRamImage()
        ram_image = self.tex.getRamImageAs(img_format)
        assert ram_image is not None # 必须要返回一个 image
        return ram_image

    @property
    def image_dimensions(self):
        """The dimensions of the output camera image.
        """
        return (self.tex.getXSize(), self.tex.getYSize())

    @property
    def position(self) -> Tuple[float, float, float]:
        """The position of the camera.
        """
        raise NotImplementedError()

    @property
    def padding(self) -> Tuple[int, int, int, int]:
        """The padding on the image. This follows the "css" convention: (top, left, bottom, right).
        """
        return self.tex.getPadYSize(), self.tex.getPadXSize(), 0, 0

    @property
    def heading(self) -> float:
        """The heading of this camera.
        """
        return np.radians(self.camera_np.getH())

    def teardown(self):
        """Clean up internal resources.
        """
        self.camera_np.removeNode()
        region = self.buffer.getDisplayRegion(0)
        region.window.clearRenderTextures()
        self.buffer.removeAllDisplayRegions()
        getattr(self, "renderer").remove_buffer(self.buffer)
        
@dataclass
class P3DOffscreenCamera(_P3DCameraMixin, OffscreenCamera):
    """A camera used for rendering images to a graphics buffer.
    """
    def update(self, pose: Pose, height: float, *args, **kwargs):
        """Update the location of the camera (这里 Update 可以使得 camera 跟踪车辆或是其他的 object).
        Args:
            pose:
                The pose of the camera target.
            height:
                The height of the camera above the camera target.
        """
        pos, heading = pose.as_panda3d()
        # 俯视的角度
        self.camera_np.setPos(pos[0], pos[1], height)
        self.camera_np.lookAt(*pos)
        self.camera_np.setH(heading) # 航向角

        # self.camera_np.setPos(pos[0], pos[1], 5)
        # self.camera_np.lookAt(pos[0], pos[1]+20, pos[2]+2)
        # self.camera_np.setH(heading) # 航向角
        # self.camera_np.setP(-1) # 俯仰角, 俯仰角的正向通常是物体的上方, 负向是物体的下方

    @property
    def position(self) -> Tuple[float, float, float]:
        return self.camera_np.getPos()