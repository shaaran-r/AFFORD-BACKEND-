import requests
from datetime import datetime

def calculate_priority_score(notification):
    """
    Calculates the priority score based on weight and recency.
    Weights: Placement (3) > Result (2) > Event (1)
    Recency: More recent notifications get a higher score.
    """
    type_weights = {
        "Placement": 3,
        "Result": 2,
        "Event": 1
    }
    
    weight = type_weights.get(notification['Type'], 0)
    
    # Calculate recency score (using timestamp)
    # Convert timestamp to unix seconds for comparison
    timestamp = datetime.strptime(notification['Timestamp'], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    seconds_since = (now - timestamp).total_seconds()
    
    # Recency score decreases as time passes. 
    # Using a simple inverse or decaying function.
    recency_score = 1 / (1 + seconds_since / 3600) # Decay over hours
    
    return (weight * 0.7) + (recency_score * 0.3) # Weighted combination

def get_notifications():
    """Fetches notifications from the API."""
    try:
        response = requests.get("http://4.224.186.213/evaluation-service/notifications")
        response.raise_for_status()
        return response.json().get("notifications", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching notifications: {e}")
        return []

def get_priority_notifications(notifications, n=10):
    """
    Returns the top 'n' most important unread notifications.
    """
    # In a real scenario, we'd filter for unread notifications here.
    # Assuming all fetched are unread or filtering is handled by API.
    
    scored_notifications = []
    for note in notifications:
        score = calculate_priority_score(note)
        scored_notifications.append((score, note))
    
    # Sort by score in descending order
    scored_notifications.sort(key=lambda x: x[0], reverse=True)
    
    return [note for score, note in scored_notifications[:n]]

def main():
    # Since API is protected, using mock data from the assessment document
    notifications = [
        {"ID": "d146095a", "Type": "Result", "Message": "mid-sem", "Timestamp": "2026-04-22 17:51:30"},
        {"ID": "b283218f", "Type": "Placement", "Message": "CSX Corporation hiring", "Timestamp": "2026-04-22 17:51:18"},
        {"ID": "81589ada", "Type": "Event", "Message": "farewell", "Timestamp": "2026-04-22 17:51:06"},
        {"ID": "0005513a", "Type": "Result", "Message": "mid-sem", "Timestamp": "2026-04-22 17:50:54"},
        {"ID": "ea836726", "Type": "Result", "Message": "project-review", "Timestamp": "2026-04-22 17:50:42"},
        {"ID": "003cb427", "Type": "Result", "Message": "external", "Timestamp": "2026-04-22 17:50:30"},
        {"ID": "1cfce5ee", "Type": "Event", "Message": "tech-fest", "Timestamp": "2026-04-22 17:50:06"},
        {"ID": "cf2885a6", "Type": "Result", "Message": "project-review", "Timestamp": "2026-04-22 17:49:54"},
        {"ID": "8a7412bd", "Type": "Placement", "Message": "Advanced Micro Devices Inc. hiring", "Timestamp": "2026-04-22 17:49:42"}
    ]
    
    n = 5 # User's choice
    priority_notes = get_priority_notifications(notifications, n)
    
    print(f"--- Top {n} Priority Notifications ---")
    for note in priority_notes:
        print(f"[{note['Type']}] {note['Message']} ({note['Timestamp']})")

if __name__ == "__main__":
    main()
