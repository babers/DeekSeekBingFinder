
# Add this at the top of main.py before other imports
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# main.py
from gui_module import GUI
from browser_controller import BrowserController
from data_manager import DataManager

def main():
    data_manager = DataManager()
    gui = None
    browser_controller = BrowserController(data_manager)  # Temporary, will be replaced
    gui = GUI(data_manager, browser_controller)
    browser_controller.gui = gui  # Set the GUI reference for topic updates
    gui.start()

if __name__ == "__main__":
    main()