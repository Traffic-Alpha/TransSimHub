'''
@Author: WANG Maonan
@Date: 2021-11-18 12:56:54
@Description: 在 berlin.net.xml, 生成探测器
@LastEditTime: 2023-09-25 19:15:25
'''
import libsumo as traci
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger
from tshub.sumo_tools.generate_detectors import generate_detector

# 初始化日志
current_file_path = get_abs_path(__file__)
set_logger(current_file_path('./'))

# 开启仿真 --> 指定 net 文件
netfile_path = current_file_path("../env/berlin.net.xml")
traci.start(["sumo", "-n", netfile_path])

# 指定要生成的路口 id 和探测器保存的位置
g_detectors = generate_detector(traci)
g_detectors.generate_multiple_detectors(
    tls_list=['25663405', '25663436', '25663407', '25663429', '25663423', '25663426'], 
    result_folder=current_file_path("../add"),
    detectors_dict={'e2':{'detector_length':50}}
)