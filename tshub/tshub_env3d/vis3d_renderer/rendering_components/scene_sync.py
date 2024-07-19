'''
@Author: WANG Maonan
@Date: 2024-07-13 20:53:01
@Description: 场景的同步, 根据 SUMO 的信息更新 panda3d
@LastEditTime: 2024-07-19 18:06:27
'''
from loguru import logger

from ..traffic_elements.vehicle import Vehicle3DElement
from ..traffic_elements.traffic_signals import TLS3DElement

class SceneSync(object):
    def __init__(self, root_np, showbase_instance) -> None:
        self.root_np = root_np
        self.showbase_instance = showbase_instance

        # 记录场景中的 element
        self._vehicle_elements = {} # 加入渲染的车辆

        # 初始化路口的摄像头


    def reset(self) -> None:
        self._vehicle_elements = {}

    def _sync(self, tshub_obs) -> None:
        """Update the current state of the vehicles and signals within the renderer.
        根据当前的状况更新 render 的信息, 包含 vehicle, traffic signals
        """
        signal_ids = set() # 记录路口的信号灯 id
        veh_ids = set() # 记录车辆的 id, 用于比较车辆的进入和驶出

        sensors = {} # 记录传感器的数据, 作为 state 返回
        
        # 在 render 中更新 vehicle 的信息
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
                    # 这里可以根据参数选择添加合适的传感器, 传感器需要有不同的类型
                    self._vehicle_elements[veh_id].attach_bev_all_sensor_to_element()
                    self._vehicle_elements[veh_id].attach_front_all_sensor_to_element()


            # traffic signal 的颜色绘制在停车线上面
            # elif isinstance(actor_state, SignalState):
            #     signal_ids.add(actor_id)
            #     color = signal_state_to_color(actor_state.state)
            #     if actor_id not in self._signal_nodes:
            #         self.create_signal_node(actor_id, actor_state.stopping_pos, color)
            #         self.begin_rendering_signal(actor_id)
            #     else:
            #         self.update_signal_node(actor_id, actor_state.stopping_pos, color)

        # 查看哪些车辆离开了路网
        missing_vehicle_ids = set(self._vehicle_elements) - set(veh_ids)
        # missing_signal_ids = set(self._signal_nodes) - signal_ids
        
        # 删除离开路网的车辆
        for vid in missing_vehicle_ids:
            self._vehicle_elements[vid].remove_node()
            del self._vehicle_elements[vid]
            logger.info(f'SIM: 3D, Del vehicle {vid} since it leaves the scenario.')

        # for sig_id in missing_signal_ids:
        #     self.remove_signal_node(sig_id)
        return sensors