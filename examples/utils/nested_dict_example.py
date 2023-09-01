'''
@Author: WANG Maonan
@Date: 2023-08-24 16:18:38
@Description: 
@LastEditTime: 2023-08-24 16:18:39
'''
from collections import defaultdict
from tshub.utils.nested_dict_conversion import create_nested_defaultdict, defaultdict2dict

# 测试 create_nested_defaultdict 函数
nested_dict = create_nested_defaultdict()
nested_dict['a']['b']['c'] = 123
print(nested_dict['a']['b']['c'])  # 输出: 123

# 测试 defaultdict2dict 函数
nested_dict = create_nested_defaultdict()
nested_dict['a']['b']['c'] = 123

regular_dict = defaultdict2dict(nested_dict)
print(regular_dict)  # 输出: {'a': {'b': {'c': 123}}}
