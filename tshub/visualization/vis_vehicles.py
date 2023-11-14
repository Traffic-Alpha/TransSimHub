'''
@Author: WANG Maonan
@Date: 2023-11-12 16:20:48
@Description: 对车辆进行可视化
@LastEditTime: 2023-11-13 19:21:52
'''
import numpy as np
import matplotlib.patches as patches
from typing import Dict
from matplotlib.transforms import Affine2D

def plot_vehicle(ax, focus_id:str=None, vehicles:Dict[str, Dict[str, float]]=None) -> None:
    for veh_id, veh_info in vehicles.items():
        # Create a rectangle with center at origin
        rectangle = patches.Rectangle(
            (-veh_info['length'], -veh_info['width']/2.0), 
            veh_info['length'], 
            veh_info['width'], 
            color='orange' if focus_id == veh_id else 'blue', 
            alpha=0.5,
            edgecolor='black',
            linewidth=1.5
        )

        # Convert the heading to matplotlib's angle
        angle = 90 - veh_info['heading']
        if angle < 0: angle += 360

        # Create an affine transformation
        t = Affine2D().rotate_deg_around(0, 0, angle).translate(*veh_info['position'])

        # Apply the transformation
        rectangle.set_transform(t + ax.transData)

        # Add the rectangle to the plot
        ax.add_patch(rectangle)

        # Add an arrow to represent direction
        speed_ratio = 1/15*veh_info['speed']
        arrow_length = veh_info['length'] / 2.0 * speed_ratio # 箭头长度和 speed 有关

        if arrow_length > 0: # 只有运动的车辆才会有箭头
            arrow_dx = arrow_length * np.sin(np.radians(veh_info['heading']))
            arrow_dy = arrow_length * np.cos(np.radians(veh_info['heading']))
            arrow = patches.FancyArrow(
                veh_info['position'][0] - arrow_dx/2, 
                veh_info['position'][1] - arrow_dy/2, 
                arrow_dx, arrow_dy, 
                width=0.1, color='red', 
                head_width=1.0, 
                head_length=1.0
            )
            ax.add_patch(arrow)
        else: # 如果没有速度, 就绘制一个小红点
            arrow_dx = veh_info['length']/3 * np.sin(np.radians(veh_info['heading']))
            arrow_dy = veh_info['length']/3 * np.cos(np.radians(veh_info['heading']))
            ax.plot(
                veh_info['position'][0]-arrow_dx, 
                veh_info['position'][1]-arrow_dy, 
                'ro',
                markersize=1,
            )


