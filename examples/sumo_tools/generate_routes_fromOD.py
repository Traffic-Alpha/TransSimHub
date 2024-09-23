'''
Author: Maonan Wang
Date: 2024-09-16 14:56:35
LastEditTime: 2024-09-17 10:13:27
LastEditors: Maonan Wang
Description: 根据起点终点生成 route
FilePath: /TransSimHub/examples/sumo_tools/generate_routes_fromOD.py
'''
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.generate_routes_fromOD import generate_route_fromOD

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'), file_log_level='WARNING', terminal_log_level='INFO')

# 开启仿真 --> 指定 net 文件
sumo_net = current_file_path("../sumo_env/three_junctions/env/3junctions.net.xml")

# 指定要生成的路口 id 和探测器保存的位置
generate_route_fromOD(
    sumo_net=sumo_net,
    interval=[5,10,15], 
    od_flow_per_minute={
        ('E0', 'E3'): [15, 15, 15], # (start, end)
        ('-E3', '-E0'): [15, 15, 15],
    }, # 每分钟每个 edge 有多少车
    veh_type={
        'ego': {'color':'26, 188, 156', 'accel':1, 'decel':1, 'probability':0.3},
        'background': {'color':'155, 89, 182', 'speed':15, 'probability':0.7},
    },
    output_trip=current_file_path('./testflow.trip.xml'),
    output_route=current_file_path('./testflow.rou.xml'),
    interpolate_flow=False,
)