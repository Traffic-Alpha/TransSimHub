'''
@Author: WANG Maonan
@Date: 2023-11-12 16:22:16
@Description: 对地图的可视化
@LastEditTime: 2023-11-13 19:21:58
'''
import matplotlib.pyplot as plt

from .vis_map_feature import plot_map_feature
from .vis_vehicles import plot_vehicle

def render_map(focus_id, map_edges, map_nodes, vehicles, x_range, y_range):
    fig, ax = plt.subplots(figsize=(6, 6))

    plot_map_feature(ax, map_edges, map_nodes)
    plot_vehicle(ax, focus_id, vehicles)

    ax.set_axis_off() # 去掉 x,y 轴
    plt.axis('equal') # x,y 的比例一样

    # 设置 x 和 y 轴的范围
    ax.set_xlim(x_range)
    ax.set_ylim(y_range)

    fig = plt.gcf() # 获得当前的图像
    return fig
