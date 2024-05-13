'''
@Author: WANG Maonan
@Date: 2024-03-24 15:19:10
@Description: 分析生成的路网数据
@LastEditTime: 2024-05-14 03:26:53
'''
from typing import Dict
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.sumo_tools.analysis_output.route_analysis import count_vehicles_for_multiple_edges, plot_vehicle_counts

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

def merge_and_add_values(dict1: Dict[str, float], dict2:Dict[str, float]):
    """用于将两个 dict 进行合并, 相同 key 对应的 value 进行相加
        输入示例：
            dict1 = {'a': 1, 'b': 2, 'c': 3}
            dict2 = {'b': 3, 'c': 4, 'd': 5}
        输出示例：
            {'a': 1, 'b': 5, 'c': 7, 'd': 5}

    Args:
        dict1 (Dict[str, float]): 等待合并的第一个字典
        dict2 (Dict[str, float]): 等待合并的第二个字典
    """
    # Create a new dictionary to store the merged data
    merged_dict = {}
    # Combine keys from both dictionaries
    all_keys = set(dict1) | set(dict2)
    # Loop through all keys and add values from both dictionaries
    for key in all_keys:
        merged_dict[key] = dict1.get(key, 0) + dict2.get(key, 0)
    return merged_dict

route_file = current_file_path('../../sumo_env/single_junction/env/straight.rou.xml')

edge_vehs = count_vehicles_for_multiple_edges(
    xml_path=route_file,
    edges_list=["gsndj_s4 gsndj_s5", "gsndj_n7 gsndj_n6", "161701303#7.248 161701303#10", "29257863#2 29257863#5"],
    interval=60
)

# 修改 key 用于修改 label
edge_vehs['NS-SN'] = merge_and_add_values(
    edge_vehs.pop("gsndj_s4 gsndj_s5"),
    edge_vehs.pop("gsndj_n7 gsndj_n6")
)
edge_vehs['WE-EW'] = merge_and_add_values(
    edge_vehs.pop("29257863#2 29257863#5"),
    edge_vehs.pop("161701303#7.248 161701303#10")
)

plot_vehicle_counts(edge_vehs, current_file_path('./route.png'))