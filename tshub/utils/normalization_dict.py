'''
@Author: WANG Maonan
@Date: 2023-08-31 17:53:38
@Description: 字典中的值归一化, 使其和为 1
@LastEditTime: 2023-08-31 17:55:06
'''
def normalize_dict(input_dict):
    """
    将字典中的值归一化，使其和为1。例如：
    + Input: a = {1:1, 2:2, 3:3},
    + Output: {1: 0.16666666666666666, 2: 0.3333333333333333, 3: 0.5}

    Args:
        input_dict (dict): 输入的字典数据。

    Returns:
        dict: 归一化后的字典。
    """
    # 计算字典值的总和
    total_value = sum(input_dict.values())

    # 归一化字典
    normalized_dict = {key: value / total_value for key, value in input_dict.items()}

    return normalized_dict
