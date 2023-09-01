'''
@Author: WANG Maonan
@Date: 2023-08-31 17:42:33
@Description: 测试生成 .trip.xml 文件
@LastEditTime: 2023-09-01 13:49:17
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.sumo_tools.generate_route.generate_trip import GenerateTrip

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

# 初始化参数
intervals = [5,10,15] # 每个阶段的持续时间
edge_flow_per_minute = {
    'edge_1': [10,5,7],
    'edge_2': [21,15,2],
    'edge_3': [2,12,3],
} # 每个阶段每分钟的车辆
veh_type = {
        'ego': {'color':'26, 188, 156', 'probability':0.3},
        'background': {'color':'155, 89, 182', 'probability':0.7},
} # 车辆的类型
output_file = current_file_path('./test.trip.xml')

# 生成 trip 文件
g_trip = GenerateTrip(
    intervals=intervals,
    edge_flow_per_minute=edge_flow_per_minute,
    veh_type=veh_type,
    output_file=output_file
)
g_trip.generate_trip_xml()
g_trip.edit_trip_xml()