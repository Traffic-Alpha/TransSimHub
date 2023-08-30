'''
@Author: WANG Maonan
@Date: 2023-08-24 16:16:20
@Description: 处理 defaultdict
@LastEditTime: 2023-08-24 16:20:55
'''
from collections import defaultdict
from typing import Union

def create_nested_defaultdict() -> defaultdict:
    """生成无限嵌套的 defaultdict
    """
    return defaultdict(create_nested_defaultdict)


def defaultdict2dict(data: Union[defaultdict, dict]) -> dict:
    """将嵌套的 defaultdict 转换为普通的 dict
    """
    if isinstance(data, dict):
        return {k: defaultdict2dict(v) for k, v in data.items()}
    else:
        return data