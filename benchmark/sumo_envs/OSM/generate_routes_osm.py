'''
@Author: WANG Maonan
@Date: 2023-09-14 12:43:28
@Description: 给 OSM 环境生成 route 的例子
@LastEditTime: 2023-09-14 15:47:49
'''
import numpy as np
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.generate_routes import generate_route

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

# 开启仿真 --> 指定 net 文件
sumo_net = current_file_path("./env/osm.net.xml")

# 指定要生成的路口 id 和探测器保存的位置
generate_route(
    sumo_net=sumo_net,
    interval=[5,5,5,5], 
    edge_flow_per_minute={
        '1125678574': [np.random.randint(10, 15) for _ in range(4)],
        '1125695391#0.789': [np.random.randint(10, 15) for _ in range(4)],
        '1125691753#1': [np.random.randint(10, 15) for _ in range(4)],
        '1125790983#0': [np.random.randint(10, 15) for _ in range(4)],
        '1125793701#3': [np.random.randint(10, 15) for _ in range(4)],
        '219056200#2': [np.random.randint(10, 15) for _ in range(4)],
    }, # 每分钟每个 edge 有多少车
    edge_turndef={
        '1125695391#0.789__1125695392#0': [0.7, 0.7, 0.8, 0.7],
        '1125684496#1__1125597092#1': [0.7, 0.7, 0.8, 0.7],
        '1125695392#0__1125695392#7.174': [0.7, 0.7, 0.8, 0.7],
        '1125790983#2__1125684496#0': [0.7, 0.7, 0.8, 0.7]
    },
    veh_type={
        'ego': {'color':'26, 188, 156', 'probability':0.3},
        'background': {'color':'155, 89, 182', 'probability':0.7},
    },
    output_trip=current_file_path('./testflow.trip.xml'),
    output_turndef=current_file_path('./testflow.turndefs.xml'),
    output_route=current_file_path('./osm.rou.xml'),
    interpolate_flow=False,
    interpolate_turndef=False,
)