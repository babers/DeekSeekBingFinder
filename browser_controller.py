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

print(f"Loading {__name__} module") 

class BrowserController:
    def __init__(self, data_manager, gui=None):
        self.data_manager = data_manager
        self.gui = gui
        self.running = False
        self.driver = None
        self.topics_provider = DailyTopics()
        self.last_points = None
        self.stop_event = threading.Event()

    def _setup_driver(self):
        edge_driver_path = 'msedgedriver.exe'  # Replace with actual path
        edge_service = Service(executable_path=edge_driver_path)
        self.driver = webdriver.Edge(service=edge_service)

    def get_current_points(self):
        try:
            if not self.driver:
                self._setup_driver()
            self.driver.get("https://rewards.bing.com/pointsbreakdown")
            wait = WebDriverWait(self.driver, 30)
            try:
                points_element = wait.until(
                    EC.visibility_of_element_located((By.XPATH, '//*[@id="userPointsBreakdown"]/div/div[2]/div/div[1]/div/div[2]/mee-rewards-user-points-details/div/div/div/div/p[2]'))
                )
            except TimeoutException:
                print("Timeout: Could not find points element. The page structure may have changed.")
                if self.driver:
                    self.driver.save_screenshot("timeout_error.png")
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

    def _perform_search(self, term):
        if not self.driver:
            self._setup_driver()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.driver.get('https://www.bing.com/news/?form=ml11z9&crea=ml11z9&wt.mc_id=ml11z9&rnoreward=1&rnoreward=1')
                search_box = self.driver.find_element(By.NAME, 'q')
                search_box.send_keys(term)
                search_box.send_keys(Keys.RETURN)
                time.sleep(5)
                return
            except Exception as e:
                print(f"Search navigation error (attempt {attempt+1}/{max_retries}): {type(e).__name__}: {e}")
                if self.driver:
                    self.driver.save_screenshot(f"search_timeout_error_{attempt+1}.png")
                if attempt == max_retries - 1:
                    raise
                else:
                    time.sleep(2)

    def start_searching(self):
        self.stop_event.clear()
        self.running = True
        self._setup_driver()
        initial_points = self.get_current_points()
        self.data_manager.rewards_points = initial_points
        threading.Thread(target=self._search_loop, daemon=True).start()

    def _search_loop(self):
        today_topics = self.topics_provider.get_topics_for_today()
        num_topics = len(today_topics)
        topic_index = 0
        last_points = self.get_current_points()
        searches_since_last_increase = 0
        pause_duration = 2 * 60  # 2 minutes

        while self.running and self.get_current_points() < 90:
            if topic_index >= num_topics:
                topic_index = 0
            term = today_topics[topic_index]
            topic_index += 1

            if self.gui is not None:
                try:
                    self.gui.set_current_topic(term)
                except Exception as e:
                    print(f"Error updating GUI topic: {e}")

            try:
                self._perform_search(term)
                current_points = self.get_current_points()
                self.data_manager.update_rewards(current_points)
                self.data_manager.add_search(term, current_points)
            except Exception as e:
                print(f"Search error: {str(e)}")

            current_points = self.get_current_points()
            if current_points > last_points:
                last_points = current_points
                searches_since_last_increase = 0
            else:
                searches_since_last_increase += 1

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
        self.running = False
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error quitting driver: {str(e)}")

        # Set completion flags in DataManager
        self.data_manager.mark_loop_complete()
        if self.get_current_points() >= 90:
            self.data_manager.mark_rewards_complete()

    def stop_searching(self):
        self.running = False
        self.stop_event.set()
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error quitting driver: {str(e)}")
