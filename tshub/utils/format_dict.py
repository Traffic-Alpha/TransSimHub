'''
@Author: WANG Maonan
@Date: 2023-08-24 17:34:14
@Description: 将 dict 转换为字符串, 带有环行
LastEditTime: 2025-01-21 19:57:27
'''
import json
import numpy as np
from loguru import logger

def dict_to_str(my_dict) -> str:
    """将字典转换为格式化的 JSON 字符串
    """
    def convert_to_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()  # 将ndarray转换为列表
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    json_str = json.dumps(my_dict, indent=4, default=convert_to_serializable)
    return json_str

def save_str_to_json(my_dict, file_path:str, indent:int=4) -> None:
    """将 dict 串保存为 JSON 文件
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(my_dict, f, ensure_ascii=False, indent=indent)
    logger.warning('SIM: 字典已成功保存到 {file_path}')