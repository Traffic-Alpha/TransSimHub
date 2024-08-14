'''
@Author: WANG Maonan
@Date: 2024-08-10 20:22:49
@Description: 
@LastEditTime: 2024-08-10 21:04:47
'''
import numpy as np
import matplotlib.pyplot as plt
from tshub.v2x import calculate_outage_probability

if __name__ == '__main__':
    snr_input = 10  # SNR in dB
    outage_prob = calculate_outage_probability(snr_input)
    print(f"The outage probability is {outage_prob:.4f}")

    # 绘制 snr 与 packet loss 的关系
    snr_values = np.linspace(-20, 30, 300)
    outage_probabilities = [calculate_outage_probability(snr) for snr in snr_values]

    # Plotting the outage probability against SNR
    plt.figure(figsize=(10, 6))
    plt.plot(snr_values, outage_probabilities, label='Outage Probability')
    plt.xlabel('SNR (dB)')
    plt.ylabel('Packet Loss Probability')
    plt.title('Packet Loss Probability vs. SNR')
    plt.grid(True)
    plt.legend()
    plt.show()