# browser_controller.py

import logging
import random
import re
import threading
import time
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import Config
from data_manager import DataManager
from daily_topics import DailyTopics

class BrowserController:
    def __init__(self, config: Config, data_manager: DataManager, gui=None):
        self.config = config
        self.data_manager = data_manager
        self.gui = gui
        self.logger = logging.getLogger(__name__)
        
        self.running = False
        self.driver = None
        self.topics_provider = DailyTopics()
        self.last_points = 0
        self.stop_event = threading.Event()

    def _setup_driver(self):
        """Sets up the Edge WebDriver using the path from the config."""
        try:
            edge_service = Service(executable_path=self.config.webdriver_path)
            self.driver = webdriver.Edge(service=edge_service)
            self.logger.info("WebDriver setup successfully.")
        except Exception as e:
            self.logger.error(f"Failed to setup WebDriver: {e}")
            raise

    def get_current_points(self):
        """Fetches the current rewards points from the rewards page."""
        try:
            if not self.driver:
                self._setup_driver()
            
            self.driver.get(self.config.rewards_url)
            wait = WebDriverWait(self.driver, 30)
            
            points_element = wait.until(EC.visibility_of_element_located((By.XPATH, self.config.points_xpath)))
            points_text = points_element.text
            match = re.search(r'\d+', points_text)
            
            if match:
                points = int(match.group())
                self.logger.info(f"Current rewards points: {points}")
                self.last_points = points
                return points
            else:
                self.logger.warning(f"Could not parse points from text: '{points_text}'")
                return self.last_points
        except (TimeoutException, WebDriverException) as e:
            self.logger.error(f"Selenium error while getting points: {e}")
            if self.driver:
                self.driver.save_screenshot("points_error.png")
            return self.last_points
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while getting points: {e}")
            return self.last_points

    def _perform_search(self, term: str):
        """Performs a single search on Bing."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.driver.get(self.config.search_url)
                search_box = self.driver.find_element(By.NAME, self.config.search_box_name)
                search_box.clear()
                search_box.send_keys(term)
                search_box.send_keys(Keys.RETURN)
                self.logger.info(f"Performed search for term: '{term}'")
                time.sleep(self.config.min_sleep_seconds) # Basic wait after search
                return
            except Exception as e:
                self.logger.warning(f"Search attempt {attempt + 1} failed for term '{term}': {e}")
                if attempt == max_retries - 1:
                    self.logger.error(f"All retries failed for term '{term}'.")
                    raise
                time.sleep(2)

    def start_searching(self):
        """Starts the search loop in a new thread."""
        self.logger.info("Starting search process...")
        self.stop_event.clear()
        self.running = True
        threading.Thread(target=self._search_loop, daemon=True).start()

    def _search_loop(self):
        """The main loop for performing searches until the target is met."""
        try:
            self._setup_driver()
            initial_points = self.get_current_points()
            self.data_manager.rewards_points = initial_points
            
            today_topics = self.topics_provider.get_topics_for_today()
            num_topics = len(today_topics)
            topic_index = 0
            searches_since_last_increase = 0

            while self.running and self.get_current_points() < self.config.target_points:
                if self.stop_event.is_set():
                    self.logger.info("Stop event received, exiting search loop.")
                    break

                term = today_topics[topic_index % num_topics]
                topic_index += 1

                if self.gui:
                    self.gui.set_current_topic(term)

                self._perform_search(term)
                current_points = self.get_current_points()
                self.data_manager.update_rewards(current_points)
                self.data_manager.add_search(term, current_points)

                if current_points > self.last_points:
                    self.last_points = current_points
                    searches_since_last_increase = 0
                else:
                    searches_since_last_increase += 1

                if searches_since_last_increase >= self.config.searches_before_pause:
                    self.logger.info(f"No points increase after {self.config.searches_before_pause} searches. Pausing...")
                    if self.gui:
                        self.gui.set_pause_timer(self.config.pause_duration_minutes * 60)
                    time.sleep(self.config.pause_duration_minutes * 60)
                    searches_since_last_increase = 0

                sleep_time = random.uniform(self.config.min_sleep_seconds, self.config.max_sleep_seconds)
                time.sleep(sleep_time)

        except Exception as e:
            self.logger.critical(f"A critical error occurred in the search loop: {e}", exc_info=True)
        finally:
            self.logger.info("Search loop finished.")
            self.running = False
            if self.driver:
                try:
                    self.driver.quit()
                    self.logger.info("WebDriver quit successfully.")
                except Exception as e:
                    self.logger.error(f"Error quitting driver: {e}")
            
            self.data_manager.mark_loop_complete()
            if self.get_current_points() >= self.config.target_points:
                self.data_manager.mark_rewards_complete()

    def stop_searching(self):
        """Stops the search loop gracefully."""
        self.logger.info("Stop searching requested.")
        self.running = False
        self.stop_event.set()
