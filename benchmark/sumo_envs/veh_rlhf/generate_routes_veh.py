'''
@Author: WANG Maonan
@Date: 2023-10-27 20:51:49
@Description: 给 Vehicle Lane Change RLHF 环境生成 route 的例子
@LastEditTime: 2023-11-17 16:29:35
'''
import numpy as np
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.generate_routes import generate_route

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

# 开启仿真 --> 指定 net 文件
sumo_net = current_file_path("./veh_rlhf.net.xml")

# 指定要生成的路口 id 和探测器保存的位置
generate_route(
    sumo_net=sumo_net,
    interval=[1,2,3], # 有 3 个时间段
    edge_flow_per_minute={
        'E0': [10,20,15],
    }, # 每分钟每个 edge 有多少车
    edge_turndef={},
    veh_type={
        'ego': {'color':'26, 188, 156', 'length':7, 'speed':11, 'probability':0.1},
        'background': {'color':'155, 89, 182', 'speed':6, 'length':7, 'probability':0.9},
    },
    output_trip=current_file_path('./testflow.trip.xml'),
    output_turndef=current_file_path('./testflow.turndefs.xml'),
    output_route=current_file_path('./veh_rlhf.rou.xml'),
    interpolate_flow=False,
    interpolate_turndef=False,
)