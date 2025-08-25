# data_manager.py
print(f"Loading {__name__} module")

from datetime import datetime


class DataManager:
    def __init__(self):
        self.search_history = []  # List of (search_index, rewards_points)
        self.rewards_points = 0
        self.total_searches = 0
        self.rewards_completed = False
        self.loop_completed = False

    def reset(self):
        self.rewards_points = 0
        self.rewards_completed = False
        self.loop_completed = False

    def update_rewards(self, points):
        self.rewards_points = points
        if self.rewards_points >= 90:
            self.rewards_completed = True
            print("DEBUG: Rewards marked complete (>=90 points)")

    def mark_loop_complete(self):
        self.loop_completed = True
        print("DEBUG: Loop marked complete")

    def mark_rewards_complete(self):
        self.rewards_completed = True
        print("DEBUG: Rewards marked complete (manual call)")

    def get_current_counts(self):
        """
        Returns a dictionary with current total searches and rewards points.
        """
        return {
            'total': self.total_searches,
            'rewards': self.rewards_points
        }

    def add_search(self, term, rewards):
        self.total_searches += 1
        self.search_history.append((self.total_searches, rewards))