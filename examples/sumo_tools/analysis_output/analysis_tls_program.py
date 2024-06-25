'''
@Author: WANG Maonan
@Date: 2024-05-05 23:16:45
@Description: 分析 tls program 文件
@LastEditTime: 2024-06-25 23:17:55
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.sumo_tools.analysis_output.tls_program_analysis import TLSProgramAnalysis

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'), file_log_level="INFO")

# 初始化 TLSProgramAnalysis
tls_program_file = current_file_path('./output/add/tls_program.out.xml')
tls_analysis = TLSProgramAnalysis(tls_program_file)

# 获得每个周期内, 每个相位的持续时间 -> 可以利用这个数据进一步处理
print(tls_analysis.cycle_durations) # 每个周期每个相位的持续时间
print(tls_analysis.percentage_cycles) # 持续时间占比
print(tls_analysis.pattern_states) # 获得周期内 state 的顺序