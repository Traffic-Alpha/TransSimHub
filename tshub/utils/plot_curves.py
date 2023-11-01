'''
@Author: WANG Maonan
@Date: 2023-11-01 23:44:45
@Description: Plot reward curve according to the log file
@LastEditTime: 2023-11-01 23:44:47
'''
import pandas as pd
import matplotlib.pyplot as plt

def plot_reward_curve(file_paths):
    rewards = []

    for file_path in file_paths:
        df = pd.read_csv(file_path, comment='#')
        rewards.append(df['r'])

    rewards = pd.concat(rewards, axis=1)
    mean_rewards = rewards.mean(axis=1)
    std_rewards = rewards.std(axis=1)

    plt.figure(figsize=(10, 6))
    plt.plot(mean_rewards, label='Mean Reward')
    plt.fill_between(range(len(mean_rewards)), mean_rewards - std_rewards, mean_rewards + std_rewards, color='b', alpha=0.2)
    plt.title('Reward Curve with Standard Deviation')
    plt.xlabel('Episode')
    plt.ylabel('Reward')
    plt.legend()
    plt.grid(True)
    plt.show()