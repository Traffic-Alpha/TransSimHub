'''
@Author: WANG Maonan
@Date: 2024-07-20 14:34:17
@Description: BaseOffscreenCamera Class
@LastEditTime: 2024-07-20 15:34:05
'''
from typing import Tuple
from dataclasses import dataclass
from abc import ABCMeta, abstractmethod

@dataclass
class BaseOffscreenCamera(metaclass=ABCMeta):
    """A camera used for rendering images to a graphics buffer.
    """

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
    def init_pos(self, *args, **kwargs):
        """初始化相机的位置
        """
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