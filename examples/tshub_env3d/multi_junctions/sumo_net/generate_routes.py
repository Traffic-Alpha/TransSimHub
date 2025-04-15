'''
@Author: WANG Maonan
@Date: 2023-09-01 13:45:26
@Description: 随机生成车辆, 包含不同的车辆类型
LastEditTime: 2025-04-15 15:20:04
'''
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.generate_routes import generate_route

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'), file_log_level='WARNING', terminal_log_level='INFO')

# 开启仿真 --> 指定 net 文件
sumo_net = current_file_path("./multi_junctions.net.xml")

# 指定要生成的路口 id 和探测器保存的位置
generate_route(
    sumo_net=sumo_net,
    interval=[1,1,1], 
    edge_flow_per_minute={
        'E0': [10, 10, 10],
        'E1': [10, 10, 10],
        '-E2': [10, 10, 10],
        'E5': [10, 10, 10],
        '-E6': [10, 10, 10],
        '-E8': [10, 10, 10],
        '-E7': [10, 10, 10],
    }, # 每分钟每个 edge 有多少车
    edge_turndef={},
    veh_type={
        'background': {'color':'220,220,220', 'length': 5, 'probability':0.6},
        'police': {'color':'0,0,255', 'length': 5, 'probability':0.1},
        'emergency': {'color':'255,165,0', 'length': 6.5, 'probability':0.1},
        'fire_engine': {'color':'255,0,0', 'length': 7.1, 'probability':0.1},
        'taxi': {'color':'255,255,0', 'length': 5, 'probability':0.1},
    },
    output_trip=current_file_path('./testflow.trip.xml'),
    output_turndef=current_file_path('./testflow.turndefs.xml'),
    output_route=current_file_path('./multi_junctions.rou.xml'),
    interpolate_flow=False,
    interpolate_turndef=False,
)