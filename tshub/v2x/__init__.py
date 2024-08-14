'''
@Author: WANG Maonan
@Date: 2024-08-09 11:26:23
@Description: Channel Models
@LastEditTime: 2024-08-10 20:22:07
'''
from .v2x_channel import V2XChannel
from .v2i_channel import V2IChannel
from .v2v_channel import V2VChannel

from .v2x_utils.snr_to_packetloss import calculate_outage_probability