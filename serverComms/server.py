"""
Author: Samara Holmes
Date: 2/6/2024

This program defines a Flask application that provides an endpoint '/solve' for solving MILP (Mixed-Integer Linear Programming) problems.
The program takes parameters 'k', 'q_k', and 'n' via a POST request to the '/solve' endpoint.
It then checks if a result for the given parameters exists in the cache folder.
If the result exists, it returns the result from the cache.
If not, it runs the MILP solver function 'solve_milp_with_optimizations' with the provided parameters on a separate thread.
Once the solver completes, it saves the result to a JSON file in the cache folder and returns the result to the client.
"""
import threading
from flask import Flask, request, jsonify, json
from serverComms.mrpcp import *
from serverComms.heuristic import *
import uuid
import requests
import os
import serverComms.json_handlers as json_handlers
from serverComms.recalculate import recalculate_paths

app = Flask(__name__)


"""
This function defines the '/solve' endpoint for solving MILP or Heuristic problems.
"""
@app.route('/solve', methods=['POST'])
def solve_endpoint():
    print("Solution request received.")
    k = request.args.get('k')
    q_k = request.args.get('q_k')
    n_a = request.args.get('n_a')
    rp = request.args.get('rp')
    l = request.args.get('l')
    d = request.args.get('d')
    mode = request.args.get('mode')

    # Generate job ID based on parameters
    job_id = f"{k}_{q_k}_{n_a}_{rp}_{l}_{d}_{mode}"

    # Get the current working directory
    current_dir = os.getcwd()

    # Define the cache folder path relative to the current directory
    cache_folder_path = os.path.join(current_dir, 'cache')

    # Check if folder with job ID exists in the cache folder
    job_folder_path = os.path.join(cache_folder_path, job_id)

    if os.path.exists(job_folder_path):
        print(f"Job folder exists: {job_folder_path}. Returning the content of the JSON file...")
        # If folder exists, read JSON file and return its content
        with open(os.path.join(job_folder_path, 'result.json'), 'r') as file:
            result = json.load(file)
        print(f"Contents of the JSON file: {result}")  # Print contents of JSON file
        return jsonify(result), 200


    print(f"Job folder does not exist: {job_folder_path}. Starting solver function with parameters k={k}, q_k={q_k}, n={n_a}, rp={rp}, l={l}, d={d}, mode={mode}...")
    # Run MILP solver function with parameters on a separate thread
    solve_thread = threading.Thread(target=run_solver, args=(k, q_k, n_a, rp, l, d, mode, job_id))
    solve_thread.start()
    result_data = {'job_id': job_id, 'params': {'k': k, 'q_k': q_k, 'n_a': n_a, 'rp': rp, 'l': l, 'd': d, 'mode': 'h'}, 'robot_node_path': 'in progress', 'robot_world_path': 'in progress', 'status': 'in progress'}
    return jsonify(result_data), 200


"""
This function runs the MILP solver function with the provided parameters.
Once the solver completes, it saves the result to a JSON file in the cache folder.
Params:
    k (int): Number of paths
    q_k (float): Maximum number of paths
    n_a (int): Number of nodes per axis
    rp (int): redundancy parameter
    l (float): 
    d (float): distance between nodes
    job_id (str): Job ID
"""
def run_solver(k, q_k, n_a, rp, l, d, mode, job_id):
    try:
        if mode == 'm':
            # Run MILP solver function with parameters
            print(f"Running MILP solver function with parameters: k={k}, q_k={q_k}, n={n_a}, rp={rp}, l={l}, d={d}, mode=m...")
            edges, world = solve_milp_with_optimizations(int(k), float(q_k), int(n_a), int(rp), float(l), float(d), job_id)
            print(f"MILP solver function completed with parameters: k={k}, q_k={q_k}, n={n_a}, rp={rp}, l={l}, d={d}, mode=m.")
            # Convert edges to a node format
            robot_node_path = [[int(edge) for edge in path] for path in edges]
            robot_world_path = world

            # Save result in a JSON file within the cache folder
            result_data = {'job_id': job_id, 'params': {'k': k, 'q_k': q_k, 'n_a': n_a, 'rp': rp, 'l': l, 'd': d, 'mode': 'h'}, 'robot_node_path': robot_node_path, 'robot_world_path': robot_world_path, 'status': 'completed'}
            json_handlers.saveResultsToCache(job_id, result_data, 'result.json') # Save the results to the cache

        elif mode == 'h':
            # Run Heuristic solver function with parameters
            print(f"Running Heuristic solver function with parameters: k={k}, q_k={q_k}, n={n_a}, rp={rp}, l={l}, d={d}, mode=h...")
            edges, world = solve_mrpcp_heuristic(int(k), float(q_k), int(n_a), int(rp), float(l), float(d), job_id)
            print(f"Heuristic solver function completed with parameters: k={k}, q_k={q_k}, n={n_a}, rp={rp}, l={l}, d={d}, mode=h.")

            # Convert edges to a node format
            robot_node_path = [[int(edge) for edge in path] for path in edges]
            robot_world_path = world

            # Save result in a JSON file within the cache folder
            result_data = {'job_id': job_id, 'params': {'k': k, 'q_k': q_k, 'n_a': n_a, 'rp': rp, 'l': l, 'd': d, 'mode': 'h'}, 'robot_node_path': robot_node_path, 'robot_world_path': robot_world_path, 'status': 'completed'}
            json_handlers.saveResultsToCache(job_id, result_data, 'result.json') # Save the results to the cache

            return result_data # Return the content of the JSON file

    except Exception as e:
        print(f"Error occurred during solving: {e}")


"""
This function defines the '/recalculate' endpoint for recalculating the paths
"""
@app.route('/recalculate', methods=['POST'])
def recalc_endpoint():
    print("Recalculation request received.")
    job_id = request.args.get('job_id')
    curr_robots_pos = request.args.get('curr_robots_pos')
    curr_robots_pos = json.loads(curr_robots_pos)
    failed_robot_id = request.args.get('failed_robot_id')

    # Run the function to recalculate the paths based on the input parameters
    return recalculate_paths(job_id, curr_robots_pos, failed_robot_id) # Return the json result of the recalculation


if __name__ == '__main__':
    print("Waiting for a request...")  # Added waiting message
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
