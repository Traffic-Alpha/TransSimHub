'''
@Author: WANG Maonan
@Date: 2024-07-13 20:53:01
@Description: 场景的同步, 根据 SUMO 的信息更新 panda3d
@LastEditTime: 2024-07-21 23:07:45
'''
import math
from loguru import logger

from ..traffic_elements.vehicle import Vehicle3DElement
from ..traffic_elements.traffic_signals import TLS3DElement
from ..traffic_elements.aircraft import Aircraft3DElement
from ...vis3d_utils.core_math import calculate_center_point, vec_to_radians, vec_2d

class SceneSync(object):
    def __init__(self, root_np, showbase_instance) -> None:
        self.root_np = root_np
        self.showbase_instance = showbase_instance

        # 记录场景中的 element
        self._vehicle_elements = {} # 加入渲染的车辆
        self._tls_elements = {} # 加入信号灯 (每一个 in road 会有一个), 这里信号灯没有实体, 只有 sensor
        self._aircraft_elements = {} # 目前 aircraft 没有实体, 只有摄像头


    def reset(self, tshub_init_obs) -> None:
        # 初始化车辆 & 关闭所有车辆的 sensors
        for veh_id, veh_info in self._vehicle_elements.items():
            print(1)
            
        self._vehicle_elements = {}
        
        # 初始化信号灯
        if not self._tls_elements: # 只需要加载一次即可
            for _tls_id, _tls_info in tshub_init_obs['tls'].items():
                _tls_in_roads_heading = _tls_info['in_roads_heading'] # 路口进入方向车道的角度
                _tls_in_road_stop_line = _tls_info['in_road_stop_line']

                # 按照 heading 角度从小到大排序
                sorted_road_ids = sorted(_tls_in_roads_heading, key=_tls_in_roads_heading.get)

                for _tls_road_index, _road_id in enumerate(sorted_road_ids):
                    _tls_element_id = f'{_tls_id}_{_tls_road_index}'
                    # 生成对应的信号灯
                    self._tls_elements[_tls_element_id] = TLS3DElement(
                        element_id=_tls_element_id,
                        element_position=calculate_center_point(_tls_in_road_stop_line[_road_id]),
                        element_heading=_tls_in_roads_heading[_road_id],
                        root_np=self.root_np,
                        showbase_instance=self.showbase_instance
                    ) # 记录对应的 tls 3d element
                    self._tls_elements[_tls_element_id].attach_sensors_to_element([
                        'junction_front_all', 'junction_front_vehicle',
                        'junction_back_all', 'junction_back_vehicle',
                    ])
                

    def _sync(self, tshub_obs) -> None:
        """Update the current state of the vehicles and signals within the renderer.
        根据当前的状况更新 render 的信息, 包含 vehicle, traffic signals
        """
        veh_ids = set() # 记录车辆的 id, 用于比较车辆的进入和驶出
        aircraft_ids = set() # 记录飞行器的 id, 用于比较飞行器的新增和离开

        sensors = {} # 记录传感器的数据, 作为 state 返回
        
        # ##########################
        # 在 render 中更新 tls 的信息
        # ##########################
        for _tls_id, _tls_element in self._tls_elements.items():
            # 这里路口传感器数量不会发生改变, 位置也不变, 因此只需要直接获取数据即可
            sensors[_tls_id] = _tls_element.get_sensor().copy()

        # ##############################
        # 在 render 中更新 aircraft 的信息
        # ##############################
        for aircraft_id, aircraft_info in tshub_obs['aircraft'].items():
            aircraft_ids.add(aircraft_id) # 记录当前场景下车辆的 id
            aircraft_pos=aircraft_info['position'] # 三维坐标

            aircraft_heading_radians=vec_to_radians(vec_2d(aircraft_info['heading'])) # 转换为度
            aircraft_heading = math.degrees(aircraft_heading_radians) % 360

            # 如果飞行器存在, 则更新飞行器上面的 camera 的位置
            if aircraft_id in self._aircraft_elements:
                self._aircraft_elements[aircraft_id].update_sensor(
                    new_position=aircraft_pos,
                    new_heading=aircraft_heading,
                ) # 更新摄像头位置
                sensors[aircraft_id] = self._aircraft_elements[aircraft_id].get_sensor() # 获得传感器数据
            
            # 如果飞行器不在场景, 则创建飞行器的 node
            else:
                self._aircraft_elements[aircraft_id] = Aircraft3DElement(
                    aircraft_id=aircraft_id,
                    aircraft_pos=aircraft_pos,
                    aircraft_heading=aircraft_heading,
                    root_np=self.root_np,
                    showbase_instance=self.showbase_instance
                ) # 创建飞行器的 element
                self._aircraft_elements[aircraft_id].attach_sensors_to_element([
                    'aircraft_all', 'aircraft_vehicle'
                ]) # 添加传感器

        # 查看哪些飞行器离开了路网
        # missing_vehicle_ids = set(self._vehicle_elements) - set(veh_ids)

        # ##############################
        # 在 render 中更新 vehicle 的信息
        # ##############################
        for veh_id, veh_info in tshub_obs['vehicle'].items():
            veh_ids.add(veh_id) # 记录当前场景下车辆的 id
            veh_pos=veh_info['position']
            veh_heading=veh_info['heading']
            veh_type=veh_info['vehicle_type']

            # 如果车辆存在, 则更新车辆的位置
            if veh_id in self._vehicle_elements:
                self._vehicle_elements[veh_id].update_node(veh_pos, veh_heading)
                self._vehicle_elements[veh_id].update_sensor() # 更新摄像头位置
                _sensor_data = self._vehicle_elements[veh_id].get_sensor() # 获得 sensor 的信息
                if _sensor_data: # 如果不是 None, 则添加到传感器的数据
                    sensors[veh_id] = _sensor_data.copy() # 得到传感器数据
            
            # 如果车辆不在场景, 则创建车辆的 node
            else:
                self._vehicle_elements[veh_id] = Vehicle3DElement(
                    veh_id=veh_id,
                    veh_type=veh_type,
                    veh_pos=veh_pos,
                    veh_heading=veh_heading,
                    veh_length=veh_info['length'],
                    root_np=self.root_np,
                    showbase_instance=self.showbase_instance
                ) # 创建车辆 elements
                self._vehicle_elements[veh_id].create_node() # 创建车辆的节点
                self._vehicle_elements[veh_id].begin_rendering_node() # 开始渲染车辆节点
                if veh_type == 'ego': # 给 ego vehicle 上面添加 sensor
                    self._vehicle_elements[veh_id].attach_sensors_to_element([
                        # 'front_left_all', 'front_right_all', 'front_all', # 前向摄像头
                        # 'back_left_all', 'back_right_all', 'back_all', # 后向摄像头
                        # 'front_left_vehicle', 'front_right_vehicle', 'front_vehicle', # 前向摄像头
                        # 'back_left_vehicle', 'back_right_vehicle', 'back_vehicle', # 后向摄像头
                        'bev_all', 'bev_vehicle', # 俯视摄像头
                    ])
        # 查看哪些车辆离开了路网
        missing_vehicle_ids = set(self._vehicle_elements) - set(veh_ids)

        
        # 删除离开路网的车辆
        for vid in missing_vehicle_ids:
            self._vehicle_elements[vid].remove_node()
            del self._vehicle_elements[vid]
            logger.info(f'SIM: 3D, Del vehicle {vid} since it leaves the scenario.')

        # for sig_id in missing_signal_ids:
        #     self.remove_signal_node(sig_id)
        return sensors