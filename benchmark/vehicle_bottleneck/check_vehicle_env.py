'''
@Author: WANG Maonan
@Date: 2023-10-27 20:16:14
@Description: 检查车辆环境
@LastEditTime: 2023-12-19 22:01:50
'''
from loguru import logger
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path

from env_utils.veh_env import VehEnvironment
from env_utils.veh_wrapper import VehEnvWrapper

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

if __name__ == '__main__':
    sumo_cfg = path_convert("../sumo_envs/veh_bottleneck/veh.sumocfg")
    log_path = path_convert('./log/test_env.log')

    ac_env = VehEnvironment(
        sumo_cfg=sumo_cfg,
        num_seconds= 650, # 秒
        vehicle_action_type='lane_continuous_speed',
        use_gui=True,
        trip_info=path_convert('./three_nocontrol.tripinfo.xml')
    )
    ac_env_wrapper = VehEnvWrapper(
        env=ac_env, 
        warmup_steps=80, 
        ego_ids=[
            'E0__0__ego.1', 
            'E0__1__ego.2', 
            'E0__2__ego.3',
        ], # ego vehicle 的 id
        edge_ids=['E0','E1','E2'], # 所有考虑的 edge, 只有在这些 edge 上才会对 ego vehicle 进行控制
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
        filepath=log_path
    )

    for constant_speed in range(6): # 测试不同的速度
        done = False
        ac_env_wrapper.reset()
        while not done:
            # 获取环境中所有车辆的ID
            # 为每个车辆生成一个动作
            action = {ego_id: constant_speed for ego_id in ac_env_wrapper.ego_ids}
            states, rewards, truncated, dones, infos = ac_env_wrapper.step(action=action)
            done = all([dones[_ego_id] for _ego_id in ac_env_wrapper.ego_ids])
            logger.info(f'SIM: Reward: {rewards}')

    ac_env_wrapper.close()