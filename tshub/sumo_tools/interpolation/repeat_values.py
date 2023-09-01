'''
@Author: WANG Maonan
@Date: 2023-08-31 17:01:13
@Description: 
@LastEditTime: 2023-08-31 17:03:33
'''
from typing import List

def repeat_values(values, period) -> List[float]:
    """
    根据 period 列表中的数值，对 values 列表进行重复。

    例如:
    + period 表示每个阶段的持续时间 (分钟);
    + values 表示每个阶段内每分钟的结果

    例如:
    + values = [0.25, 0.5] # 每个时间段的转向比
    + period = [3, 3] # 每个时间段的持续时间
    -> 这里会转换为 [0.25, 0.25, 0.25, 0.5, 0.5, 0.5], 重复对应的次数

    参数:
        values (list): 需要重复的数值。
        period (list): 每个时间段的持续时间列表。

    返回:
        list: 重复后的结果。
    """
    repeated_values = []
    for i, num in enumerate(values):
        repeated_values.extend([num] * period[i])
    return repeated_values