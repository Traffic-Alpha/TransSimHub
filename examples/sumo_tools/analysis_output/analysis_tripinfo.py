'''
@Author: WANG Maonan
@Date: 2024-06-25 22:07:05
@Description: 分析 TripInfo 文件
@LastEditTime: 2024-06-25 22:09:24
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.sumo_tools.analysis_output.tripinfo_analysis import TripInfoAnalysis

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'), file_log_level="INFO")

tripinfo_file = current_file_path("./output/tripinfo.out.xml")
tripinfo_parser = TripInfoAnalysis(tripinfo_file)
stats = tripinfo_parser.get_all_stats()
tripinfo_parser.print_stats()