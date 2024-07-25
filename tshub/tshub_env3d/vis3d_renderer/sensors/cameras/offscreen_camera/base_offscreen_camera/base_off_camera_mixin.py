'''
@Author: WANG Maonan
@Date: 2024-07-20 14:36:14
@Description: 
@LastEditTime: 2024-07-26 03:04:53
'''
import numpy as np

from typing import Tuple
from loguru import logger
from dataclasses import dataclass

from panda3d.core import (
    GraphicsOutput,
    NodePath,
    Texture,
)

from ......vis3d_renderer._showbase_instance import _ShowBaseInstance

@dataclass
class _BaseOffCameraMixin:
    camera_np: NodePath
    buffer: GraphicsOutput
    tex: Texture
    showbase_instance: _ShowBaseInstance

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

    def teardown(self) -> None:
        """Clean up internal resources.
        """
        self.camera_np.removeNode()
        region = self.buffer.getDisplayRegion(0)
        region.window.clearRenderTextures()
        self.buffer.removeAllDisplayRegions()
        self.showbase_instance.graphicsEngine.removeWindow(self.buffer)