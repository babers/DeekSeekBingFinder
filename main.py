# Add this at the top of main.py before other imports
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# main.py
from gui_module import GUI
from browser_controller import BrowserController
from data_manager import DataManager
from rewards_watcher import RewardsWatcher

def main():
    data_manager = DataManager()
    gui = None
    browser_controller = BrowserController(data_manager)
    gui = GUI(data_manager, browser_controller)
    browser_controller.gui = gui

    rewards_watcher = RewardsWatcher(data_manager, gui)
    gui.rewards_watcher = rewards_watcher  # <-- Add this line
    rewards_watcher.start()

    try:
        gui.start()
    finally:
        rewards_watcher.stop()

if __name__ == "__main__":
    main()