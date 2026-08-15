'''
@Author: WANG Maonan
@Date: 2024-05-29 17:27:13
@Description: 对 SNIR 进行可视化
@LastEditTime: 2024-05-29 18:45:01
'''
import numpy as np
import matplotlib.pyplot as plt

def render_map(
        x_min, y_min, resolution, grid_z, 
        trajectories, goal_points,
        img_path
    ) -> None:
    fig, ax = plt.subplots()

    plot_snir_map(ax, x_min, y_min, resolution, grid_z, img_path) # 绘制 SNIR
    plot_trajectories(ax, trajectories) # 绘制 aircraft 的轨迹
    plot_goal_points(ax, goal_points) # 绘制目标点
    
    # 保存图像
    plt.savefig(img_path)
    
    # 显示图像
    plt.show()


def plot_snir_map(ax, x_min, y_min, resolution, grid_z, img_path):
    """绘制 SNIR 的底图
    """
    # 计算 x 和 y 坐标
    y_max, x_max = grid_z.shape
    
    # 绘制 grid_z 数值
    cax = ax.imshow(grid_z, extent=(x_min, x_min + x_max * resolution, y_min, y_min + y_max * resolution), origin='lower')
    
    # 添加颜色条
    plt.colorbar(cax, ax=ax)


def plot_trajectories(ax, trajectories):
    """绘制车辆轨迹信息
    """
    for vehicle, path in trajectories.items():
        # 提取 x 和 y 坐标
        x_coords, y_coords = zip(*path)
        
        # 绘制轨迹
        ax.plot(x_coords, y_coords, label=vehicle)
        
        # 绘制轨迹的最后一个点
        if path:
            ax.scatter(x_coords[-1], y_coords[-1], s=100, c='red', marker='*', label=f"{vehicle} current")

    # 添加图例
    ax.legend()


def plot_goal_points(ax, goal_points):
    """绘制目标点
    """
    for point in goal_points:
        ax.scatter(*point, s=100, c='blue', marker='o', label=f"Goal at {point}")

    # 添加图例
    ax.legend()
