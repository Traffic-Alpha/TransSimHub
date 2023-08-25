'''
@Author: WANG Maonan
@Date: 2023-08-25 16:55:36
@Description: Traffic Light Signal Action Type
@LastEditTime: 2023-08-25 17:42:17
'''
import enum

class tls_action_type(enum.Enum):
    ChooseNextPhase = 'choose_next_phase'
    """
    Action= ``int``. Discrete action that can choose from all phases
    """

    NextorNot = 'next_or_not'
    """
    Action= ``int``. Discrete action from one of
    
    + 0, Change to the next phase
    + 1, Keep the current phase
    """