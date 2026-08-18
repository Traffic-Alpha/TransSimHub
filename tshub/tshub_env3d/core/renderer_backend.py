'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 渲染后端接口 (tshub3d 与具体渲染引擎之间的契约).

放在 scene/ 根目录: 它既不属于「场景状态」也不属于某个后端, 而是两者之间的边界.
在线后端 (Panda3D) 实现它, 供 Tshub3DEnvironment 每步调用; 离线高精度渲染
(Blender) 不实现它 —— 那条路径是「导出剧集数据 -> 后台批量渲染」, 见 scene/export/.
@LastEditTime: 2026-08-15
'''
from abc import ABC, abstractmethod
from typing import Any

from .state.scene_elements import SceneFrame, SceneStatic


class RendererBackend(ABC):
    """渲染后端接口. 任何渲染引擎 (Panda3D / PyTorch3D / moderngl / ...) 实现它,
    即可被 Tshub3DEnvironment 使用.

    约定:
    - 场景静态资源 (地图 glb、天空、灯光等) 的加载在后端构造时完成;
    - reset() 接收 SceneStatic, 重置动态物体并准备好路口等静态相机 rig;
    - sync() 接收一帧 SceneFrame, 完成「增删改物体 -> 渲染 -> 读回传感器数据」;
    - 传感器数据的结构 (例如 {element_id: {camera_name: image}}) 由后端定义, 上层不解释.
    """

    @abstractmethod
    def reset(self, static: SceneStatic) -> None:
        """重置渲染场景到初始状态 (清空动态节点, 建立静态相机 rig)."""
        raise NotImplementedError

    @abstractmethod
    def sync(self, frame: SceneFrame, should_count_vehicles: bool = False) -> Any:
        """根据一帧 SceneFrame 更新场景并渲染, 返回传感器数据.

        should_count_vehicles 为 True 时, 额外返回用于离线渲染 (如 Blender) 的车辆信息.
        """
        raise NotImplementedError

    @abstractmethod
    def destroy(self) -> None:
        """销毁渲染器, 释放资源."""
        raise NotImplementedError
