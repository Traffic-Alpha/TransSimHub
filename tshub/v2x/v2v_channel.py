'''
@Author: WANG Maonan
@Date: 2024-08-09 11:40:50
@Description: V2V Channel Model
@LastEditTime: 2024-08-14 20:07:00
'''
import math
import numpy as np
from loguru import logger
from typing import List, Tuple

from .v2x_channel import V2XChannel

class V2VChannel(V2XChannel):
    """
    V2V (Vehicle-to-Vehicle) channel model.
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(
            h_bs=1.5, h_ms=1.5,
            decorrelation_distance=10, shadow_std=3, **kwargs
        )
        self.v2v_shadowing = np.random.normal(0, self.shadow_std)
        self.distance = None

    def get_channels_with_fastfading(
            self, 
            # 车辆 A 的位置
            previous_position_obj_A: List[float], 
            current_position_obj_A: List[float],
            # 车辆 B 的位置
            previous_position_obj_B: List[float], 
            current_position_obj_B: List[float],
        )->float:
        free_path_loss = self._get_path_loss(current_position_obj_A, current_position_obj_B)

        shadowing = self._get_shadowing(
            previous_position_obj_A, current_position_obj_A,
            previous_position_obj_B, current_position_obj_B
        )
        noise = np.random.normal(0, 1)
        channels_with_fastfading = (free_path_loss + shadowing + noise)
        
        return channels_with_fastfading
    
    def get_received_power(
            self, 
            # 车辆 A 的位置
            previous_position_obj_A: List[float], 
            current_position_obj_A: List[float],
            # 车辆 B 的位置
            previous_position_obj_B: List[float], 
            current_position_obj_B: List[float],
            is_ms_transmit:bool = True, # 是否是 ms 作为发送, V2X
            is_ms_received:bool = True # 是否是 ms 作为接收, X2V
        )->float:
        channels_with_fastfading = self.get_channels_with_fastfading(
            previous_position_obj_A, current_position_obj_A,
            previous_position_obj_B, current_position_obj_B
        )

        noise_figure = self.noise_figure_ms if is_ms_received else self.noise_figure_bs
        if is_ms_transmit: # ms->bs/ms, 所以使用 power_ms
            received_power = self.power_ms - channels_with_fastfading - noise_figure
        else: # bs -> ms
            received_power = self.power_bs - channels_with_fastfading - noise_figure
        
        return received_power
    
    def get_snr(
            self, 
            # 车辆 A 的位置
            previous_position_obj_A: List[float], 
            current_position_obj_A: List[float],
            # 车辆 B 的位置
            previous_position_obj_B: List[float], 
            current_position_obj_B: List[float],
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
            previous_position_obj_A, current_position_obj_A,
            previous_position_obj_B, current_position_obj_B,
            is_ms_transmit=is_ms_transmit,
            is_ms_received=is_ms_received,
        )

        noise_power_dbm = self.sig2_dB_ms if is_ms_transmit else self.sig2_dB_bs
        v2v_snr = 10*np.log10(V2XChannel.dbm2w(received_power)/V2XChannel.dbm2w(noise_power_dbm))
        
        return v2v_snr
    
    def _get_path_loss(self, position_A:List[float], position_B:List[float]):
        """
        Calculate the path loss between two positions.

        The path loss PL(d) in dB is calculated based on the distance d between the transmitter and receiver:
        For LOS (Line of Sight):
            1. PL(d) = 22.7 * log10(d) + 41 + 20 * log10(fc/5) for d > 3m
            2. PL(d) = 22.7 * log10(3) + 41 + 20 * log10(fc/5) for d <= 3m, 小于 3 的时候距离就是 3

        For NLOS (Non-Line of Sight):
            - PL(d) = PL_Los(d_a) + 20 - 12.5 * n_j + 10 * n_j * log10(d_b) + 3 * log10(fc/5)
            - where n_j is the environment factor, d_a and d_b are the distances.
        """
        # Calculate Euclidean distance
        self.distance = math.hypot(
            position_A[0] - position_B[0], 
            position_A[1] - position_B[1]
        ) + 0.001 # 计算两个点的距离

        # Constants for WINNER II Model (example values, should be adjusted based on specific scenario)
        light_speed = 3e8  # Speed of light in vacuum (m/s)
        n_los = 3.0  # Path loss exponent for NLOS
        n_los_factor = 20  # Additional NLOS factor in dB

        def PL_Los():
            # Free space path loss (FSPL) formula
            fspl = 20*math.log10(self.distance) + 20*math.log10(self.fc*1e9) + 20 * math.log10(4*math.pi/light_speed) - 2*self.antrenna_gain_bs
            return fspl

        def PL_NLos():
            # NLOS path loss, typically higher than LOS
            pl_nlos = PL_Los() + n_los_factor + 10*n_los*math.log10(self.distance)
            return pl_nlos

        # Example condition to determine if the path is LOS or NLOS
        # This should be replaced with a real condition based on environmental data
        if self.distance < 100:  # Assuming LOS if distance is less than 100 meters
            PL = PL_Los()
        else:
            PL = PL_NLos()

        return PL

    def _get_shadowing(
            self, 
            previous_position_obj_A: Tuple[float, float], 
            current_position_obj_A: Tuple[float, float],
            previous_position_obj_B: Tuple[float, float], 
            current_position_obj_B: Tuple[float, float],
        ) -> float:
        """Calculate the shadowing effect for multiple vehicles based on the change in distance.
        """
        # delta_distance 是两个时刻之间的距离, \Delta d = | d(P_VehA, P_VehB) - d(P_VehA, P_P_VehB)|
        delta_distance = abs(
            V2XChannel.calculate_distance(previous_position_obj_A, previous_position_obj_B) - \
            V2XChannel.calculate_distance(current_position_obj_A, current_position_obj_B)
        )

        shadowing_rho = np.exp(-1*(delta_distance / self.decorrelation_distance))
        shadowing = shadowing_rho*self.v2v_shadowing + \
            np.sqrt(1 - shadowing_rho**2)*np.random.normal(0, self.shadow_std)
        
        return shadowing