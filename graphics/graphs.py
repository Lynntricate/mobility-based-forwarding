import pandas as pd
import numpy as np
import math
import re
import os

import matplotlib.pyplot as plt

results_folder = 'results'
run = 'test_run_3'
config_file_name = 'config.py'
result_mbf_filename = 'results_mbf.csv'
result_prophet_filename = 'results_prophet.csv'
result_random_filename = 'results_random.csv'


def take_any(x):
    return x.iloc[0]

def group_by_column_keep_timestamp(group_column, dataframe):
    return dataframe.groupby(group_column).agg({
        'success_count': 'mean',
        'total_sent': 'mean',
        'avg_hop_count': 'mean',
        'avg_delay': 'mean',
        'end_time': take_any
    })


def get_config(timestamp, config_item):
    path = os.path.join('..', results_folder, run, timestamp, config_file_name)

    with open(path, 'r') as file:
        file_contents = file.read()
    pattern = rf'{config_item}\s*=\s*([0-9.]+)'
    match = re.search(pattern, file_contents)
    if match:
        return float(match.group(1))
    else:
        raise Exception(f'{config_item} not found in {results_folder}/{run}/{timestamp}/{config_file_name}')

if __name__ == '__main__':
    # print(get_config('1719426572', 'h_factor'))

    result_path_mbf = os.path.join('..', results_folder, run, result_mbf_filename)
    result_path_prophet = os.path.join('..', results_folder, run, result_prophet_filename)
    result_path_random = os.path.join('..', results_folder, run, result_random_filename)


    df_mbf = pd.read_csv(result_path_mbf, header=0)
    df_prophet = pd.read_csv(result_path_prophet, header=0)
    df_random = pd.read_csv(result_path_random, header=0)

    df_mbf = group_by_column_keep_timestamp('config_h_factor', df_mbf)
    df_prophet = group_by_column_keep_timestamp('config_h_factor', df_prophet)
    df_random = group_by_column_keep_timestamp('config_h_factor', df_random)

    timestamps_mbf = df_mbf['end_time']
    timestamps_prophet = df_prophet['end_time']
    timestamps_random = df_random['end_time']

    x_axis = [get_config(str(timestamp), 'h_factor') for timestamp in timestamps_mbf]  # Create shared x axis

    print(x_axis)



    df_mbf['success_mbf_frac'] = df_mbf['success_count'] / df_mbf['total_sent']
    df_prophet['success_prophet_frac'] = df_prophet['success_count'] / df_prophet['total_sent']
    df_random['success_random_frac'] = df_random['success_count'] / df_random['total_sent']

    success_mbf = df_mbf['success_mbf_frac'].tolist()
    success_prophet = df_prophet['success_prophet_frac'].tolist()
    success_random = df_random['success_random_frac'].tolist()

    hops_mbf = df_mbf['avg_hop_count'].tolist()
    hops_prophet = df_prophet['avg_hop_count'].tolist()
    hops_random = df_random['avg_hop_count'].tolist()


    # Create figure and axes
    fig, ax1 = plt.subplots(figsize=(10, 10))

    # Plot ping_from values on the first y-axis
    ax1.plot(x_axis, success_mbf, label='Success MBF', marker='o', linestyle='-', color='blue')
    ax1.plot(x_axis, success_prophet, label='Success Prophet', marker='x', linestyle='--', color='red')
    ax1.plot(x_axis, success_random, label='Success Random', marker='+', linestyle='-', color='green')
    ax1.set_xlabel('h_factor')
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.legend(loc='upper right')
    #
    # Create a second y-axis for number of hops
    # ax2 = ax1.twinx()
    # ax2.plot(x_axis, hops_mbf, label='Average Hops MBF', marker='o', linestyle='-', color='m')
    # ax2.plot(x_axis, hops_prophet, label='Average Hops Prophet', marker='x', linestyle='--', color='red')
    # ax2.plot(x_axis, hops_random, label='Average Hops Random', marker='^', linestyle='-.', color='orange')
    # ax2.set_ylabel('Average number of hops', color='m')
    # ax2.tick_params(axis='y', labelcolor='m')
    # ax2.legend(loc='center right')
    # #
    #
    # # Title and grid
    # plt.title(title)
    # plt.grid(True)
    plt.title('Delivery success rate MBF vs Prophet')

    plt.show()
