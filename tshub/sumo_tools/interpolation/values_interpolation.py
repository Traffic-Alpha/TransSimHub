'''
@Author: WANG Maonan
@Date: 2021-04-07 12:01:20
@Description: 对于数值进行平滑
@LastEditTime: 2023-09-01 14:12:04
'''
import numpy as np
from scipy.interpolate import interp1d
from typing import Tuple, List

class InterpolationValues(object):
    def __init__(self, values:List[float], intervals:List[int]) -> None:
        """将时间段切分为每一分钟的时间粒度, 并对每一分钟的结果进行插值
        
        现在输入为:
            - values 为 [0.25, 1, 0.4], 表示每个时间段的转弯概率 (每个时间段车辆进入流量)
            - intervals 为 [20, 20, 10], 表示每个时间段的时间长度
        
        我们会转换为一下的格式:
            - self.values, 重复一下第一个时间段的值, 为 [0.25, 0.25, 1, 0.4]
            - self.x_pos, 从 0 开始统计一个时间段, 为 [0, 20, 40, 50]
        
        然后我们使用 self.values 和 self.x_pos 来计算插值, 得到 self.f, 用于返回每个时刻的转向概率;
        """
        self.values = [values[0]] + values + [values[-1]]
        self.x_pos = self._transform_list(intervals)
        self.f = interp1d(self.x_pos, self.values, kind='linear')

    def _transform_list(self, input_list) -> List[int]:
        """对给定的列表进行累加、计算平均值，并在新列表中添加首尾元素。

        参数:
            input_list (list): 输入的列表。

        返回:
            list: 转换后的列表。

        示例:
            >>> Input: [20, 20, 10]
            >>> Output: [0, 10, 30, 45, 50]
        """
        cumulative_list = [0] # 初始累加列表以0开头
        for num in input_list:
            cumulative_list.append(cumulative_list[-1] + num) # 将当前元素与前一个累加值相加并添加到累加列表中
        
        average_list = [] # 平均值列表
        for i in range(len(cumulative_list) - 1):
            average = (cumulative_list[i] + cumulative_list[i+1]) // 2 # 计算两两元素的平均值
            average_list.append(average)
        
        output_list = [0] + average_list + [cumulative_list[-1]] # 添加首尾元素到新列表中
        return output_list

    
    def _interpolation(self, x) -> float:
        """对给定的时间点进行插值计算。

        参数:
            x (float): 时间点。

        返回:
            float: 插值后的结果。

        示例:
            >>> smooth_value = InterpolationValues(values=[0.25, 1, 0.4], intervals=[20, 20, 10])
            >>> smooth_value._interpolation(15)
            0.25
            >>> smooth_value._interpolation(30)
            0.62
        """
        turndef_period = self.f(x) # 某个时刻的转向比
        return round(turndef_period.item(), 2)

    def get_smooth_values(self) -> Tuple[List[int], List[float]]:
        """
        获取平滑的值的列表。

        返回:
            tuple: 包含时间间隔和插值后值的列表的元组。

        示例:
            >>> smooth_value = InterpolationValues(values=[0.25, 1, 0.4], intervals=[20, 20, 10])
            >>> time_intervals, smooth_turndef_list = smooth_value.get_smooth_turndef()
            >>> time_intervals
            array([0, 1, 2, ..., 47, 48, 49])
            >>> smooth_turndef_list
            [0.25, 0.25, 0.25, ..., 0.58, 0.52, 0.46]
        """
        time_index = np.arange(int(self.x_pos[-1]))
        smooth_turndef_list = [self._interpolation(i) for i in time_index]
        return smooth_turndef_list