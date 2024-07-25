'''
@Author: WANG Maonan
@Date: 2024-07-13 22:14:31
@Description: 仿真器中飞行器的可视化 (在飞行器上安装摄像头)
@LastEditTime: 2024-07-26 02:06:22
'''
from typing import Tuple

from .base_element import BaseElement

# 导入传感器
from ..sensors.rgb_sensor import RGBSensor
from ...vis3d_utils.masks import CamMask
from ....utils.get_abs_path import get_abs_path

class Aircraft3DElement(BaseElement):
    current_file_path = get_abs_path(__file__)

    def __init__(
            self, 
            aircraft_id: str,
            aircraft_pos: Tuple[float, float],
            aircraft_heading: float,
            aircraft_length: float = None,
            root_np = None, # showbase 的根节点
            showbase_instance = None, # panda3d showbase, 单例模式 
        ) -> None:
        super().__init__(aircraft_id, aircraft_pos, aircraft_heading, aircraft_length, root_np, showbase_instance)
    
    # ###########################################
    # Aircraft Node 的更新 (暂时没有 Aircraft 的模型)
    # ###########################################
    def create_node(self) -> None:
        pass

    def update_node(self) -> None:
        pass
        
    def begin_rendering_node(self) -> None:
        pass
    
    # #################
    # 添加和更新 Sensors
    # #################
    def attach_sensor_to_element(self, sensor_type: str) -> None:
        sensor_configs = {
            'aircraft_all': {
                'camera_mask': (CamMask.VehMask | CamMask.GroundMask | CamMask.MapMask | CamMask.SkyBoxMask),
                'camera_type': 'Off_Aircraft_Camera'
            },
            'aircraft_vehicle': {
                'camera_mask': CamMask.VehMask,
                'camera_type': 'Off_Aircraft_Camera'
            },
        }

        config = sensor_configs.get(sensor_type)
        if config is None:
            raise ValueError(f"Unknown sensor type: {sensor_type}")

        _camera_name = BaseElement._gen_sensor_name(
            base_name=sensor_type, # sensor 类型
            vehicle_id=self.element_id, # sensor 放在哪一个 element 上面
        )

        veh_rgb_sensor = RGBSensor(
            camera_name=_camera_name,
            camera_mask=config['camera_mask'],
            showbase_instance=self.showbase_instance,
            root_np=self.root_np,
            init_element_pose=self.get_element_pose_from_center(),
            element_dimensions=(self.length, self.width, self.height),
            fig_width=360, # 360, 480
            fig_height=240, # 240, 320
            fig_resolution=0.2,
            camera_type=config['camera_type']
        )
        self.sensors[sensor_type] = veh_rgb_sensor

    def update_sensor(
            self,
            new_position:Tuple[float, float], 
            new_heading:float
        ) -> None:
        """更新 sensor 的位置, 这里需要跟随无人机的位置移动
        """
        self.update_element_position_heading(new_position, new_heading)
        for _sensor_id, _sensor in self.sensors.items():
            _sensor.step(self.get_element_pose_from_center())
    
    def get_sensor(self):
        sensor_data = {}
        for _sensor_id, _sensor in self.sensors.items():
            ego_rgb = _sensor()
            sensor_data[_sensor_id] = ego_rgb
        return sensor_data