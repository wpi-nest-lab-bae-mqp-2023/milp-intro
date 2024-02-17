"""
Author: Samara Holmes
Date: 2/17/2024

This program defines the methods relating to recalculating the paths for robots after a failure occurs
"""

import os

import numpy as np
from flask import json
from matplotlib import pyplot as plt

from serverComms.mrpcp import saveGraphPath, convertToWorldPath

"""
This function recalculates the paths based on the current positions and where the failed robot starts back at the origin.
"""
def recalculate_paths(job_id, curr_robots_pos, failed_robot):
    # Define the cache folder path relative to the current directory
    cache_folder_path = os.path.join(os.getcwd(), 'cache')

    # Check if the job folder exists
    job_folder_path = os.path.join(cache_folder_path, job_id)
    if not os.path.exists(job_folder_path):
        print(f"Job folder does not exist: {job_folder_path}.")
        return

    # Read the result.json file to retrieve the parameters
    result_file_path = os.path.join(job_folder_path, 'result.json')
    if not os.path.exists(result_file_path):
        print(f"Result file does not exist: {result_file_path}.")
        return

    # Parse the JSON content to extract the parameters
    with open(result_file_path, 'r') as file:
        result_data = json.load(file)
        params = result_data.get('params')
        previous_robot_node_path = result_data.get('robot_node_path')

    # Use the extracted parameters for recalculation
    k = params.get('k')
    q_k = params.get('q_k')
    n_a = params.get('n_a')
    rp = params.get('rp')
    l = params.get('l')
    d = params.get('d')


    # Lets say that the we use 6_0.5_4 for the parameters (this will be the edges)
    #[[16, 17, 10, 14, 9], [16, 17, 0, 1, 3, 2], [16, 17, 4, 8, 12, 13, 5], [16, 17, 7], [16, 17, 15], [16, 17, 6, 11]]

    # Example current robot positions
    ex_robot_positions = [10, 16, 16, 16, 16, 16] # 1 index based
    ex_failed_robot_id = 1

    new_robot_paths = recalcRobotPaths(previous_robot_node_path, ex_robot_positions, rp, ex_failed_robot_id)

    # visualize the new paths and save the graph to the cache
    visualize_recalculated_paths(new_robot_paths, int(k), int(n_a), saveGraphPath(job_id, 'recalculated_paths'))

    result_data = {'job_id': job_id, 'params': {'k': k, 'q_k': q_k, 'n_a': n_a, 'rp': rp, 'l': l, 'd': d, 'mode': 'h'}, 'robot_node_path': new_robot_paths, 'robot_world_path': convertToWorldPath(new_robot_paths)}
    with open(os.path.join(job_folder_path, 'recalculated_paths.json'), 'w') as file:
        json.dump(result_data, file)
        print("Result and parameters saved to recalculated_paths.json file.")
    return result_data  # Return the content of the JSON file

"""
This function takes in the previous_node_path and the current_robot_positions and recalculates the paths based on the new positions.
The robots start where they currently are. The failed robot starts back at the depot. All the robots recalculate their paths based on the new positions
and the failed robot's new position. They need even frequency coverage to match the redundancy parameter.
"""
def recalcRobotPaths(previous_node_path, current_robot_positions, rp, failed_robot_id):
    new_node_paths = [[16, 17, 10, 14, 9], [16, 17, 0, 1, 3, 2], [16, 17, 4, 8, 12, 13, 5], [16, 17, 7], [16, 17, 15], [16, 17, 6, 11]]
    # Calculate visit counts for each node
    node_visit_counts = calculate_visit_counts(current_robot_positions, previous_node_path)

    # Start the failed robot back at the depot
    # new_node_paths[failed_robot_id] = [[0]]

    # Recalculate paths for all robots (making all considerations but prioritizing matching the redundancy parameter) TODO: Implement this


    # prioritize fuel capacity

    return new_node_paths


