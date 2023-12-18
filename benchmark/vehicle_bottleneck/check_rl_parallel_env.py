'''
@Author: WANG Maonan
@Date: 2023-10-30 23:01:03
@Description: 检查同时开启多个仿真环境
-> 首先设置一个环境, GUI 打开, 查看仿真结束是否正确
-> 接着开启多个仿真, 关闭 GUI, 查看是否可以运行
@LastEditTime: 2023-12-18 22:05:11
'''
from loguru import logger
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from env_utils.make_veh_env import make_parallel_env

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

if __name__ == '__main__':
    sumo_cfg = path_convert("../sumo_envs/veh_bottleneck/veh.sumocfg")
    log_path = path_convert('./log/')

    veh_env = make_parallel_env(
        num_envs=4,
        prefix='check_parallel',
        sumo_cfg=sumo_cfg,
        warmup_steps=100, # reset 的时候初始的步数
        num_seconds=600, # 仿真时间 (这里实际没有被用到)
        ego_ids=[
            'E0__0__ego.1', 
            'E0__1__ego.2', 
            'E0__2__ego.3',
        ], # ego vehicle 的 id
        edge_ids=['E0','E1','E2'],
        edge_lane_num={
            'E0':4,
            'E1':4,
            'E2':4
        }, # 每一个 edge 对应的车道数
        bottle_necks=['E2'], # bottleneck 的 edge id
        bottle_neck_positions=(700, 70), # bottle neck 的坐标, 用于计算距离
        calc_features_lane_ids=[
            'E0_0', 'E0_1', 'E0_2', 'E0_3',
            'E1_0', 'E1_1', 'E1_2', 'E1_3',
            'E2_0', 'E2_1', 'E2_2', 'E2_3',
        ], # 计算对应的 lane 的信息        
        use_gui=False,
        log_file=log_path
    )

    rollouts = veh_env.rollout(1_000, break_when_any_done=False)
    for r in rollouts:
        logger.info(f'RL: {r}')