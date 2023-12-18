'''
@Author: WANG Maonan
@Date: 2023-12-16 22:48:21
@Description: Bottleneck Environment for Petting Zoo
@LastEditTime: 2023-12-18 19:57:00
'''
import functools

from typing import Dict
from pettingzoo import ParallelEnv

class VehEnvironmentPZ(ParallelEnv):
    def __init__(self, env):
        super().__init__()
        self.env = env # VehEnvWrapper
        
        self.agents = self.env.ego_ids
        self.possible_agents = self.env.ego_ids

        # spaces
        self.action_spaces = self.env.action_space
        self.observation_spaces = self.env.observation_space
    
    @functools.lru_cache(maxsize=None)
    def observation_space(self, agent):
        """Return the observation space for the agent.
        """
        return self.observation_spaces[agent]
    
    @functools.lru_cache(maxsize=None)
    def action_space(self, agent):
        """Return the action space for the agent.
        """
        return self.action_spaces[agent]
    
    def observe(self, agent):
        """Return the observation for the agent.
        """
        obs = self.observations[agent].copy()
        return obs
    
    def close(self):
        """Close the environment and stop the SUMO simulation.
        """
        self.env.close()

    def reset(self, seed=None, options=None):
        """Reset the environment
        """
        observations, infos = self.env.reset()
        self.agents = self.possible_agents[:]
        self.num_moves = 0
        self.state = observations

        for _ego_id in self.agents:
            infos[_ego_id] = {'termination': False}

        return observations, infos

    def step(self, actions:Dict[str, int]):
        """Step the environment.
        """
        self.num_moves += 1
        observations, rewards, terminations, truncations, infos = self.env.step(actions)
        self.agents = list(observations.keys()) # 表示存活的 agent
        return observations, rewards, terminations, truncations, infos        