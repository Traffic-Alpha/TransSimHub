'''
@Author: WANG Maonan
@Date: 2024-08-11 19:53:55
@Description: 测试同时控制车辆和信号灯
@LastEditTime: 2024-08-12 15:06:11
'''
import numpy as np

from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from env_utils.tshub_env import MixFlowEnvironment

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

def filter_ego_id(vehicle_data):
    ego_ids = []
    for _veh_id, _veh_info in vehicle_data.items():
        if _veh_info['vehicle_type'] == 'ego':
            ego_ids.append(_veh_id)
    return ego_ids

if __name__ == '__main__':
    sumo_cfg = path_convert("./sumo_net/env/three_junctions.sumocfg")
    mixflow_env = MixFlowEnvironment(
            sumo_cfg=sumo_cfg, # sumocfg
            num_seconds=2000, # 仿真时间
            tls_ids=['J1', 'J2', 'J3'],
            use_gui=True
        )

    done = False
    states = mixflow_env.reset()
    while not done:
        ego_ids = filter_ego_id(states.get('vehicle', {}))
        action = {
            "vehicle": {
                _ego_id: {'speed_action': 1, 'acceleration_rate': 2} 
                for _ego_id in ego_ids
            },
            "tls": {
                "J1": np.random.randint(4),
                "J2": np.random.randint(4),
                "J3": np.random.randint(4),
            }
        }
        states, rewards, truncateds, done, infos = mixflow_env.step(action)
    mixflow_env.close()