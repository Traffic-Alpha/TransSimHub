'''
@Author: WANG Maonan
@Date: 2023-09-25 18:02:47
@Description: 
@LastEditTime: 2023-09-25 19:37:57
'''
'''
@Author: WANG Maonan
@Date: 2023-09-01 13:45:26
@Description: 给场景生成路网
@LastEditTime: 2023-09-01 14:32:04
'''
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.generate_routes import generate_route

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

# 开启仿真 --> 指定 net 文件
sumo_net = current_file_path("../env/berlin.net.xml")

# 指定要生成的路口 id 和探测器保存的位置
generate_route(
    sumo_net=sumo_net,
    interval=[5,5,5], 
    edge_flow_per_minute={
        '65040946#0': [8, 8, 8],
        '24242838#0': [8, 8, 8],
        '1152723807': [7, 7, 7],
        '-32938173#2': [7, 7, 7],
        '-1147648945#1': [10, 10, 13],
        '-1152723815': [10, 10, 7],
        '-1105574288#1': [10, 10, 9],
        '-23755718#2': [10, 10, 7]
    }, # 每分钟每个 edge 有多少车
    edge_turndef={
        '24242838#0__24242838#5': [0.7, 0.7, 0.8],
        '24242838#5__1105574288#0': [0.9, 0.9, 0.9],
    },
    veh_type={
        'ego': {'color':'26, 188, 156', 'probability':0.3},
        'background': {'color':'155, 89, 182', 'speed':15, 'probability':0.7},
    },
    output_trip=current_file_path('./testflow.trip.xml'),
    output_turndef=current_file_path('./testflow.turndefs.xml'),
    output_route=current_file_path('../env/berlin.rou.xml'),
    interpolate_flow=False,
    interpolate_turndef=False,
)