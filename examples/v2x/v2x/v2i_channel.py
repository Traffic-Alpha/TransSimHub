'''
@Author: WANG Maonan
@Date: 2024-08-09 18:03:12
@Description: 测试 V2I 模型
@LastEditTime: 2024-08-09 21:30:01
'''
import matplotlib.pyplot as plt
from tshub.v2x.v2i_channel import V2IChannel

if __name__ == '__main__':
    v2i_channel = V2IChannel(BS_position=(0,0)) # 基站位于原点
    vehicle_speed = 13 # 车辆速度为 13m/s
    previous_vehicle_pos, current_vehicle_pos = [0,0], [0,0]
    
    time_steps = 360
    channels_with_fastfading_list = []
    snr_list = []
    for _ in range(time_steps):
        previous_vehicle_pos = current_vehicle_pos.copy()
        current_vehicle_pos[0] += vehicle_speed
        
        # 计算 path loss + shadowing
        channels_with_fastfading = v2i_channel.get_channels_with_fastfading(
            previous_vehicle_pos, current_vehicle_pos
        )
        channels_with_fastfading_list.append(channels_with_fastfading)

        # 计算 snr
        snr = v2i_channel.get_snr(
            previous_vehicle_pos, current_vehicle_pos, 
            is_ms_transmit=True, is_ms_received=False # V2I
        )
        snr_list.append(snr)        
    
    # Create a figure and a set of subplots
    fig, ax1 = plt.subplots()

    # Plot channels_with_fastfading on y1
    ax1.plot([i*vehicle_speed for i in range(time_steps)], channels_with_fastfading_list, 'b-')
    ax1.set_xlabel('Distance (m)')
    ax1.set_ylabel('Channels with Fast Fading', color='b')
    ax1.tick_params('y', colors='b')

    # Create a second y-axis that shares the same x-axis
    ax2 = ax1.twinx()

    # Plot snr on y2
    ax2.plot([i*vehicle_speed for i in range(time_steps)], snr_list, 'r-')
    ax2.set_ylabel('SNR', color='r')
    ax2.tick_params('y', colors='r')

    plt.title('Channels with Fast Fading and SNR')
    plt.grid(True)
    plt.show()
