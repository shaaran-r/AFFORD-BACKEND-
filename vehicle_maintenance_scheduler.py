import requests

def solve_knapsack(tasks, max_hours):
    """
    Solves the 0/1 Knapsack problem to maximize total impact score
    within the available mechanic-hours.
    """
    n = len(tasks)
    # dp[i][j] will store the maximum impact score using the first i tasks
    # with a total duration not exceeding j hours.
    dp = [[0 for _ in range(max_hours + 1)] for _ in range(n + 1)]

    for i in range(1, n + 1):
        task_id, duration, impact = tasks[i-1]
        for j in range(max_hours + 1):
            if duration <= j:
                # Maximize impact: either include the current task or don't
                dp[i][j] = max(dp[i-1][j], dp[i-1][j-duration] + impact)
            else:
                # Cannot include the current task
                dp[i][j] = dp[i-1][j]

    # Backtrack to find the selected tasks
    selected_tasks = []
    j = max_hours
    for i in range(n, 0, -1):
        if dp[i][j] != dp[i-1][j]:
            selected_tasks.append(tasks[i-1])
            j -= tasks[i-1][1]

    return selected_tasks, dp[n][max_hours]

def get_depots():
    """Fetches depot data from the API."""
    try:
        response = requests.get("http://4.224.186.213/evaluation-service/depots")
        response.raise_for_status()
        return response.json().get("depots", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching depots: {e}")
        return []

def get_vehicles():
    """Fetches vehicle/task data from the API."""
    try:
        response = requests.get("http://4.224.186.213/evaluation-service/vehicles")
        response.raise_for_status()
        return response.json().get("vehicles", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching vehicles: {e}")
        return []

def main():
    # Since the APIs are protected (401 Unauthorized), we use mock data
    # based on the examples provided in the assessment document.
    
    depots = [
        {"ID": 1, "MechanicHours": 60},
        {"ID": 2, "MechanicHours": 135},
        {"ID": 3, "MechanicHours": 188},
        {"ID": 4, "MechanicHours": 97},
        {"ID": 5, "MechanicHours": 164}
    ]
    
    vehicles = [
        {"TaskID": "v1", "Duration": 1, "Impact": 5},
        {"TaskID": "v2", "Duration": 6, "Impact": 2},
        {"TaskID": "v3", "Duration": 1, "Impact": 3},
        {"TaskID": "v4", "Duration": 5, "Impact": 5},
        {"TaskID": "v5", "Duration": 7, "Impact": 3},
        {"TaskID": "v6", "Duration": 6, "Impact": 3},
        {"TaskID": "v7", "Duration": 5, "Impact": 1},
        {"TaskID": "v8", "Duration": 5, "Impact": 9},
        {"TaskID": "v9", "Duration": 6, "Impact": 10},
        {"TaskID": "v10", "Duration": 6, "Impact": 6},
        {"TaskID": "v11", "Duration": 6, "Impact": 1},
        {"TaskID": "v12", "Duration": 1, "Impact": 5},
        {"TaskID": "v13", "Duration": 6, "Impact": 9},
        {"TaskID": "v14", "Duration": 2, "Impact": 5},
        {"TaskID": "v15", "Duration": 5, "Impact": 7},
        {"TaskID": "v16", "Duration": 1, "Impact": 1},
        {"TaskID": "v17", "Duration": 8, "Impact": 7},
        {"TaskID": "v18", "Duration": 2, "Impact": 9},
        {"TaskID": "v19", "Duration": 2, "Impact": 3},
        {"TaskID": "v20", "Duration": 2, "Impact": 5},
        {"TaskID": "v21", "Duration": 3, "Impact": 10},
        {"TaskID": "v22", "Duration": 5, "Impact": 5},
        {"TaskID": "v23", "Duration": 8, "Impact": 8},
        {"TaskID": "v24", "Duration": 8, "Impact": 5},
        {"TaskID": "v25", "Duration": 7, "Impact": 10},
        {"TaskID": "v26", "Duration": 1, "Impact": 8},
        {"TaskID": "v27", "Duration": 5, "Impact": 8},
        {"TaskID": "v28", "Duration": 8, "Impact": 8},
        {"TaskID": "v29", "Duration": 7, "Impact": 8}
    ]

    # Prepare tasks list: [(TaskID, Duration, Impact), ...]
    tasks = [(v['TaskID'], v['Duration'], v['Impact']) for v in vehicles]

    for depot in depots:
        depot_id = depot['ID']
        max_hours = depot['MechanicHours']
        
        selected_tasks, total_impact = solve_knapsack(tasks, max_hours)
        
        print(f"--- Depot ID: {depot_id} (Max Hours: {max_hours}) ---")
        print(f"Total Impact Score: {total_impact}")
        print("Selected Tasks:")
        for task_id, duration, impact in selected_tasks:
            print(f"  - Task ID: {task_id}, Duration: {duration}, Impact: {impact}")
        print("\n")

if __name__ == "__main__":
    main()
