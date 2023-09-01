'''
@Author: WANG Maonan
@Date: 2023-08-31 20:05:01
@Description: 生成转向概率
@LastEditTime: 2023-09-01 13:53:52
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.sumo_tools.generate_route.generate_turn_def import GenerateTurnDef

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

# 初始化参数
intervals = [5,10,15] # 每个阶段的持续时间
edge_turndef = {
    '-E9__E4': [0.7, 0.7, 0.8],
    '-E9__-E0': [0.1, 0.1, 0.1],
} # 每个阶段每分钟的车辆
sumo_net = current_file_path("../../sumo_env/three_junctions/env/3junctions.net.xml")
output_file = current_file_path('./test.trundefs.xml')

# 生成 trip 文件
g_turndefs = GenerateTurnDef(
    intervals=intervals,
    edge_turndef=edge_turndef,
    sumo_net=sumo_net,
    output_file=output_file
)
g_turndefs.generate_turn_definition()
g_turndefs.edit_turn_definition()