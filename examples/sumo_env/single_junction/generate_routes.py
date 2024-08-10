'''
@Author: WANG Maonan
@Date: 2023-09-01 13:45:26
@Description: 给场景生成路网 (180s)
@LastEditTime: 2024-07-21 04:30:02
'''
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.generate_routes import generate_route

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'), file_log_level='WARNING', terminal_log_level='INFO')

# 开启仿真 --> 指定 net 文件
sumo_net = current_file_path("./env/single_junction.net.xml")

# 指定要生成的路口 id 和探测器保存的位置
generate_route(
    sumo_net=sumo_net,
    interval=[1,1,1], 
    edge_flow_per_minute={
        'gsndj_n7': [15, 15, 15],
        '29257863#2': [15, 15, 15],
        'gsndj_s4': [7, 7, 7],
        '161701303#7.248': [7, 7, 7],
    }, # 每分钟每个 edge 有多少车
    edge_turndef={},
    veh_type={
        'ego': {'color':'26, 188, 156', 'accel':1, 'decel':1, 'probability':0.07},
        'background': {'color':'155, 89, 182', 'speed':15, 'probability':0.93},
    },
    output_trip=current_file_path('./testflow.trip.xml'),
    output_turndef=current_file_path('./testflow.turndefs.xml'),
    output_route=current_file_path('./testflow.rou.xml'),
    interpolate_flow=False,
    interpolate_turndef=False,
)