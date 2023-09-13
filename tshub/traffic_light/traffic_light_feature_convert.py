'''
@Author: WANG Maonan
@Date: 2023-08-25 19:37:07
@Description: TSC 中 id 和 meaning 的转换
@LastEditTime: 2023-09-11 19:56:28
'''
class TSCKeyMeaningsConverter:
    def __init__(self):
        self.key_to_meaning = {
            17: 'last_step_mean_speed',
            18: 'last_step_vehicle_id_list',
            24: 'jam_length_vehicle',
            25: 'jam_length_meters',
            19: 'last_step_occupancy',
        }
        self.meaning_to_key = {v: k for k, v in self.key_to_meaning.items()}
    
    def get_meaning(self, key):
        return self.key_to_meaning.get(key, '')
    
    def get_key(self, meaning):
        return self.meaning_to_key.get(meaning, '')
