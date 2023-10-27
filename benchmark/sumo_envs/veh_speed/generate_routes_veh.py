'''
@Author: WANG Maonan
@Date: 2023-10-27 20:51:49
@Description: 给 Vehicle Speed Control 环境生成 route 的例子
@LastEditTime: 2023-10-27 20:55:37
'''
import numpy as np
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.generate_routes import generate_route

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

# 开启仿真 --> 指定 net 文件
sumo_net = current_file_path("./veh.net.xml")

# 指定要生成的路口 id 和探测器保存的位置
generate_route(
    sumo_net=sumo_net,
    interval=[5,5,5,5],
    edge_flow_per_minute={
        'E1': [np.random.randint(10, 15) for _ in range(4)],
    }, # 每分钟每个 edge 有多少车
    edge_turndef={},
    veh_type={
        'ego': {'color':'26, 188, 156', 'probability':0.3},
        'background': {'color':'155, 89, 182', 'probability':0.7},
    },
    output_trip=current_file_path('./testflow.trip.xml'),
    output_turndef=current_file_path('./testflow.turndefs.xml'),
    output_route=current_file_path('./veh.rou.xml'),
    interpolate_flow=False,
    interpolate_turndef=False,
)