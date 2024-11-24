'''
@Author: WANG Maonan
@Date: 2024-06-25 22:01:24
@Description: 分析 tripinfo 文件
LastEditTime: 2024-10-02 16:55:44
'''
import numpy as np
from loguru import logger
from typing import Dict, List
import xml.etree.ElementTree as ET

class TripInfoAnalysis:
    def __init__(self, xml_file) -> None:
        with open(xml_file, 'r') as file:
            self.xml_data = file.read()
        logger.info(f"SIM: 读取 {xml_file} 完成.")
        self.metrics = self.parse_xml()
        logger.info(f"SIM: 解析 {xml_file} 完成.")

    def parse_xml(self)-> Dict[str, List]:
        """解析 xml 文件, 获得各个指标
        """
        tree = ET.ElementTree(ET.fromstring(self.xml_data))
        root = tree.getroot()

        metrics = {
            'travelTime': [],
            'routeLength': [],
            'waitingTime': [],
            'waitingCount': [],
            'stopTime': [],
            'timeLoss': [],
            'CO_abs': [],
            'CO2_abs': [],
            'HC_abs': [],
            'PMx_abs': [],
            'NOx_abs': [],
            'fuel_abs': [],
            'electricity_abs': []
        }

        for tripinfo in root.findall('tripinfo'):
            metrics['travelTime'].append(float(tripinfo.get('duration')))
            metrics['routeLength'].append(float(tripinfo.get('routeLength')))
            metrics['waitingTime'].append(float(tripinfo.get('waitingTime')))
            metrics['waitingCount'].append(int(tripinfo.get('waitingCount')))
            metrics['stopTime'].append(float(tripinfo.get('stopTime')))
            metrics['timeLoss'].append(float(tripinfo.get('timeLoss')))
            
            emissions = tripinfo.find('emissions')
            metrics['CO_abs'].append(float(emissions.get('CO_abs')) / 1000)  # Convert mg to g
            metrics['CO2_abs'].append(float(emissions.get('CO2_abs')) / 1000)  # Convert mg to g
            metrics['HC_abs'].append(float(emissions.get('HC_abs')) / 1000)  # Convert mg to g
            metrics['PMx_abs'].append(float(emissions.get('PMx_abs')) / 1000)  # Convert mg to g
            metrics['NOx_abs'].append(float(emissions.get('NOx_abs')) / 1000)  # Convert mg to g
            metrics['fuel_abs'].append(float(emissions.get('fuel_abs')) / (750 * 1000))  # Convert mg to L
            metrics['electricity_abs'].append(float(emissions.get('electricity_abs')))

        return metrics

    def calculate_stats(self, values):
        return {
            'mean': np.mean(values),
            'variance': np.var(values),
            'max': np.max(values),
            'min': np.min(values),
            'percentile_25': np.percentile(values, 25),
            'percentile_50': np.percentile(values, 50),
            'percentile_75': np.percentile(values, 75)
        }

    def get_all_stats(self):
        all_stats = {}
        for key, values in self.metrics.items():
            all_stats[key] = self.calculate_stats(values)
        return all_stats

    def print_stats(self) -> None:
        """将指标输出, 方便统计结果
        """
        all_stats = self.get_all_stats()
        for metric, stats in all_stats.items():
            print(f"Statistics for {metric}:")
            for stat_name, value in stats.items():
                print(f"  {stat_name.capitalize()}: {value:.2f}")
            print()  # Blank line for better readability
    
    def print_stats_as_table(self) -> None:
        """将指标以表格形式输出, 使用逗号隔开, 方便粘贴到 CSV 文件
        """
        all_stats = self.get_all_stats()
        header = "Metric,Mean,Variance,Max,Min,25th,50th,75th"
        print(header)
        for metric, stats in all_stats.items():
            row = f"{metric},{stats['mean']:.2f},{stats['variance']:.2f},{stats['max']:.2f},{stats['min']:.2f},{stats['percentile_25']:.2f},{stats['percentile_50']:.2f},{stats['percentile_75']:.2f}"
            print(row)