"""
This function calculates the visit counts for each node based on the current robot positions and the previous paths.
"""
def calculate_visit_counts(current_robot_positions, robot_previous_paths):
    # Find the largest node number
    max_node = max(max(path) for path in robot_previous_paths)

    # Count visits for each node
    node_visit_counts = {}
    for robot_position, previous_path in zip(current_robot_positions, robot_previous_paths):
        node_visit_counts[robot_position] = node_visit_counts.get(robot_position, 0) + 1
        for node in previous_path:
            node_visit_counts[node] = node_visit_counts.get(node, 0) + 1

    # Ensure that the largest node has the same number of visits as the largest node - 1
    max_visits = node_visit_counts.get(max_node, 0)
    max_minus_1_visits = node_visit_counts.get(max_node - 1, 0)
    node_visit_counts[max_node] = node_visit_counts[max_node - 1] = max(max_visits, max_minus_1_visits)

    print("Node visit counts:", node_visit_counts)
    return node_visit_counts

def visualize_recalculated_paths(paths, robots, targets, save_path=None):
    k = robots
    # Chose the number of targets in an axis
    n_a = int(targets)

    # Create a uniform (n*n, 2) numpy target grid for MAXIMUM SPEED
    targets = np.mgrid[-1:1:n_a * 1j, -1.:1:n_a * 1j]
    targets = targets.reshape(targets.shape + (1,))
    targets = np.concatenate((targets[0], targets[1]), axis=2)
    targets = targets.reshape((n_a*n_a, 2))
    print(f"{targets.shape=}")
    depots = np.array([
        [-1., -1.],
    ])

    depots = np.concatenate((depots, depots))
    depot_indices = range(len(targets), len(targets)+len(depots))

    nodes = np.concatenate((targets, depots))
    B_k = np.array([depot_indices[0]] * k)

    num_robots = len(paths)
    num_rows = (num_robots + 1) // 2  # Two plots per row
    fig, axs = plt.subplots(num_rows, 2, figsize=(10, 5 * num_rows))  # Adjust the figure size as needed

    # Flatten the axs array for easy iteration if there's more than one row
    if num_robots > 2:
        axs = axs.flatten()

    for index, path in enumerate(paths):
        ax = axs[index]

        # Plot targets and depots
        ax.scatter(targets[:, 0], targets[:, 1], c='blue', s=10, label='Targets')
        ax.scatter(depots[:, 0], depots[:, 1], c='red', s=50, label='Depots')

        # Plot path for this robot
        for i in range(len(path) - 1):
            start_node = path[i]
            end_node = path[i + 1]
            ax.plot([nodes[start_node, 0], nodes[end_node, 0]],
                    [nodes[start_node, 1], nodes[end_node, 1]],
                    color="purple", linewidth=1)
            ax.scatter(nodes[start_node, 0], nodes[start_node, 1], c="purple", s=8)
            ax.text(nodes[start_node, 0], nodes[start_node, 1], str(start_node), fontsize=8, ha='center', va='center')

        # Plot a line returning to the starting depot
        ax.plot([nodes[path[-1], 0], nodes[B_k[0], 0]],
                [nodes[path[-1], 1], nodes[B_k[0], 1]],
                color="purple", linewidth=1, linestyle="--", label='Return to Depot')

        # Plot the starting depot
        ax.text(nodes[B_k[0], 0], nodes[B_k[0], 1], str(B_k[0]), fontsize=8, ha='center', va='center')

        # Set title with cost
        ax.set_title(f"Robot #{index + 1}")
        ax.grid()
        ax.legend()

    # Hide any unused subplots
    for i in range(index + 1, num_rows * 2):
        fig.delaxes(axs[i])

    # plt.tight_layout()
    fig.suptitle(f"Paths for all robots")

    # Save the figure if save_path is provided
    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()

def worldPathToNodePath(world_path):
    node_path = []
    for i in range(len(world_path)):
        if i == 0:
            node_path.append([world_path[i]])
        else:
            node_path.append([world_path[i], world_path[i-1]])
    return node_path