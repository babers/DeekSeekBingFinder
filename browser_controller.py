# browser_controller.py

# At the top of each module
print(f"Loading {__name__} module") 

# browser_controller.py
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import random
import time
import threading
from datetime import datetime
from daily_topics import DailyTopics
import re
import traceback

class BrowserController:
    def __init__(self, data_manager, gui=None):
        self.data_manager = data_manager
        self.gui = gui  # Reference to GUI for updating topic
        self.running = False
        self.driver = None
             
        self.topics_provider = DailyTopics()  # <-- NEW TOPICS HANDLER INSTANCE
        self.last_points = None 
        import threading
        self.stop_event = threading.Event()
        
    
    def _get_current_day_topics(self):
        """Get today's search topics based on current day of week"""
        day_name = datetime.now().strftime('%A')
        return self.daily_topics.get(day_name, [
            'General technology', 'Science news',
            'World current affairs', 'Educational content'
        ])   
        
    def _setup_driver(self):
        # Update path to your Edge WebDriver
        edge_driver_path = 'msedgedriver.exe'  # Replace with actual path
        edge_service = Service(executable_path=edge_driver_path)  # Updated syntax
        self.driver = webdriver.Edge(service=edge_service)

    
    def get_current_points(self):
        """Public method to fetch current reward points"""
        try:
            if not self.driver:
                self._setup_driver()
            self.driver.get("https://rewards.bing.com/pointsbreakdown")
            
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # wait = WebDriverWait(self.driver, 10)   
            # points_element = wait.until(
            #     EC.visibility_of_element_located((By.CSS_SELECTOR, '[class="pointsDetail c-subheading-3 ng-binding"]'))
            # )
            
            #<p ng-bind-html="$ctrl.pointProgressText" class="pointsDetail c-subheading-3 ng-binding"><b>63</b> / 90</p>
            wait = WebDriverWait(self.driver, 15)  
            points_element = wait.until(
               EC.visibility_of_element_located((By.CLASS_NAME, "pointsDetail"))
)
            # time.sleep(3)
            # points_element = self.driver.find_element(
            #     By.CSS_SELECTOR,
            #     '[class="pointsDetail c-subheading-3 ng-binding"]'
            # )
            
            
            
            points_text = points_element.text
            match = re.search(r'\d+', points_text)
            if match:
                points = int(match.group())
                print("************  PC Search Points Balance **************** :", points)
                self.last_points = points
                return points
            else:
                print("Could not find points in text:", points_text)
                # Always return an integer (last_points if set, else 0)
                return self.last_points if self.last_points is not None else 0
        except Exception as e:
            print(f"Error retrieving points: {type(e).__name__}: {e}")
            traceback.print_exc()
            # Optionally, take a screenshot for debugging:
            if self.driver:
                self.driver.save_screenshot("error_screenshot.png")
            return self.last_points if self.last_points is not None else 0

            
    def _generate_search_term(self):
        return f"{random.choice(self.search_terms)}"
            
        
    def _perform_search(self, term):
        if not self.driver:
            self._setup_driver()
        
        self.driver.get('https://www.bing.com/news/?form=ml11z9&crea=ml11z9&wt.mc_id=ml11z9&rnoreward=1&rnoreward=1')
        search_box = self.driver.find_element(By.NAME, 'q')
        #search_box.clear()
        search_box.send_keys(term)
        search_box.send_keys(Keys.RETURN)
        time.sleep(5)  # Wait for search results to load     
    
    def start_searching(self):
        """Start searching with today's topics"""
        self.stop_event.clear()
        self.running = True
        self._setup_driver()
        initial_points = self.get_current_points()
        self.data_manager.rewards = initial_points
        threading.Thread(target=self._search_loop, daemon=True).start()
  
        
    def _search_loop(self):
        """Search loop using today's specific topics"""
        today_topics = self.topics_provider.get_topics_for_today()  # <-- NEW TOPICS SOURCE
        num_topics = len(today_topics)
        search_count = 0
        topic_index = 0

        while self.running and search_count < 300 and self.get_current_points() < 90:
            # Restart topic search from beginning after all topics are used
            if topic_index >= num_topics:
                topic_index = 0
            term = today_topics[topic_index]
            topic_index += 1

            # Update GUI with current topic
            if self.gui is not None:
                try:
                    self.gui.set_current_topic(term)
                except Exception as e:
                    print(f"Error updating GUI topic: {e}")

            try:
                self._perform_search(term)
                self.data_manager.add_search(term, rewards=self.get_current_points())
                search_count += 1
                if search_count % 15 == 0:
                    self.data_manager.rewards = self.get_current_points()
            except Exception as e:
                print(f"Search error: {str(e)}")

            sleep_time = random.uniform(5, 7)
            interval = 0.5
            elapsed = 0
            while elapsed < sleep_time and not self.stop_event.is_set():
                time.sleep(interval)
                elapsed += interval
        
        print(f"*************** Quitting from Search Loop *************") 
        self.data_manager.rewards = self.last_points # baber added this line to set last points July 17
        self.running = False
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error quitting driver: {str(e)}")
              
    def stop_searching(self):
        """Stop the search process and quit the browser driver."""
        self.running = False
        self.stop_event.set()
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error quitting driver: {str(e)}")