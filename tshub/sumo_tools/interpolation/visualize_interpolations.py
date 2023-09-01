'''
@Author: WANG Maonan
@Date: 2023-08-31 17:06:54
@Description: 对插值之后的结果进行可视化展示
@LastEditTime: 2023-08-31 17:16:20
'''
import numpy as np
import matplotlib.pyplot as plt
from .repeat_values import repeat_values

def visualize_interpolations(values, period, smooth_values) -> None:
    """
    可视化原始转弯概率数据和平滑后的转弯概率数据。

    参数:
        values (list): 每个周期内的值。
        period (int): 每个周期持续的时长。
        smooth_values (list): 平滑后的每分钟的值。
    """
    # 创建时间间隔
    time_intervals = np.arange(len(smooth_values))

    # 将 values 按照 period 重复
    repeated_values = repeat_values(values, period)

    # 绘制原始转弯概率数据
    plt.plot(time_intervals, repeated_values, 'o-', label='Original')
    # 绘制平滑后的转弯概率数据
    plt.plot(time_intervals, smooth_values, 's-', label='Smoothed')

    # 设置图表标题和轴标签
    plt.title('Comparison of Interpolations Results')
    plt.xlabel('Time Intervals')

    # 添加图例
    plt.legend()

    # 显示图表
    plt.show()