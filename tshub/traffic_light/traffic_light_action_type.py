'''
@Author: WANG Maonan
@Date: 2023-08-25 16:55:36
@Description: Traffic Light Signal Action Type
@LastEditTime: 2024-04-24 20:06:18
'''
import enum

class tls_action_type(enum.Enum):
    ChooseNextPhase = 'choose_next_phase'
    """
    Action= ``int``. Discrete action that can choose from all phases
    """

    ChooseNextPhaseSyn = 'choose_next_phase_syn'
    """
    Action= ``int``. Discrete action that can choose from all phases (Synchronize)
    """

    NextorNot = 'next_or_not'
    """
    Action= ``int``. Discrete action from one of
    
    + 0, Change to the next phase
    + 1, Keep the current phase
    """