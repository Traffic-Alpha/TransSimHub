'''
@Author: WANG Maonan
@Date: 2024-07-20 14:36:14
@Description: 
LastEditTime: 2025-03-31 14:39:06
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

from tshub.tshub_env3d.renderers.panda._showbase_instance import _ShowBaseInstance

@dataclass
class _BaseOffCameraMixin:
    camera_np: NodePath
    buffer: GraphicsOutput
    tex: Texture
    showbase_instance: _ShowBaseInstance

    def wait_for_ram_image(self, img_format: str, retries=100):
        """Attempt to acquire a graphics buffer.
        """
        # SceneSync._sync 在读回所有传感器之前, 已经对整个场景 renderFrame 过一次,
        # 因此通常此时本相机的 RAM image 已就绪. 所以先检查 mightHaveRamImage(),
        # 只有在缺失时才强制补渲一帧 —— 避免「每个 sensor 都白渲一整帧」的开销
        # (实测 720P 6 相机 116ms->54ms, ~2.2x). 补渲逻辑保留作为掉帧时的兜底:
        # 偶发丢帧 (尤其多 agent / 多实例初始化时) 仍可通过重试拿到图像.
        for i in range(retries):
            if self.tex.mightHaveRamImage(): # 检查 RAM 是否有图像
                break
            region = self.buffer.getDisplayRegion(0)
            region.window.engine.renderFrame()
            logger.debug(
                f"SIM: No image available (attempt {i}/{retries}), forcing a render"
            )

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