'''
@Author: WANG Maonan
@Date: 2023-08-29 18:05:16
@Description: builder 基类
@LastEditTime: 2023-08-30 15:14:36
'''
from abc import ABC, abstractmethod

class BaseBuilder(ABC):
    @abstractmethod
    def create_objects(self) -> None:
        """创建场景内所有的 object
        """
        pass
    
    @abstractmethod
    def update_objects_state(self) -> None:
        """更新场景内所有 object 的信息
        1. 对于 vehicle 和 traffic light, 需要从 sumo 中获得信息来进行更新;
        2. 对于 aircraft, 每次 control 之后自动进行更新;
        """
        pass

    @abstractmethod
    def get_objects_infos(self) -> None:
        """返回场景内所有 object 的信息
        """
        pass

    @abstractmethod
    def control_objects(self) -> None:
        """控制场景内所有的 objects
        """
        pass