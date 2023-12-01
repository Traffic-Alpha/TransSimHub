'''
@Author: WANG Maonan
@Date: 2023-11-24 16:06:00
@Description: 解析 Trip Info 的信息
@LastEditTime: 2023-12-01 20:15:07
'''
import sumolib
import pandas as pd
from tshub.utils.get_abs_path import get_abs_path

path_convert = get_abs_path(__file__)

class TripInfoStats(object):
    def __init__(self, filepath:str):
        """统计 tripinfo 的信息

        Args:
            filepath (str): tripinfo 的信息
        """
        self.filepath = filepath
        self.vTypeStats = self.__calculate_stats()

    def __calculate_stats(self):
        vTypeStats = {}
        for tripinfo in sumolib.xml.parse(self.filepath, ['tripinfo']):
            vType = tripinfo.vType # 获得车辆的类型

            if vType not in vTypeStats:
                vTypeStats[vType] = {
                    "duration": sumolib.miscutils.Statistics(f"{vType} duration"),
                    "routeLength": sumolib.miscutils.Statistics(f"{vType} routeLength"),
                    "speed": sumolib.miscutils.Statistics(f"{vType} speed"),
                    "stopTime": sumolib.miscutils.Statistics(f"{vType} stopTime"),
                    "timeLoss": sumolib.miscutils.Statistics(f"{vType} timeLoss"),
                    "waitingCount": sumolib.miscutils.Statistics(f"{vType} waitingCount"),
                    "waitingTime": sumolib.miscutils.Statistics(f"{vType} waitingTime"),
                }

            vTypeStats[vType]["duration"].add(float(tripinfo.duration))
            vTypeStats[vType]["routeLength"].add(float(tripinfo.routeLength))
            vTypeStats[vType]["speed"].add(float(tripinfo.routeLength) / float(tripinfo.duration))
            vTypeStats[vType]["stopTime"].add(float(tripinfo.stopTime))
            vTypeStats[vType]["timeLoss"].add(float(tripinfo.timeLoss))
            vTypeStats[vType]["waitingCount"].add(int(tripinfo.waitingCount))
            vTypeStats[vType]["waitingTime"].add(float(tripinfo.waitingTime))

        return vTypeStats

    def output_str(self):
        output = ""
        for vType, stats in self.vTypeStats.items():
            output += f"Statistics for vType {vType}:\n"
            for stat_name, stat in stats.items():
                mean, std = stat.meanAndStdDev()
                output += f"  {stat_name}: count={stat.count()}, min={stat.min}, max={stat.max}, median={stat.median()}, mean={mean}, std={std}\n"
        return output

    def to_csv(self, output_path):
        data = []
        for vType, stats in self.vTypeStats.items():
            for stat_name, stat in stats.items():
                mean, std = stat.meanAndStdDev()
                data.append({
                    'vType': vType,
                    'stat_name': stat_name,
                    'count': stat.count(),
                    'min': stat.min,
                    'max': stat.max,
                    'median': stat.median(),
                    'mean': mean,
                    'std': std
                })
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
