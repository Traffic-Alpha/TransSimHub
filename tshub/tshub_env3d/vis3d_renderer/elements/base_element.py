'''
@Author: WANG Maonan
@Date: 2024-07-08 21:51:45
@Description: Base 3D Elements, 主要包含以下的方法:
-> 在 render 的 root node path 上添加 node
--> create node
--> update node
--> remove node
--> begin render node
-> 在 node 上添加传感器
@LastEditTime: 2024-07-08 23:12:34
'''
from abc import ABC, abstractmethod

class BaseElement(ABC):
    def __init__(
            self,
            tshub_render,
        ) -> None:
        super().__init__()
        self.tshub_render = tshub_render

    @abstractmethod
    def create_node(self):
        raise NotImplementedError

    @abstractmethod
    def update_node(self):
        raise NotImplementedError

    @abstractmethod
    def remove_node(self):
        raise NotImplementedError

    @abstractmethod
    def begin_rendering_node(self):
        raise NotImplementedError