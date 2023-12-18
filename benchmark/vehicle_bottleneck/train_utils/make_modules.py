'''
@Author: WANG Maonan
@Date: 2023-10-30 23:15:18
@Description: 创建 Actor 和 Critic Module
@LastEditTime: 2023-12-18 19:57:19
'''
import torch
from torch import nn

from tensordict.nn import TensorDictModule

from torchrl.data import OneHotDiscreteTensorSpec
from torchrl.modules import (
    MultiAgentMLP,
    OneHotCategorical,
    ProbabilisticActor,
    ValueOperator,
)

class policy_module():
    def __init__(self, env, n_agents, device) -> None:
        self.n_agents = n_agents
        self.action_space = env.action_spec.shape[-1]
        self.actor_net = nn.Sequential(
            MultiAgentMLP(
                n_agent_inputs=env.observation_spec["agents", "observation"].shape[-1],
                n_agent_outputs=env.action_spec.shape[-1],
                n_agents=n_agents,
                centralised=False,
                share_params=True,
                device=device,
                depth=2,
                num_cells=256,
                activation_class=nn.Tanh,
            ),
        ) # obs = torch.zeros(10, 3, 60).to(device), actor_net(obs)

    def make_policy_module(self):
        policy_module = TensorDictModule(
            self.actor_net,
            in_keys=[("agents", "observation")],
            out_keys=[("agents", "logits")],
        )
        unbatched_action_spec = OneHotDiscreteTensorSpec(
            n=self.action_space, 
            shape=torch.Size([self.n_agents, self.action_space]), 
            dtype=torch.int64
        )
        policy = ProbabilisticActor(
            module=policy_module,
            spec=unbatched_action_spec, # CompositeSpec({("agents", "action"): env.action_spec})
            in_keys=[("agents", "logits")],
            out_keys=[("agents", "action")], # env.action_key
            distribution_class=OneHotCategorical,
            return_log_prob=True,
        )
        return policy
    
    def save_model(self, model_path):
        torch.save(self.actor_net.state_dict(), model_path)
    
    def load_model(self, model_path):
        model_dicts = torch.load(model_path)
        self.actor_net.load_state_dict(model_dicts)

class critic_module():
    def __init__(self, env, n_agents, device) -> None:
        self.critic_net = MultiAgentMLP(
            n_agent_inputs=env.observation_spec["agents", "observation"].shape[-1],
            n_agent_outputs=1,
            n_agents=n_agents,
            centralised=True, # MAPPO if True, IPPO if False
            share_params=True,
            device=device,
            depth=2,
            num_cells=256,
            activation_class=nn.Tanh,
        )

    def make_critic_module(self):
        value_module = ValueOperator(
            module=self.critic_net,
            in_keys=[("agents", "observation")],
        )
        return value_module
    
    def save_model(self, model_path):
        torch.save(self.critic_net.state_dict(), model_path)
    
    def load_model(self, model_path):
        model_dicts = torch.load(model_path)
        self.critic_net.load_state_dict(model_dicts)