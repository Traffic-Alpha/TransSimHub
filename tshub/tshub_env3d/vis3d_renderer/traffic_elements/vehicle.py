'''
@Author: WANG Maonan
@Date: 2024-07-08 22:21:18
@Description: 3D 场景内的车辆
@LastEditTime: 2024-07-21 02:02:44
'''
import random
from loguru import logger
from typing import Tuple

from .base_element import BaseElement

# 导入传感器
from ..sensors.rgb_sensor import RGBSensor
from ...vis3d_utils.masks import CamMask
from ....utils.get_abs_path import get_abs_path

class Vehicle3DElement(BaseElement):
    current_file_path = get_abs_path(__file__)

    def __init__(
            self, 
            veh_id: str,
            veh_type: str,
            veh_pos: Tuple[float, float],
            veh_heading: float,
            veh_length: float,
            root_np, # showbase 的根节点
            showbase_instance # panda3d showbase, 单例模式 
        ) -> None:
        super().__init__(veh_id, veh_pos, veh_heading, veh_length, root_np, showbase_instance)
        self.veh_type = veh_type # 车辆的类型, 对 ego 车辆特殊处理
        self.veh_node_path = None # 记录这辆车的 node path
    
    # ###################
    # Vehicle Node 的更新
    # ###################
    def create_node(self) -> bool:
        """Create a vehicle node.
        """
        veh_model_path = self._select_vehicle_model() # 随机选择车辆的模型
        self.veh_node_path = self.showbase_instance.loader.loadModel(veh_model_path)
        self.get_node_dimensions(node_path=self.veh_node_path)
        self.veh_node_path.setName(f"vehicle-{self.element_id}")

        pose = self.get_element_pose_from_bumper() # 车辆坐标转换
        pos, heading = pose.as_panda3d() # 转换为位置和角度
        self.veh_node_path.setPosHpr(*pos, heading, 0, 0)
        self.veh_node_path.hide(CamMask.AllOn) # 首先不让所有相机看到
        self.veh_node_path.show(CamMask.VehMask) # 接着只让部分相机可以看到
        
        return True

    def _select_vehicle_model(self) -> str:
        """随机选择车辆的模型, ego vehicle 和 soical vehicle 的模型是不一样的
        """
        if 'ego' in self.veh_type:
            veh_list = ['AudiTT', 'FerrariF355']
            weights = [0, 1]
            selected_model = random.choices(veh_list, weights=weights, k=1)[0]
            return Vehicle3DElement.current_file_path(f"../../_assets_3d/vehicles/ego_vehicles/{selected_model}.bam")
        else:
            veh_list = [
                'BMWZ4', 'HyundaiKona', 'KiaXceed', 
                'LamborghiniUrus', 'MercedesCL', 'NIssanMurano', 
                'Peugeot208', 'volkswagenT-Roc'
            ]
            weights = [1/14, 1/14, 1/14, 1/2, 1/14, 1/14, 1/14, 1/14]
            selected_model = random.choices(veh_list, weights=weights, k=1)[0]
            return Vehicle3DElement.current_file_path(f"../../_assets_3d/vehicles/social_vehicles/{selected_model}.bam")


    def update_node(
            self, 
            veh_position:Tuple[float],
            veh_heading: float,
        ) -> None:
        """Move the specified vehicle node (更新车辆的位置)
        """
        if not self.veh_node_path: # 如果是 None, 则会出现提示
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.element_id}")
            return

        self.update_element_position_heading(veh_position, veh_heading) # 更新 vehicle element 的位置
        pose = self.get_element_pose_from_bumper() # 坐标转换
        pos, heading = pose.as_panda3d()
        self.veh_node_path.setPosHpr(*pos, heading, 0, 0)

    def remove_node(self) -> None:
        """Remove a vehicle node
        """
        if not self.veh_node_path:
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.element_id}")
            return
        self.veh_node_path.removeNode()
        # TODO, 同时删除所有的 sensor
        
    def begin_rendering_node(self) -> None:
        """Add the vehicle node to the scene graph
        """
        if not self.veh_node_path:
            logger.warning(f"SIM: Renderer ignoring invalid vehicle id: {self.element_id}")
            return
        
        # 连接到 TSHub Render 的根节点
        self.veh_node_path.reparentTo(self.root_np.find("**/vehicles"))
    
    # #################
    # 添加和更新 Sensors
    # #################
    def attach_sensor_to_element(self, sensor_type: str) -> None:
        sensor_configs = {
            'bev_all': {
                'camera_mask': (CamMask.VehMask | CamMask.GroundMask | CamMask.MapMask | CamMask.SkyBoxMask),
                'camera_type': 'Off_BEV_Camera'
            },
            'bev_vehicle': {
                'camera_mask': CamMask.VehMask,
                'camera_type': 'Off_BEV_Camera'
            },
            # --- 正前方 ---
            'front_all': {
                'camera_mask': (CamMask.VehMask | CamMask.GroundMask | CamMask.MapMask | CamMask.SkyBoxMask),
                'camera_type': 'Off_Front_Camera'
            },
            'front_vehicle': {
                'camera_mask': CamMask.VehMask,
                'camera_type': 'Off_Front_Camera'
            },
            # 正前方 (左侧)
            'front_left_all': {
                'camera_mask': (CamMask.VehMask | CamMask.GroundMask | CamMask.MapMask | CamMask.SkyBoxMask),
                'camera_type': 'Off_FrontLeft_Camera'
            },
            'front_left_vehicle': {
                'camera_mask': CamMask.VehMask,
                'camera_type': 'Off_FrontLeft_Camera'
            },
            # 正前方 (右侧)
            'front_right_all': {
                'camera_mask': (CamMask.VehMask | CamMask.GroundMask | CamMask.MapMask | CamMask.SkyBoxMask),
                'camera_type': 'Off_FrontRight_Camera'
            },
            'front_right_vehicle': {
                'camera_mask': CamMask.VehMask,
                'camera_type': 'Off_FrontRight_Camera'
            },
            # --- 正后方 ---
            'back_all': {
                'camera_mask': (CamMask.VehMask | CamMask.GroundMask | CamMask.MapMask | CamMask.SkyBoxMask),
                'camera_type': 'Off_Back_Camera'
            },
            'back_vehicle': {
                'camera_mask': CamMask.VehMask,
                'camera_type': 'Off_Back_Camera'
            },
            # 正前方 (左侧)
            'back_left_all': {
                'camera_mask': (CamMask.VehMask | CamMask.GroundMask | CamMask.MapMask | CamMask.SkyBoxMask),
                'camera_type': 'Off_BackLeft_Camera'
            },
            'back_left_vehicle': {
                'camera_mask': CamMask.VehMask,
                'camera_type': 'Off_BackLeft_Camera'
            },
            # 正前方 (右侧)
            'back_right_all': {
                'camera_mask': (CamMask.VehMask | CamMask.GroundMask | CamMask.MapMask | CamMask.SkyBoxMask),
                'camera_type': 'Off_BackRight_Camera'
            },
            'back_right_vehicle': {
                'camera_mask': CamMask.VehMask,
                'camera_type': 'Off_BackRight_Camera'
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
            init_element_pose=self.get_element_pose_from_bumper(),
            element_dimensions=(self.length, self.width, self.height),
            fig_width=360, # 360, 480
            fig_height=240, # 240, 320
            fig_resolution=0.2,
            camera_type=config['camera_type']
        )
        self.sensors[sensor_type] = veh_rgb_sensor

    def update_sensor(self) -> None:
        """更新 sensor 的数据
        """
        for _sensor_id, _sensor in self.sensors.items():
            # 更新 camera 的位置, 车辆的 sensor 跟着车辆跑就行
            _sensor.step(self.get_element_pose_from_bumper())
    
    def get_sensor(self):
        sensor_data = {}
        for _sensor_id, _sensor in self.sensors.items():
            ego_rgb = _sensor()
            sensor_data[_sensor_id] = ego_rgb
        return sensor_data