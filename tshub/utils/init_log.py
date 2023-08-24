'''
@Author: WANG Maonan
@Date: 2023-08-23 11:07:43
@Description: 初始化 Log, 分为以下几个部分:
1. INFO 级别的日志打印在控制台;
2. 仿真相关的日志存储在 SIM 开头的文件
3. 算法相关的日志存储在 Traing 开头的文件
@LastEditTime: 2023-08-24 15:28:27
'''
import os
from loguru import logger
from datetime import datetime

def simulation_filter(record) -> bool:
    """单独过滤出仿真部分产生的日志

    Args:
        record (_type_): _description_
    """
    if 'SIM' in record['message']:
        return True
    return False


def training_filter(record) -> bool:
    """单独过滤出训练部分的日志

    Args:
        record (_type_): _description_

    Returns:
        bool: _description_
    """
    if 'RL' in record['message']:
        return True
    return False


def set_logger(log_path):
    now = datetime.strftime(datetime.now(),'%Y-%m-%d_%H_%M_%S')
    log_path = os.path.join(log_path, now)
    if not os.path.exists(log_path):
        os.makedirs(log_path, exist_ok=True)

    logger.add(
        os.path.join(log_path, './SIM-{time}.log'), 
        format="{time} | {level:<6} | {message}", 
        filter=simulation_filter, 
        level="DEBUG", 
        rotation="7 MB"
    )

    logger.add(
        os.path.join(log_path, './Traing-{time}.log'), 
        format="{time} {level} {message}", 
        filter=training_filter, 
        level="DEBUG", 
        rotation="7 MB"
    )