'''
@Author: WANG Maonan
@Date: 2024-06-25 22:01:24
@Description: 分析 tripinfo 文件
LastEditTime: 2025-04-29 17:17:28
'''
import numpy as np
import pandas as pd
from loguru import logger
from typing import Dict, List
import xml.etree.ElementTree as ET

class TripInfoAnalysis:
    def __init__(self, xml_file_path):
        try:
            with open(xml_file_path, 'r', encoding='utf-8') as file:
                xml_content = file.read()
            self.df = self.__xml_to_dataframe(xml_content) # 转换为 panda dataframe
            logger.info(f"SIM: 读取 {xml_file_path} 成功.")
        except FileNotFoundError:
            logger.error(f"SIM: 错误, 文件 {xml_file_path} 未找到。")
            self.df = None
        except Exception as e:
            logger.error(f"SIM: 发生未知错误：{e}")
            self.df = None

    def __xml_to_dataframe(self, xml_content):
        """将 xml 文件转换为 dataframe 格式
        """
        root = ET.fromstring(xml_content)
        rows = []
        for tripinfo in root.findall('tripinfo'):
            tripinfo_attr = tripinfo.attrib
            emissions = tripinfo.find('emissions')
            if emissions is not None:
                emissions_attr = emissions.attrib
                combined_attr = {**tripinfo_attr, **emissions_attr}
                rows.append(combined_attr)
        return pd.DataFrame(rows)


    def calculate_multiple_stats(self, metrics:List[str]):
        if self.df is not None:
            all_results = {}
            for metric in metrics:
                if metric in self.df.columns:
                    values = pd.to_numeric(self.df[metric])
                    stats = {
                        'mean': np.mean(values),
                        'variance': np.var(values),
                        'max': np.max(values),
                        'min': np.min(values),
                        'percentile_25': np.percentile(values, 25),
                        'percentile_50': np.percentile(values, 50),
                        'percentile_75': np.percentile(values, 75)
                    }
                    all_results[metric] = stats
                else:
                    logger.info(f"SIM: 列 {metric} 不存在于数据中。")
            return all_results
        return None

    def statistics_by_vehicle_type(self, metrics:List[str]):
        if self.df is not None:
            valid_metrics = [metric for metric in metrics if metric in self.df.columns]
            if valid_metrics:
                result = {}
                for metric in valid_metrics:
                    self.df[metric] = pd.to_numeric(self.df[metric])
                    grouped = self.df.groupby('vType')[metric]
                    stats = grouped.agg([
                        'mean', 'var', 'max', 'min',
                        lambda x: np.percentile(x, 25),
                        lambda x: np.percentile(x, 50),
                        lambda x: np.percentile(x, 75)
                    ])
                    stats.columns = ['mean', 'variance', 'max', 'min', 'percentile_25', 'percentile_50', 'percentile_75']
                    result[metric] = stats
                return result
            else:
                logger.info("SIM: 没有有效的指标用于按车辆类型统计。")
                return None
        return None

    @staticmethod
    def print_stats_as_table(stats) -> None:
        """将指标以表格形式输出, 使用逗号隔开, 方便粘贴到 CSV 文件
        """
        stat_names = ['mean', 'variance', 'max', 'min', 'percentile_25', 'percentile_50', 'percentile_75']

        # Print header
        header = "Statistic," + ",".join(stats.keys())
        print(header)

        # Print each row
        for stat_name in stat_names:
            row = stat_name.capitalize() + ","
            row += ",".join(f"{stats[metric][stat_name]:.2f}" for metric in stats.keys())
            print(row)