# data_manager.py
# At the top of each module
print(f"Loading {__name__} module") 

import json
import time
from datetime import datetime
import browser_controller 


class DataManager:
    def __init__(self):
        self.searched_terms = set()
        self.start_time = time.time()
        self.search_history = []
        self.rewards = 0
        self.total_searches = 0  # Track all searches, including duplicates
        
    def add_search(self, term, rewards=None):
        self.total_searches += 1
        if term not in self.searched_terms:
            self.searched_terms.add(term)
        if rewards is not None:
            self.rewards = rewards
        self.search_history.append({
            'timestamp': datetime.now(),
            'count': self.total_searches,
            'rewards': self.rewards
        })
            
    def get_progress_data(self):
        return [(entry['timestamp'], entry['count']) for entry in self.search_history]
    
    def get_current_counts(self):
        return {
            'total': self.total_searches,
            'rewards': self.rewards
        }