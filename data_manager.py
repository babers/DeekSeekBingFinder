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
        
    def add_search(self, term, rewards=None):  # added rewards=None by baber
        if term not in self.searched_terms:
            self.searched_terms.add(term)
            # self.rewards += 1  # Microsoft Rewards typically gives 3-5 points per search
         
            if rewards is not None:
                self.rewards = rewards                       
            self.search_history.append({
                'timestamp': datetime.now(),
                'count': len(self.searched_terms),
                'rewards': self.rewards
            })
            
    def get_progress_data(self):
        return [(entry['timestamp'], entry['count']) for entry in self.search_history]
    
    def get_current_counts(self):
        return {
            'total': len(self.searched_terms),
            'rewards': self.rewards
        }