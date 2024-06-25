'''
@Author: WANG Maonan
@Date: 2024-05-05 23:12:32
@Description: 分析 tls_program.out.xml 文件, 这里信号灯需要是按照周期进行控制 (例如 next or not 的动作设计)
@LastEditTime: 2024-06-25 23:17:37
'''
from loguru import logger
import xml.etree.ElementTree as ET

class TLSProgramAnalysis(object):
    def __init__(self, xml_file_path):
        self.xml_file_path = xml_file_path
        self.pattern_states = [] # 一个周期内 phase state
        self.cycle_durations = [] # 每个周期, 每个 phase 的持续时间 (每个周期 cycle 可能是不一样的)
        self.percentage_cycles = [] # 每个周期, 每个 phase 的持续时间占比
        self.state_index_map = {} # 每个 phase state 对应的索引, 方便在 cycle_durations 和 percentage_cycles 找到对应的数
        self.parse_xml_file() # 解析 xml 文件

    def parse_xml_file(self):
        tree = ET.parse(self.xml_file_path)
        root = tree.getroot()

        phases = root.findall('.//phase')
        states = [phase.get('state') for phase in phases]
        durations = [float(phase.get('duration')) for phase in phases]

        # Identify the repeating pattern of states to delineate cycles
        pattern_end_index = states[1:].index(states[0]) + 1
        self.pattern_states = states[:pattern_end_index]

        # Calculate the total number of cycles
        self.cycle_durations = [durations[i:i + pattern_end_index] for i in range(0, len(durations), pattern_end_index)]

        # Calculate the percentage duration of each phase within its cycle
        self.percentage_cycles = self.__calculate_percentage_cycles()

        # Map pattern phase states to their indexes
        self.state_index_map = {state: index for index, state in enumerate(self.pattern_states)}


    def __calculate_percentage_cycles(self):
        """计算每个周期内, 每个 phase duration 的占比, 取出 cycle 的影响
        """
        percentage_cycles = []
        for cycle in self.cycle_durations:
            total_duration = sum(cycle)
            percentages = [(phase_duration / total_duration) * 100 for phase_duration in cycle]
            percentage_cycles.append(percentages)
        return percentage_cycles