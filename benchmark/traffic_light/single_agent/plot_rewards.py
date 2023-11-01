'''
@Author: WANG Maonan
@Date: 2023-11-01 23:46:03
@Description: 
@LastEditTime: 2023-11-01 23:46:04
'''
from tshub.utils.plot_curves import plot_reward_curve
from tshub.utils.get_abs_path import get_abs_path
path_convert = get_abs_path(__file__)


if __name__ == '__main__':
    log_files = [
        path_convert(f'./log/{i}.monitor.csv')
        for i in range(1, 6)
    ]
    plot_reward_curve(log_files)