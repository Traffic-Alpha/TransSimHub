'''
@Author: WANG Maonan
@Date: 2023-11-01 23:44:45
@Description: Plot reward curve according to the log file
LastEditTime: 2024-09-23 17:22:56
'''
import pandas as pd
import matplotlib.pyplot as plt
from typing import List

def plot_reward_curve(file_paths:List[str], output_file:str, window_size:int=10, fill_outliers:bool=True) -> None:
    """将 log 文件绘制为 reward 曲线

    Args:
        file_paths (List[str]): log 文件的路径, 这里可以输入多个 log 文件
        output_file (str): 图片保存的路径
        window_size (int): 滑动平均的窗口大小
        fill_outliers (bool): 是否对异常值进行处理, 删除异常值
    """
    rewards = []

    for file_path in file_paths:
        df = pd.read_csv(file_path, comment='#')
        rewards.append(df['r'])

    rewards = pd.concat(rewards, axis=1, ignore_index=True)
    
    # Remove outliers using the Interquartile Range (IQR)
    if fill_outliers:
        # Fill outliers for each column using the median of that column
        for i in range(rewards.shape[1]):
            Q1 = rewards.iloc[:, i].quantile(0.25)
            Q3 = rewards.iloc[:, i].quantile(0.75)
            IQR = Q3 - Q1
            outlier_condition = (rewards.iloc[:, i] < (Q1 - 1.5 * IQR)) | (rewards.iloc[:, i] > (Q3 + 1.5 * IQR))
            rewards.iloc[outlier_condition, i] = rewards.iloc[:, i].median()

    # Apply a rolling window for the rewards
    rewards = rewards.rolling(window_size).mean().dropna()

    mean_rewards = rewards.mean(axis=1).reset_index(drop=True)
    Q1_rewards = rewards.quantile(0.25, axis=1).reset_index(drop=True)
    Q3_rewards = rewards.quantile(0.75, axis=1).reset_index(drop=True)

    plt.figure(figsize=(10, 6))
    plt.plot(mean_rewards, label='Mean Reward')
    plt.fill_between(range(len(mean_rewards)), Q1_rewards, Q3_rewards, color='b', alpha=0.2)
    plt.title('Reward Curve with Standard Deviation')
    plt.xlabel('Episode')
    plt.ylabel('Reward')
    plt.legend()
    plt.grid(True)
    plt.savefig(output_file)  # Save the figure to a file
    plt.close()  # Close the figure


def plot_multi_reward_curves(dirs_and_labels, output_file, window_size:int=3):
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
        rewards = rewards.rolling(window_size).mean().dropna()
        mean_rewards = rewards.mean(axis=1).reset_index(drop=True)
        Q1_rewards = rewards.quantile(0.25, axis=1).reset_index(drop=True)
        Q3_rewards = rewards.quantile(0.75, axis=1).reset_index(drop=True)

        # Plot the mean reward and fill between the mean +/- standard deviation
        plt.plot(mean_rewards, label=label)
        plt.fill_between(range(len(mean_rewards)), Q1_rewards, Q3_rewards, alpha=0.2)

    # Add title, labels, legend, and grid
    plt.title('Reward Curve with Standard Deviation')
    plt.xlabel('Episode')
    plt.ylabel('Reward')
    plt.legend()
    plt.grid(True)

    plt.savefig(output_file)  # Save the figure to a file
    plt.close()  # Close the figure
