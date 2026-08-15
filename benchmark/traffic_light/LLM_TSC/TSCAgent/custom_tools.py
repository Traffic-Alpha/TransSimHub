'''
@Author: WANG Maonan
@Date: 2023-09-06 14:57:39
@Description: Agent Tools
1. 获得所有可行的动作 (phase index list)
2. 输入场景和动作, 输出预测的下一个时刻的场景
3. 对整个场景进行评估（可以是前后两个场景的性能比较）
@LastEditTime: 2023-09-07 11:28:36
'''
from typing import Any
from tshub.utils.format_dict import dict_to_str

def prompts(name, description):
    def decorator(func) -> Any:
        func.name = name
        func.description = description
        return func

    return decorator


class GetAvailableActions:
    def __init__(self, env: Any, action_type='next_or_not') -> None:
        self.env = env
        self.action_type = action_type

    @prompts(name='Get Available Actions',
             description="""Useful before you make decisions, this tool let you know what are your available actions in this situation step. The input is a string, representing the id of the traffic signal light you want to control. DONNOT input multiple traffic signal light ids once.""")
    def inference(self, tls_id: str) -> str:
        outputPrefix = 'You can ONLY use one of the following actions: \n'
        available_actions = self.env.get_available_actions()
        if tls_id not in available_actions:
            return 'Not a valid traffic signal light id! Check the traffic signal light id first.'

        for action in available_actions[tls_id]:
            outputPrefix += f'- Phase {action} to be green: Make Phase {action} green light and the other phases red lights.\n'
            
        outputPrefix += """\nTo check decision safety and efficiency you should follow steps:"""
        for action_index, action in enumerate(available_actions[tls_id]):
            outputPrefix += f"Step {action_index}: Predict the queue length of each phase when change Phase {action} to be green light."
        
        return outputPrefix


class PredictQueueLength:
    def __init__(self, env: Any) -> None:
        self.env = env

    @prompts(name='Predict Queue Length',
            description="""Useful when you want to predict the queue length for the action you want to execute. The input is a str, representing the index of the phase that you decide to change to the green light. For example, the index for Phase 1 is 1.""")
    def inference(self, phase_id: int) -> str:
        predict_queue_length = self.env.predict_future_scene(phase_id)
        predict_state_str = f'If the Phase {phase_id} becomes green light, the queue length of each phase may become {dict_to_str(predict_queue_length)}.\n'
        predict_state_str += """You need to also check other available actions you mentioned above until all of them have beem checked."""
        return predict_state_str
    