'''
@Author: WANG Maonan
@Date: 2024-08-09 22:06:58
@Description: 单路口, 只包含两个车辆的测试
1. RSU 设置在路口中心
2. 只有两个车辆, 不同方向行驶
@LastEditTime: 2024-08-14 19:32:26
'''
import matplotlib.pyplot as plt
from tshub.utils.init_log import set_logger
from tshub.utils.get_abs_path import get_abs_path
from tshub.tshub_env.tshub_env import TshubEnvironment
# V2I and V2V
from tshub.v2x import V2IChannel, V2VChannel

path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

def update_position(veh_obs, vehicle_id, current_position):
    if vehicle_id in veh_obs:
        previous_position = current_position.get(vehicle_id, None)
        current_position[vehicle_id] = veh_obs[vehicle_id]['position']
        return previous_position, current_position[vehicle_id]
    return None, None

class SNRPlotter:
    def __init__(self) -> None:
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1)
        plt.tight_layout(pad=3.0)

    def plot(self, distances, snrs, subplot, title, color='b'):
        x = list(range(len(distances)))
        ax_distance = subplot
        ax_distance.plot(x, distances, color + '-')
        ax_distance.set_title(title)
        ax_distance.set_ylabel('Distance (m)', color=color)
        ax_distance.tick_params('y', colors=color)

        ax_snr = subplot.twinx()
        ax_snr.plot(x, snrs, 'r-')
        ax_snr.set_ylabel('SNR', color='r')
        ax_snr.tick_params('y', colors='r')

    def show(self) -> None:
        plt.show()

    def save(self, filename) -> None:
        plt.tight_layout()
        self.fig.savefig(filename, bbox_inches='tight')

# Main simulation loop
def run_simulation(tshub_env, v2i_channel, v2v_channel):
    obs = tshub_env.reset()
    done = False
    current_positions = {} # 记录车辆当前的位置
    v2i_snrs, v2v_snrs = [], []

    while not done:
        actions = {'vehicle': {}, 'tls': {'htddj_gsndj': 0}}
        obs, reward, info, done = tshub_env.step(actions=actions)
        
        prev_pos_A, curr_pos_A = update_position(obs['vehicle'], 'gsndj_n7__0.5', current_positions)
        prev_pos_B, curr_pos_B = update_position(obs['vehicle'], 'gsndj_s4__0.5', current_positions)

        # 更新 V2I 的 SNR
        if prev_pos_A is not None:
            v2i_snr = v2i_channel.get_snr(
                previous_position_obj=prev_pos_A,
                current_position_obj=curr_pos_A,
                is_ms_received=True, is_ms_transmit=False
            )
            v2i_snrs.append((v2i_channel.distance, v2i_snr))

        # 更新 V2V 的 SNR
        if prev_pos_A and prev_pos_B:
            v2v_snr = v2v_channel.get_snr(
                previous_position_obj_A=prev_pos_A, 
                current_position_obj_A=curr_pos_A,
                previous_position_obj_B=prev_pos_B, 
                current_position_obj_B=curr_pos_B,
                is_ms_received=True, is_ms_transmit=True
            )
            v2v_snrs.append((v2v_channel.distance, v2v_snr))

    tshub_env._close_simulation()

    # Plotting
    plotter = SNRPlotter()
    if v2i_snrs:
        v2i_distance, v2i_snr = zip(*v2i_snrs)
        plotter.plot(v2i_distance, v2i_snr, plotter.ax1, 'V2I', 'b')

    if v2v_snrs:
        v2v_distance, v2v_snr = zip(*v2v_snrs)
        plotter.plot(v2v_distance, v2v_snr, plotter.ax2, 'V2V', 'b')
    plt.subplots_adjust(hspace=0.5) # Adjust the horizontal space between the subplot
    plotter.show()
    plotter.save(path_convert("./snr_figure.png"))

if __name__ == '__main__':
    # 初始化环境
    sumo_cfg = path_convert("../../sumo_env/single_junction/env/single_junction.sumocfg")
    tshub_env = TshubEnvironment(
        sumo_cfg=sumo_cfg,
        is_map_builder_initialized=False,
        is_aircraft_builder_initialized=False, 
        is_vehicle_builder_initialized=True, 
        is_traffic_light_builder_initialized=True,
        tls_ids=['htddj_gsndj'],
        vehicle_action_type='lane', 
        tls_action_type='next_or_not',
        use_gui=True, num_seconds=300
    ) # 初始化环境

    # 初始化 V2X Channel Model
    v2i_channel = V2IChannel(BS_position=(1779.29, 931.97))
    v2v_channel = V2VChannel(power_ms=-35)

    # 开始仿真
    run_simulation(tshub_env, v2i_channel, v2v_channel)