'''
@Author: WANG Maonan
@Date: 2023-09-01 13:45:26
@Description: 给场景生成路网
@LastEditTime: 2023-10-29 23:25:23
'''
import numpy as np
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.generate_routes import generate_route

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

# 开启仿真 --> 指定 net 文件
sumo_net = current_file_path("./env/three_junctions.net.xml")

# 指定要生成的路口 id 和探测器保存的位置
generate_route(
    sumo_net=sumo_net,
    interval=[5,5,5,5], 
    edge_flow_per_minute={
        'E0': [np.random.randint(15, 20) for _ in range(4)],
        '-E7': [np.random.randint(15, 20) for _ in range(4)],
        
        '-E4': [np.random.randint(5, 10) for _ in range(4)],
        'E3': [np.random.randint(5, 10) for _ in range(4)],

        'E5': [np.random.randint(5, 10) for _ in range(4)],
        '-E6': [np.random.randint(5, 10) for _ in range(4)],

        'E8': [np.random.randint(5, 10) for _ in range(4)],
        '-E9': [np.random.randint(5, 10) for _ in range(4)],
    }, # 每分钟每个 edge 有多少车
    edge_turndef={
        'E0__E1': [0.8]*4,
        '-E1__-E0': [0.8]*4,
        'E1__E2': [0.8]*4,
        '-E2__-E1': [0.8]*4,
        'E2__E7': [0.8]*4,
        '-E7__-E2':[0.8]*4,
    },
    veh_type={
        'ego': {'color':'26, 188, 156', 'probability':0.3},
        'background': {'color':'155, 89, 182', 'speed':15, 'probability':0.7},
    },
    output_trip=current_file_path('./testflow.trip.xml'),
    output_turndef=current_file_path('./testflow.turndefs.xml'),
    output_route=current_file_path('./three_junctions.rou.xml'),
    interpolate_flow=False,
    interpolate_turndef=False,
)