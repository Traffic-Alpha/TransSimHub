'''
@Author: WANG Maonan
@Date: 2024-05-05 23:12:32
@Description: 分析 tls_program.out.xml 文件, 这里信号灯需要是按照周期进行控制 (例如 next or not 的动作设计)
@LastEditTime: 2024-05-05 23:15:49
'''
from loguru import logger
import matplotlib.pyplot as plt
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
    
    def __prepare_visualization_data(self, state_labels):
        """选择部分 state 的数据用于可视化

        Args:
            state_labels (_type_): _description_

        Returns:
            _type_: _description_
        """
        x_ticks = []
        duration_values = []
        percentage_values = []
        for state, label in state_labels.items():
            if state in self.state_index_map:
                index = self.state_index_map[state]
                x_ticks.append(label)
                duration_values.append([cycle[index] for cycle in self.cycle_durations])
                percentage_values.append([cycle[index] for cycle in self.percentage_cycles])
        return x_ticks, duration_values, percentage_values

    def _plot_line(self, 
                         x_ticks, duration_values, percentage_values, 
                         time_stamps, title, y_label, save_path, 
                         is_percentage:bool, is_timestamp:bool
        ) -> None:
        plt.figure(figsize=plt.figaspect(0.6))
        for i, label in enumerate(x_ticks):
            y_values = percentage_values[i] if is_percentage else duration_values[i] # y 使用百分比或是数值
            x_values = time_stamps[1:] if is_timestamp else list(range(1,len(y_values)+1))
            plt.plot(x_values, y_values, label=label)
        plt.title(title)
        if is_timestamp:
            plt.xlabel('Time (minutes)')
        else:
            plt.xlabel('Cycles (idx)')
        plt.ylabel(y_label)
        plt.legend()
        plt.grid(True)
        plt.savefig(f"{save_path}.png")
        plt.close()
        logger.info(f"SIM: Save Line to {save_path}")

    def _plot_bar_chart(self, 
                        duration_values, percentage_values, 
                        colors, title:str, save_path:str, 
                        is_horizontal:bool, is_percentage:bool
        ) -> None:
        transposed_values = list(map(list, zip(*percentage_values))) \
            if is_percentage else list(map(list, zip(*duration_values)))
        num_bars = len(transposed_values)
        bar_height = 0.8
        fig_dim = num_bars * (bar_height + 0.2)
        plt.figure(figsize=(10, fig_dim) if is_horizontal else (fig_dim, 10))
        # Define the plotting function based on orientation
        bar_func = plt.barh if is_horizontal else plt.bar

        # Plot the bars
        for idx, cycle in enumerate(transposed_values):
            left = 0
            for i, value in enumerate(cycle):
                if is_horizontal:
                    bar_func(idx, value, left=left, color=colors[i], edgecolor='black', height=bar_height)
                else:
                    bar_func(idx, value, bottom=left, color=colors[i], edgecolor='black', width=bar_height)
                left += value
        plt.title(title)
        plt.savefig(f"{save_path}.png")
        logger.info(f"SIM: Save Bar Chat to {save_path}")
        plt.close()

    def visualize_cycles_timestamps(self, state_labels, save_path):
        x_ticks, duration_values, percentage_values = self.__prepare_visualization_data(state_labels)
        
        # Initialize time_stamps
        time_stamps = [0]
        for cycle in self.cycle_durations:
            # Calculate the new time stamp and append it to the list
            new_time_stamp = time_stamps[-1] + sum(cycle) / 60.0  # Convert seconds to minutes
            time_stamps.append(new_time_stamp)

        self._plot_line(
            x_ticks, duration_values, percentage_values, time_stamps, 
            'Phase Durations Over Time', 'Green Time Ratio (%)', 
            f"{save_path}/durations_timestamps", 
            is_percentage=False, is_timestamp=True
        )
        self._plot_line(
            x_ticks, duration_values, percentage_values, time_stamps, 
            'Phase Percentages Over Time', 'Green Time Ratio (%)', 
            f"{save_path}/percentages_timestamps", 
            is_percentage=True, is_timestamp=True
        )

    def visualize_cycles_idx(self, state_labels, save_path):
        x_ticks, duration_values, percentage_values = self.__prepare_visualization_data(state_labels)
        # Initialize time_stamps
        time_stamps = [0]
        for cycle in self.cycle_durations:
            # Calculate the new time stamp and append it to the list
            new_time_stamp = time_stamps[-1] + sum(cycle) / 60.0  # Convert seconds to minutes
            time_stamps.append(new_time_stamp)

        self._plot_line(
            x_ticks, duration_values, percentage_values, time_stamps, 
            'Phase Durations Over Time', 'Green Time Ratio (%)', 
            f"{save_path}/durations_idx", 
            is_percentage=False, is_timestamp=False
        )
        self._plot_line(
            x_ticks, duration_values, percentage_values, time_stamps, 
            'Phase Percentages Over Time', 'Green Time Ratio (%)', 
            f"{save_path}/percentages_idx", 
            is_percentage=True, is_timestamp=False
        )

    def plot_state_percentages_barh(self, state_info, image_path):
        x_ticks, duration_values, percentage_values = self.__prepare_visualization_data(
            {
                state: label 
                for state, (label, _) 
                in state_info.items()
            }
        )
        colors = [color for _, (_, color) in state_info.items()]
        # 绘制 phase duration 百分比
        self._plot_bar_chart(
            duration_values, percentage_values, colors, 
            title='Phase Percentages', 
            save_path=f"{image_path}/phase_percentages_barh", 
            is_horizontal=True, is_percentage=True
        )
        # 直接绘制数值
        self._plot_bar_chart(
            duration_values, percentage_values, colors, 
            'Phase Percentages', 
            save_path=f"{image_path}/phase_values_barh", 
            is_horizontal=True, is_percentage=False
        )

    def plot_state_percentages_bar(self, state_info, image_path):
        x_ticks, duration_values, percentage_values = self.__prepare_visualization_data(
            {
                state: label 
                for state, (label, _) 
                in state_info.items()
            }
        )
        colors = [color for _, (_, color) in state_info.items()]
        # 绘制 phase duration 百分比
        self._plot_bar_chart(
            duration_values, percentage_values, colors, 
            'Phase Percentages', 
            save_path=f"{image_path}/phase_percentages_bar", 
            is_horizontal=False, is_percentage=True
        )
        # 直接绘制数值
        self._plot_bar_chart(
            duration_values, percentage_values, colors, 
            'Phase Percentages', 
            save_path=f"{image_path}/phase_values_bar", 
            is_horizontal=False, is_percentage=False
        )