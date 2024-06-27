'''
@Author: WANG Maonan
@Date: 2024-06-25 22:53:53
@Description: 对 Phase Duration Visualization 进行可视化
@LastEditTime: 2024-06-27 17:39:43
'''
import scienceplots
import numpy as np
from typing import List
import matplotlib.pyplot as plt
plt.style.use(['science', 'grid', 'no-latex', 'vibrant'])

from .tls_program_analysis import TLSProgramAnalysis

class TLSProgram_PDVis(TLSProgramAnalysis):
    def __init__(self, xml_file_path):
        super().__init__(xml_file_path) # 用于解析 xml 文件
    
    def plot_phase_ratio_line(self, phase_strs, phase_label, fig_text:str, image_path:str) -> None:
        duration_values = [] # 每个相位的占比
        for state in phase_strs:
            if state in self.state_index_map:
                index = self.state_index_map[state]
                duration_values.append([cycle[index]/100 for cycle in self.percentage_cycles[:-1]]) # 每一个phase在整个 cycle 的占比

        # 计算每个点的坐标, 用于 x 轴
        cycle_duration_sum = np.cumsum([sum(_cycle_duration)/60 for _cycle_duration in self.cycle_durations[:-1]]) 

        # 开始绘图
        plt.figure(figsize=plt.figaspect(0.6))
        
        for label, values in zip(phase_label, duration_values):
            plt.plot(cycle_duration_sum, values, label=label)

        plt.text(0.95, 0.95, fig_text, ha='right', va='top', transform=plt.gca().transAxes,
                fontsize=8, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.5)
        )
        
        plt.ylim([0, 0.5])
        plt.xlabel('Time (Minutes)')
        plt.ylabel("Green Time Ratio")
        plt.legend(loc=2, fontsize='small', fancybox=True, framealpha=0.5)
        plt.savefig(image_path)
        plt.close()

    def plot_allphase_ratio(self, phase_strs:List[str], traffic_light_duration:int, image_path:str) -> None:
        """绘制每个相位时长的占比, 可以与 traffic flow 进行分析

        Args:
            phase_strs (List[str]): 每个 phase 的内容, 例如:
                [
                    'grrrrrgGGGrgrrrgGGr', 
                    'GrrrrrGrrrGGrrrGrrG', 
                    'GGGGrrGrrrrGGGrGrrr', 
                    'GrrrGGGrrrrGrrGGrrr'
                ]
            traffic_light_duration (int): tls program 的持续时间, 单位是分钟
            image_path (str): 导出图像的路径
        """
        # 准备数据
        duration_values = []
        for state in phase_strs:
            if state in self.state_index_map:
                index = self.state_index_map[state]
                duration_values.append([cycle[index] for cycle in self.cycle_durations[:-1]])
        
        data_array = np.array(duration_values) # 每个相位的持续时间
        col_sums = data_array.sum(axis=0)
        normalized_data = data_array / col_sums # 计算每个周期内, 每个相位持续时间的占比

        # 开始绘图
        fig, ax = plt.subplots(figsize=(10, 6))

        categories = np.linspace(1, traffic_light_duration, len(normalized_data[0])) # 横坐标
        bottom_stack = [0] * len(normalized_data[0])

        # Plotting using a loop
        for i, a in enumerate(normalized_data):
            plt.bar(categories, a, 
                    bottom=bottom_stack, 
                    width=traffic_light_duration/len(normalized_data[0])*1.2, 
                    align='edge', label=f'Phase-{i+1}'
            )
            bottom_stack = [sum(x) for x in zip(bottom_stack, a)]

        # Chart details
        plt.xlabel('Time (Minutes)', fontsize='xx-large')
        plt.ylabel('Phase Duration Ratio', fontsize='xx-large')
        plt.legend(loc=1,)

        plt.savefig(image_path)
        plt.close()