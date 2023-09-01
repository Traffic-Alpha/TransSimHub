'''
@Author: WANG Maonan
@Date: 2023-08-31 15:43:07
@Description: 对转向概率进行插值, 对插值前后的结果进行可视化
@LastEditTime: 2023-09-01 14:12:23
'''
from tshub.sumo_tools.interpolation.values_interpolation import InterpolationValues
from tshub.sumo_tools.interpolation.visualize_interpolations import visualize_interpolations

turn_def = [0.25, 0.5, 0.4, 0.7, 0.4, 0.5] # 每个时间段的转向比
period = [10, 10, 10, 15, 10, 15] # 每个时间段的持续时间
smooth_turn_def = InterpolationValues(values=turn_def, intervals=period)

# test _interpolation
print(smooth_turn_def._interpolation(15))
print(smooth_turn_def._interpolation(30))

# test get_smooth_turndef
smooth_turndef_list = smooth_turn_def.get_smooth_values()
print(smooth_turndef_list)

# visualize
visualize_interpolations(values=turn_def, period=period, smooth_values=smooth_turndef_list)