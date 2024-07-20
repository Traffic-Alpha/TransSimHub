'''
@Author: WANG Maonan
@Date: 2023-10-29 23:28:22
@Description: Multi-Agent TSC Env Unsing Petting Zoo
@LastEditTime: 2024-04-24 21:00:44
'''
import functools

from typing import Dict
from pettingzoo import ParallelEnv

class TSCEnvironmentPZ(ParallelEnv):
    def __init__(self, env):
        super().__init__()
        self.env = env # TSCEnvironment
        
        # agent id == tls id
        self.agents = self.env.tls_ids
        self.possible_agents = self.env.tls_ids

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

        for _tls_id in self.agents:
            infos[_tls_id] = {f'{i}': 0 for i in range(2)}
            infos[_tls_id]['can_perform_action'] = True

        return observations, infos

    def step(self, actions:Dict[str, int]):
        """Step the environment.
        """
        self.num_moves += 1
        observations, rewards, terminations, truncations, infos = self.env.step(actions)
        return observations, rewards, terminations, truncations, infos