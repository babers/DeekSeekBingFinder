# browser_controller.py

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import random
import time
import threading
from daily_topics import DailyTopics
import re
import traceback

# At the top of each module
print(f"Loading {__name__} module") 

class BrowserController:
    def __init__(self, data_manager, gui=None):
        self.data_manager = data_manager
        self.gui = gui  # Reference to GUI for updating topic
        self.running = False
        self.driver = None
        self.topics_provider = DailyTopics()
        self.last_points = None
        self.stop_event = threading.Event()
        
    
    # Removed unused _get_current_day_topics
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
            wait = WebDriverWait(self.driver, 30)
            try:
                points_element = wait.until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "pointsDetail"))
                )
            except TimeoutException as e:
                print("Timeout: Could not find points element. The page structure may have changed.")
                if self.driver:
                    self.driver.save_screenshot("timeout_error.png")
                    page_source = self.driver.page_source
                    print("Page source (first 1000 chars):\n", page_source[:1000])
                return self.last_points if self.last_points is not None else 0
            points_text = points_element.text
            match = re.search(r'\d+', points_text)
            if match:
                points = int(match.group())
                print("************  PC Search Points Balance **************** :", points)
                self.last_points = points
                return points
            else:
                print("Could not find points in text:", points_text)
                return self.last_points if self.last_points is not None else 0
        except (TimeoutException, WebDriverException) as e:
            print(f"Selenium error in get_current_points: {type(e).__name__}: {e}")
            if self.driver:
                self.driver.save_screenshot("selenium_error.png")
            return self.last_points if self.last_points is not None else 0
        except Exception as e:
            print(f"Unexpected error in get_current_points: {type(e).__name__}: {e}")
            return self.last_points if self.last_points is not None else 0

            
    # Removed unused _generate_search_term
            
        
    def _perform_search(self, term):
        if not self.driver:
            self._setup_driver()
        try:
            self.driver.get('https://www.bing.com/news/?form=ml11z9&crea=ml11z9&wt.mc_id=ml11z9&rnoreward=1&rnoreward=1')
            search_box = self.driver.find_element(By.NAME, 'q')
            #search_box.clear()
            search_box.send_keys(term)
            search_box.send_keys(Keys.RETURN)
            time.sleep(5)  # Wait for search results to load
        except Exception as e:
            # Handle navigation/network timeouts and log the error
            print(f"Search navigation error: {type(e).__name__}: {e}")
            if self.driver:
                self.driver.save_screenshot("search_timeout_error.png")
    
    def start_searching(self):
        """Start searching with today's topics"""
        self.stop_event.clear()
        self.running = True
        self._setup_driver()
        initial_points = self.get_current_points()
        self.data_manager.rewards = initial_points
        threading.Thread(target=self._search_loop, daemon=True).start()
  
        
    def _search_loop(self):
        """Search loop using today's specific topics, with pause if points do not increase after 10 searches."""
        today_topics = self.topics_provider.get_topics_for_today()
        num_topics = len(today_topics)
        topic_index = 0
        last_points = self.get_current_points()
        searches_since_last_increase = 0
        pause_duration = 2 * 60  # 2 minutes in seconds

        while self.running and self.get_current_points() < 90:
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
                current_points = self.get_current_points()
                self.data_manager.add_search(term, rewards=current_points)
                if len(self.data_manager.searched_terms) % 15 == 0:
                    self.data_manager.rewards = current_points
            except Exception as e:
                print(f"Search error: {str(e)}")

            # Check if points increased
            current_points = self.get_current_points()
            if current_points > last_points:
                last_points = current_points
                searches_since_last_increase = 0
            else:
                searches_since_last_increase += 1

            # If 5 searches without points increase, pause for 2 minutes
            if searches_since_last_increase >= 5:
                if self.gui is not None:
                    try:
                        self.gui.set_pause_timer(pause_duration)
                    except Exception as e:
                        print(f"Error updating GUI pause timer: {e}")
                print("No points increase after 5 searches. Pausing for 2 minutes...")
                remaining = pause_duration
                while remaining > 0 and self.running and not self.stop_event.is_set():
                    if self.gui is not None:
                        try:
                            self.gui.update_pause_timer(remaining)
                        except Exception as e:
                            print(f"Error updating GUI pause timer: {e}")
                    time.sleep(1)
                    remaining -= 1
                if self.gui is not None:
                    try:
                        self.gui.clear_pause_timer()
                    except Exception as e:
                        print(f"Error clearing GUI pause timer: {e}")
                searches_since_last_increase = 0

            sleep_time = random.uniform(5, 7)
            interval = 0.5
            elapsed = 0
            while elapsed < sleep_time and not self.stop_event.is_set():
                time.sleep(interval)
                elapsed += interval

        print("*************** Quitting from Search Loop *************")
        self.data_manager.rewards = self.last_points
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