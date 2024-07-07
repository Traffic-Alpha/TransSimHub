'''
@Author: WANG Maonan
@Date: 2024-07-07 23:49:19
@Description: TSHub 包含 3D 场景的渲染
@LastEditTime: 2024-07-08 00:27:55
'''
from abc import ABC, abstractmethod

class BaseSumoEnvironment3D(ABC):

    @abstractmethod
    def reset(self):
        raise NotImplementedError
    
    @abstractmethod
    def step(self):
        raise NotImplementedError