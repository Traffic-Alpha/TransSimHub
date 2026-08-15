'''
@Author: WANG Maonan
@Date: 2023-09-05 17:47:24
@Description: 直接使用大语言模型进行判断
1. 明确当前的 phase id 和做动作之后的 phase id 和 phase info
@LastEditTime: 2023-09-05 22:16:43
'''
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser

from TSCAgent.tsc_agent_prompt import TSC_INSTRUCTIONS, TSC_SUMMARY
from utils.readConfig import read_config

from loguru import logger
from tshub.utils.format_dict import dict_to_str
from tshub.utils.get_abs_path import get_abs_path
from tshub.utils.init_log import set_logger

from TSCEnvironment.tsc_env import TSCEnvironment
from TSCEnvironment.tsc_env_wrapper import TSCEnvWrapper
path_convert = get_abs_path(__file__)
set_logger(path_convert('./'))

if __name__ == '__main__':
    config = read_config()
    openai_proxy = config['OPENAI_PROXY']
    openai_api_key = config['OPENAI_API_KEY']
    # 模型初始化
    chat = ChatOpenAI(
        model='gpt-3.5-turbo-16k', temperature=0.0,
        openai_api_key=openai_api_key, 
        openai_proxy=openai_proxy
    )

    # #################
    # 构造 parser 的模板
    # #################
    response_schemas = [
            ResponseSchema(
                name="now_phase_id", 
                description=f"output the id(int) of the current phase."),
            ResponseSchema(
                name="action_id", 
                description=f"output the id(int) of the decision. The comparative table is: {{ 0: 'keep_current_phase', 1: 'change_to_next_phase'}} . For example, if the traffic light wants to keep current phase, please output `0` as a int."),
            ResponseSchema(
                name="action_name", 
                description=f"output the name(str) of the decision. MUST consist with previous \"action_id\". The comparative table is: {{ 0: 'keep_current_phase', 1: 'change_to_next_phase'}}. For example, if the action_id is 1, please output 'Change_to_next_phase' as a str."),
            ResponseSchema(
                name="explanation", 
                description=f"Explain for the driver why you make such decision in 40 words.")
        ]
    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = output_parser.get_format_instructions()
    
    # ##############
    # 构造 Input 模板
    # ##############
    thinking_templete = ChatPromptTemplate.from_template(TSC_INSTRUCTIONS)
    action_templete = ChatPromptTemplate.from_template(TSC_SUMMARY)

    # #################
    # 与环境交互, 获得结果
    # #################
    tls_id = 'htddj_gsndj'
    sumo_cfg = path_convert("./single_junction/env/single_junction.sumocfg")
    tsc_scenario = TSCEnvironment(
        sumo_cfg=sumo_cfg, 
        num_seconds=1200,
        tls_ids=['htddj_gsndj'], 
        tls_action_type='next_or_not',
        use_gui=True
    )
    tsc_wrapper = TSCEnvWrapper(tsc_scenario)


    dones = False
    tsc_wrapper.reset()
    while not dones:
        action = {
            'tls': {'htddj_gsndj':0},
        }
        states, rewards, truncated, dones, infos = tsc_wrapper.step(action=action)
        phase_num = len(states[tls_id]['phase_queue_lengths'])
        phase_info = dict_to_str(states[tls_id]['phase_queue_lengths'])
        phase_id = states[tls_id]['this_phase_index']
        next_phase_id = (phase_id + 1)%phase_num

        # 1. 首先进行思考
        thinking_message = thinking_templete.format_messages(
            phase_num = phase_num, # 相位数量
            phase_info = phase_info, # 相位信息
            phase_id = phase_id, # 当前的相位
            next_phase_id = next_phase_id, # 下一个相位的信息
        )
        logger.info(f"SIM: {infos['step_time']} Prompt: \n{thinking_message[0].content}")
        custom_response = chat(thinking_message)
        logger.info(f"SIM: {infos['step_time']} Reasoning Answer: \n{dict_to_str(custom_response.content)}")

        # 2. 对思考的内容进行总结
        action_message = action_templete.format_messages(
            decision_result = custom_response.content,
            format_instructions = format_instructions
        )
        action_response = chat(action_message)
        output_dict = output_parser.parse(action_response.content)
        logger.info(f"SIM: {infos['step_time']} Action Answer: \n{dict_to_str(output_dict)}")

    tsc_wrapper.close()