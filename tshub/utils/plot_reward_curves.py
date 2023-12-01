'''
@Author: WANG Maonan
@Date: 2023-11-01 23:44:45
@Description: Plot reward curve according to the log file
@LastEditTime: 2023-11-28 17:44:48
'''
import os
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


def plot_multi_reward_curves(dirs_and_labels):
    """
    Plot the reward curve for all files in multiple directories.

    Args:
        dirs_and_labels (dict): A dictionary where the keys are labels and the values are directory paths.

    Returns:
        None
    """
    plt.figure(figsize=(10, 6))

    # Loop over the dictionary
    for label, files in dirs_and_labels.items():
        rewards = []

        # Loop over all files in the directory
        for file_path in files:
                # Read the file
                df = pd.read_csv(file_path, comment='#')
                rewards.append(df['r'])

        # Concatenate all rewards and calculate the mean and standard deviation
        rewards = pd.concat(rewards, axis=1)
        mean_rewards = rewards.mean(axis=1)
        std_rewards = rewards.std(axis=1)

        # Plot the mean reward and fill between the mean +/- standard deviation
        plt.plot(mean_rewards, label=label)
        plt.fill_between(range(len(mean_rewards)), mean_rewards - std_rewards, mean_rewards + std_rewards, alpha=0.2)

    # Add title, labels, legend, and grid
    plt.title('Reward Curve with Standard Deviation')
    plt.xlabel('Episode')
    plt.ylabel('Reward')
    plt.legend()
    plt.grid(True)

    # Show the plot
    plt.show()
