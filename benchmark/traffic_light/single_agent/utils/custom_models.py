'''
@Author: WANG Maonan
@Date: 2023-09-08 18:34:24
@Description: Custom Model
@LastEditTime: 2023-09-08 18:44:03
'''
import gym
import torch.nn as nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

class CustomModel(BaseFeaturesExtractor):
    def __init__(self, observation_space: gym.Space, features_dim: int = 16):
        """特征提取网络
        """
        super().__init__(observation_space, features_dim)
        net_shape = observation_space.shape

        self.fc = nn.Sequential(
            nn.Linear(net_shape[0], 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, features_dim)
        )

    def forward(self, observations):
        return self.fc(observations)