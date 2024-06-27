'''
@Author: WANG Maonan
@Date: 2023-08-25 16:55:36
@Description: Traffic Light Signal Action Type
@LastEditTime: 2024-06-27 19:00:42
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

    AdjustCycleDuration = 'adjust_cycle_duration'
    """Action= ``List``. Fine-tuning of each phase duration
    """

    SetPhaseDuration = 'set_phase_diration'
    """Action= ``int``. The new phase duration for the current traffic phase.
    """