'''
@Author: WANG Maonan
@Date: 2023-12-01 20:14:30
@Description: 分析 Trip Info 文件
@LastEditTime: 2023-12-01 20:15:54
'''
from tshub.utils.parse_trip_info import TripInfoStats
from tshub.utils.get_abs_path import get_abs_path

path_convert = get_abs_path(__file__)

if __name__ == '__main__':
    stats = TripInfoStats(path_convert('./single_junction.tripinfo.xml'))
    print(stats.output_str())
    stats.to_csv(path_convert('./output.csv'))