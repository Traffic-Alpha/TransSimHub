'''
@Author: WANG Maonan
@Date: 2023-08-24 17:34:14
@Description: 将 dict 转换为字符串, 带有环行
@LastEditTime: 2023-08-31 20:17:33
'''
import json
import numpy as np

def dict_to_str(my_dict) -> str:
    """将字典转换为格式化的JSON字符串
    """
    def convert_to_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()  # 将ndarray转换为列表
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    json_str = json.dumps(my_dict, indent=4, default=convert_to_serializable)
    return json_str