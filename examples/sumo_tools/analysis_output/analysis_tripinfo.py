'''
@Author: WANG Maonan
@Date: 2024-06-25 22:07:05
@Description: 分析 TripInfo 文件
LastEditTime: 2025-04-29 17:15:07
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.sumo_tools.analysis_output.tripinfo_analysis import TripInfoAnalysis

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'), file_log_level="INFO")

tripinfo_file = current_file_path("./output/tripinfo.out.xml")
tripinfo_parser = TripInfoAnalysis(tripinfo_file)

# 所有车辆一起分析
stats = tripinfo_parser.calculate_multiple_stats(metrics=['fuel_abs', 'duration', 'waitingTime'])
TripInfoAnalysis.print_stats_as_table(stats)

# 按照车辆类型分析
vehicle_stats = tripinfo_parser.statistics_by_vehicle_type(metrics=['fuel_abs', 'duration', 'waitingTime'])
print(vehicle_stats['waitingTime'])
print(vehicle_stats['fuel_abs'])
print(vehicle_stats['duration'])