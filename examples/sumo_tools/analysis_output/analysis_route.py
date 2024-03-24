'''
@Author: WANG Maonan
@Date: 2024-03-24 15:19:10
@Description: 分析生成的路网数据
@LastEditTime: 2024-03-24 15:36:27
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.sumo_tools.analysis_output.route_analysis import count_vehicles_for_multiple_edges, plot_vehicle_counts

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

route_file = current_file_path('../../sumo_env/single_junction/env/straight.rou.xml')

edge_vehs = count_vehicles_for_multiple_edges(
    xml_path=route_file,
    edges_list=["gsndj_s4 gsndj_s5", "gsndj_n7 gsndj_n6"],
    interval=120
)
plot_vehicle_counts(edge_vehs, current_file_path('./route.png'))