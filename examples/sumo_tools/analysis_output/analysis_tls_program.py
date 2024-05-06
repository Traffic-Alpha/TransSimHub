'''
@Author: WANG Maonan
@Date: 2024-05-05 23:16:45
@Description: 分析 tls program 文件
@LastEditTime: 2024-05-05 23:29:45
'''
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.sumo_tools.analysis_output.tls_program_analysis import TLSProgramAnalysis

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'), file_log_level="INFO")

# 初始化 TLSProgramAnalysis
tls_program_file = current_file_path('./add/tls_program.out.xml')
tls_analysis = TLSProgramAnalysis(tls_program_file)

# 获得每个周期内, 每个相位的持续时间 -> 可以利用这个数据进一步处理
tls_analysis.cycle_durations # 每个周期每个相位的持续时间
tls_analysis.percentage_cycles # 持续时间占比
tls_analysis.pattern_states # 获得周期内 state 的顺序

# 绘制折线图, 绿灯时间变化
directions_state = {
    'grrrrrgGGGrgrrrgGGr': 'WE-EW',
    'GGGGrrGrrrrGGGrGrrr': 'NS-SN'
}
tls_analysis.visualize_cycles_timestamps(directions_state, current_file_path("./"))
tls_analysis.visualize_cycles_idx(directions_state, current_file_path("./"))

# 绘制 bar chart, 每一个 bar 表示一个 cycle, 其中长度表示 phase 在这个 cycle 的占比
directions_state = {
    'grrrrrgGGGrgrrrgGGr': ['A', 'green'],
    'GrrrrrGrrrGGrrrGrrG': ['B', 'blue'],
    'GGGGrrGrrrrGGGrGrrr': ['C', 'red'],
    'GrrrGGGrrrrGrrGGrrr': ['D', 'cyan']
}
tls_analysis.plot_state_percentages_barh(directions_state, current_file_path("./"))
tls_analysis.plot_state_percentages_bar(directions_state, current_file_path("./"))
