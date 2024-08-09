'''
@Author: WANG Maonan
@Date: 2024-08-09 11:26:39
@Description: V2X Channel Model (默认有 V2I 和 V2V, 支持自定义模型)
@LastEditTime: 2024-08-09 21:29:01
'''
import numpy as np
from typing import List
from loguru import logger
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class V2XChannel(ABC):
    """
    Base class for V2X channel models.
    """
    h_bs:float = field(default=25)  # Base station antenna height in meters.
    h_ms:float = field(default=1.5)  # Mobile station antenna height in meters.
    power_bs:float = field(default=40) # Base station power (改变 snr 的绝对数值大小)
    power_ms:float = field(default=-35) # Mobile station power, 如果车辆使用的是蜂窝移动网络，那么车辆接收端的信号强度可能会显示为-50 dBm 到 -100 dBm 之间
    fc:float = field(default=2.4) # Carrier frequency in GHz.
    decorrelation_distance:float = field(default=50)  # Distance over which the signal decorrelation occurs.
    shadow_std:float = field(default=8)  # Standard deviation of the shadowing component in dB.
    sig2_dB_bs:float = field(default=-57) # Base station noise power, dB (越大噪声越大)
    sig2_dB_ms:float = field(default=-114) # Mobile station noise power, dB
    antrenna_gain_bs:float = field(default=8) # 基站增益, dBi
    antrenna_gain_ms:float = field(default=3) # Mobile station 增益, dBi
    noise_figure_bs:float = field(default=5) # shadowing standard deviation for base station, dB
    noise_figure_ms:float = field(default=9) # shadowing standard deviation for mobile station, dB

    def get_channels_with_fastfading(
            self, 
            previous_position_obj: List[float], 
            current_position_obj: List[float],
        )->float:
        free_path_loss = self._get_path_loss(current_position_obj)
        shadowing = self._get_shadowing(previous_position_obj, current_position_obj)
        noise = np.random.normal(0, 1)
        return (free_path_loss + shadowing + noise)
    
    def get_received_power(
            self, 
            previous_position_obj: List[float], 
            current_position_obj: List[float],
            is_ms_transmit:bool = True, # 是否是 ms 作为发送, V2X
            is_ms_received:bool = True # 是否是 ms 作为接收, X2V
        )->float:
        channels_with_fastfading = self.get_channels_with_fastfading(
            previous_position_obj, current_position_obj
        )

        noise_figure = self.noise_figure_ms if is_ms_received else self.noise_figure_bs
        if is_ms_transmit: # ms->bs/ms, 所以使用 power_ms
            received_power = self.power_ms - channels_with_fastfading - noise_figure
        else: # bs -> ms
            received_power = self.power_bs - channels_with_fastfading - noise_figure
            
        return received_power
    
    def get_snr(
            self, 
            previous_position_obj: List[float], 
            current_position_obj: List[float],
            is_ms_transmit:bool = True, # 是否是 ms 作为发送, V2X
            is_ms_received:bool = True # 是否是 ms 作为接收, X2V
        )->float:
        if is_ms_transmit and is_ms_received:
            logger.info('SIM: Calculate **V2V** SNR')
        elif is_ms_transmit and not is_ms_received:
            logger.info('SIM: Calculate **V2I** SNR')
        elif not is_ms_transmit and is_ms_received:
            logger.info('SIM: Calculate **I2V** SNR')
        else:
            raise ValueError("Invalid combination of transmission and reception for SNR calculation.")

        received_power = self.get_received_power(
            previous_position_obj, 
            current_position_obj,
            is_ms_transmit=is_ms_transmit,
            is_ms_received=is_ms_received,
        )

        noise_power_dbm = self.sig2_dB_ms if is_ms_transmit else self.sig2_dB_bs
        return 10*np.log10(V2XChannel.dbm2w(received_power)/V2XChannel.dbm2w(noise_power_dbm))
    
    @abstractmethod
    def _get_path_loss(self):
        raise NotImplementedError
    
    @abstractmethod
    def _get_shadowing(self):
        raise NotImplementedError
    
    @staticmethod
    def dbm2w(dbm:float) -> float:
        return 10**(dbm/10)/1000

    @staticmethod
    def db2w(dbm:float) -> float:
        return 10**(dbm/10)
          
    @staticmethod
    def calculate_distance(coord1, coord2):
        """
        Calculate the Euclidean distance between two points in N-dimensional space.

        Parameters:
        coord1 (iterable): An iterable of coordinates for the first point (e.g., list or tuple).
        coord2 (iterable): An iterable of coordinates for the second point.

        Returns:
        float: The Euclidean distance between the two points.
        """
        return np.linalg.norm(np.array(coord1) - np.array(coord2))