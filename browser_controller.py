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
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.running = False
        self.driver = None
        # self.search_terms = [
        #     # List of random search terms
            
        #     'Olympics', 'How memory works in the human brain', 'Mysterious stone structures around the world', 'The rise of eSports', 
        #     'Animal species rediscovered after extinction', 'The science of aging', 'Paranormal investigations and their tools', 'The impact of AI on job markets', 
        #     'Historical figures who changed the world', 'How solar flares affect Earth', 'The mystery of the Zodiac Killer', 'The psychology of cults', 
        #     'How satellites communicate', 'The history of tattoos in different cultures', 'Unexplained mass animal deaths', 'The future of renewable energy', 
        #     'The science behind dreams', 'How COVID-19 vaccines were developed', 'The lost treasure of the Knights Templar', 'Effects of deforestation on indigenous tribes', 
        #     'Cryptography’s role in historical wars', 'How animals adapt to urban environments', 'The mystery of the Nazca Lines', 'The rise of plant-based meat alternatives', 'Unexplained spontaneous human combustion', 'Social media’s influence on politics', 
        #     'Possibility of life on Europa (Jupiter’s moon)', 'How CRISPR is changing genetics', 
        #     'The history of samurai warriors', 'Effects of sleep deprivation on health', 'The Oak Island Money Pit mystery', 'Global cultural impact of anime', 'Unexplained ancient artifacts', 'The future of space tourism', 
        #     'The science of addiction', 'The Philadelphia Experiment conspiracy', 'How the human microbiome affects health', 'The history of the Freemasons', 'Mysterious sky lights (e.g., Hessdalen lights)', 'Fast fashion’s environmental impact', 
        #     'How quantum entanglement works', 'Disappearance of Flight MH370', 'The science of placebo effects', 'Ancient civilizations’ knowledge of astronomy', 'Ethics of artificial intelligence', 'The mystery of the Taos Hum', 'Vertical farming’s role in agriculture', 
        #     'History of the Rosetta Stone', 'Microplastics’ effect on human health', 'The science behind time perception', 
        #     'Unexplained ghost ship sightings', 'Future of holographic technology', 'Psychology of color in marketing', 'How volcanoes predict eruptions', 'The Dancing Plague of 1518',
        #     'AI advancements', 'space exploration', 'quantum computing', 'sustainable energy', 'global economics', 'modern architecture', 'marine biology', 'climate change', 'nanotechnology',
        #     'renewable resources'
        # ]
        
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
        
    
       # from webdriver_manager.microsoft import EdgeChromiumDriverManager
       # self.driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()))
    
    
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
    
    # def get_current_points(self):
    #     """Public method to fetch current reward points"""
    #     try:
    #         if not self.driver:
    #             self._setup_driver()
                
    #         self.driver.get("https://rewards.bing.com/pointsbreakdown")
    #         time.sleep(3)
    #         points_element = self.driver.find_element(
    #             By.CSS_SELECTOR,
    #             '[class="pointsDetail c-subheading-3 ng-binding"]'
    #         )
            
    #         print("************  PC Search Points Balance **************** :", points_element.text[:2])         
    #         return int(points_element.text[:2])
    
    #     except Exception as e:
    #         print(f"Error retrieving points: {str(e)}")
    #         return 0
            
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
        
        while (self.running and 
            len(self.data_manager.searched_terms) < 300) and self.get_current_points() < 90 :
            
            # Cycle through today's topics with variations
            base_topic = today_topics[len(self.data_manager.searched_terms) % num_topics]  # <-- UPDATED
            term = f"{base_topic}"
            
            if term not in self.data_manager.searched_terms:
                try:
                    self._perform_search(term)
                    self.data_manager.add_search(term,rewards=self.get_current_points()) # added rewards parameter by Baber
                    # Update points every 15 searches
                    if len(self.data_manager.searched_terms) % 15 == 0:
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
      
      
    # def _search_loop(self):
    #     while self.running and len(self.data_manager.searched_terms) < 100:
    #         term = self._generate_search_term()
    #         if term not in self.data_manager.searched_terms:
    #             self._perform_search(term)
    #             self.data_manager.add_search(term)
    #         time.sleep(random.uniform(5, 10))
            
    #     if self.driver:
    #         self.driver.quit()
              
    def stop_searching(self):
        """Stop the search process and quit the browser driver."""
        self.running = False
        self.stop_event.set()
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error quitting driver: {str(e)}")