'''
@Author: WANG Maonan
@Date: 2024-08-10 20:18:53
@Description: 将 SNR 转换为 Packet Loss
@LastEditTime: 2024-08-10 20:27:00
'''
import numpy as np

def calculate_outage_probability(snr_db, bandwidth_hz=30e3, target_rate_bps=20e3):
    """
    Calculate the outage probability in a Rayleigh fading channel.

    Parameters:
    snr_db (float): The signal-to-noise ratio in decibels (dB).
    bandwidth_hz (float): The channel bandwidth in Hertz (default is 30kHz).
    target_rate_bps (float): The target rate in bits per second (default is 20kb/s).

    Returns:
    float: The calculated outage probability.
    """
    # Convert SNR from dB to linear scale
    snr_linear = 10 ** (snr_db / 10)
    
    # Calculate the threshold u based on the target rate and SNR
    u_threshold = (2 ** (target_rate_bps / bandwidth_hz) - 1) / snr_linear
    
    # Calculate the outage probability
    outage_probability = 1 - np.exp(-u_threshold)
    
    return outage_probability