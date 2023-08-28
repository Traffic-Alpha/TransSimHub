'''
@Author: WANG Maonan
@Date: 2023-08-25 11:23:21
@Description: 调度场景中的 traffic lights
@LastEditTime: 2023-08-28 16:30:38
'''
import traci
import numpy as np
from collections import defaultdict
from typing import Dict, List

from .traffic_light import TrafficLightInfo
from .traffic_light_feature_convert import TSCKeyMeaningsConverter
from ..utils.nested_dict_conversion import defaultdict2dict

class TrafficLightBuilder:
    def __init__(self, sumo, 
                 tls_ids:List[str], 
                 action_type:str, 
                 delta_time:int=5) -> None:
        self.sumo = sumo
        self.tls_ids = tls_ids # 信号灯 id 列表
        self.action_type = action_type # 信号灯支持的动作类型
        self.delta_time = delta_time # 信号灯的动作间隔
        self.traffic_lights = dict()  # 存储场景中的所有交通信号灯
        self.tsc_convert = TSCKeyMeaningsConverter()

        self.subscribe_detector() # 订阅传感器
        self.create_traffic_lights() # 初始化场景所有信号灯
        

    def subscribe_detector(self) -> None:
        """
        订阅传感器
        """
        for e2_id in self.sumo.lanearea.getIDList():
            self.sumo.lanearea.subscribe(e2_id, 
                    [
                        traci.constants.LAST_STEP_MEAN_SPEED, # 17
                        traci.constants.JAM_LENGTH_VEHICLE, # 24
                        traci.constants.JAM_LENGTH_METERS, # 25
                        traci.constants.LAST_STEP_OCCUPANCY, # 19, Note: 因为车辆之间有间隔, 所以即使排满了, occ 也不会是 100%
                    ])

    def create_traffic_lights(self) -> None:
        """
        为场景初始化所有的交通信号灯
        """
        zeros = np.zeros(12) # 十字路口包含 12 个 movement
        for _tls_id in self.tls_ids:
            traffic_light = TrafficLightInfo.create_traffic_light(
                id=_tls_id,
                action_type=self.action_type,
                delta_time=self.delta_time,
                last_step_mean_speed=zeros.tolist(), 
                jam_length_vehicle=zeros.tolist(), 
                jam_length_meters=zeros.tolist(),
                last_step_occupancy=zeros.tolist(),
                this_phase=zeros.astype(bool).tolist(), 
                last_phase=zeros.astype(bool).tolist(), 
                next_phase=zeros.astype(bool).tolist(), 
                sumo=self.sumo,
            )
            self.traffic_lights[_tls_id] = traffic_light

    def process_detector_data(self, raw_data) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        处理从传感器传回来的原始数据
            raw_data 的数据结果如下, 其中 id 含义为 e2det--junctionID--fromEdge--fromLane--toLane--Direction
                {
                    'e2det--ftddj_frj--gneE27--gneE27_0--r': {17: 14.374141326903933, 24: 7, 25: 1, 19: 0.4},
                    'e2det--ftddj_frj--gneE27--gneE27_1--s': {17: 7.298125864714802, 24: 14, 25: 2, 19: 0.8},
                    ...
                }
            我们希望按照 movement 对上面的结果进行处理:
                {
                    'INT-1':{
                        'gneE27--gneE27_0--r': {17: 14.374141326903933, 24: 7, 25: 1, 19: 0.4},
                        'gneE27--gneE27_0--s': {17: 14.374141326903933, 24: 7, 25: 1, 19: 0.4},
                        ...
                    },
                    'INT-2:{
                        ...
                    },
                    ...
                }
            最后将每个 movement 对应的 key 转换为关键词
                {
                    'INT-1':{
                        'gneE27--gneE27_0--r': {'last_step_mean_speed': 0.0, 'jam_length_vehicle': 0.0, 'jam_length_meters': 0.0, 'last_step_occupancy': 0.0},
                        'gneE27--gneE27_0--s': {'last_step_mean_speed': 0.0, 'jam_length_vehicle': 0.0, 'jam_length_meters': 0.0, 'last_step_occupancy': 0.0},
                        ...
                    },
                    'INT-2:{
                        ...
                    },
                    ...
                }
        """
        output = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        count = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        
        for key, value in raw_data.items():
            parts = key.split('--')
            junction_id = parts[1]
            edge_id = parts[2]
            direction = parts[4]
            
            edge_direction = f'{edge_id}_{direction}'
            
            # 处理每一个 lane 对应的 {17: 14.374141326903933, 24: 7, 25: 1, 19: 0.4} 的信息
            for k, v in value.items():
                _meaning_key = self.tsc_convert.get_meaning(k)
                output[junction_id][edge_direction][_meaning_key] += v
                count[junction_id][edge_direction][_meaning_key] += 1
        
        for junction_id, edges in output.items():
            for edge_direction, values in edges.items():
                for k in values:
                    values[k] /= count[junction_id][edge_direction][k]
        
        return defaultdict2dict(output)

    def update_traffic_lights_state(self, processed_data) -> None:
        """更新每一个信号灯的状态

        Args:
            processed_data (Dict[str, Dict[str, Dict[float]]]): 每一个路口每一个 movement 的数据
                {
                    'INT-1':{
                        '161701303#7.248_r': {17: 0.0, 24: 0.0, 25: 0.0, 19: 0.0},
                        '161701303#7.248_s': {17: 0.0, 24: 0.0, 25: 0.0, 19: 0.0},
                        '161701303#7.248_l': {17: 0.0, 24: 0.0, 25: 0.0, 19: 0.0},
                        ...
                    },
                    'INT-2':{
                        ...
                    }
                }
        """
        for _tls_id, _tls_data in processed_data.items():
            self.traffic_lights[_tls_id].update_features(_tls_data)

    def get_traffic_lights_infos(self):
        """
        获取场景中所有交通信号灯的信息
        """
        detector_result = self.sumo.lanearea.getAllSubscriptionResults()
        processed_data = self.process_detector_data(detector_result)
        self.update_traffic_lights_state(processed_data)
        # 最后需要将其转换为 dict 进行输出
        tls_features = {}
        for _tls_id in self.tls_ids:
            tls_features[_tls_id] = self.traffic_lights[_tls_id].get_feature()
        return tls_features

    def control_traffic_lights(self, actions):
        """
        控制所有交通信号灯
        """
        for _tls_id in self.tls_ids:
            tls_action = actions[_tls_id] # 得到对应 tls 的 action
            self.traffic_lights[_tls_id].control_traffic_light(tls_action)
