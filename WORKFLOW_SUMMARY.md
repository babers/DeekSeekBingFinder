# Workflow & Module Summary

## Workflow Overview

1. **Startup**: Run `main.py` to launch the Tkinter GUI and initialize all modules.
2. **User Action**: Click "Start Searching" in the GUI to begin automated Bing searches.
3. **Search Automation**: `BrowserController` uses Selenium to perform Bing searches with daily/random topics.
4. **Progress Tracking**: `DataManager` records each search and updates rewards points.
5. **Visualization**: The GUI displays current stats and plots rewards points (X-axis) vs. searches (Y-axis) in real time.
6. **Shutdown Automation**: When all rewards and search loop conditions are met, and the shutdown checkbox is enabled, a professional dialog box appears allowing the user to cancel the scheduled shutdown within 60 seconds. If not cancelled, the PC will shut down automatically.
7. **User Control**: The user can stop the search process or cancel the shutdown sequence at any time.

## Newly Added/Updated Modules

### `rewards_watcher.py`
- Monitors completion of rewards and search loop.
- Triggers a shutdown sequence if the GUI checkbox is enabled.
- Presents a styled dialog box with a 60-second countdown and a "Cancel Shutdown" button.
- Allows shutdown to be retried if the checkbox is toggled.

### GUI Enhancements
- Shutdown checkbox added to the GUI for user control.
- Graph now plots rewards points on the X-axis and searches on the Y-axis.
- Improved shutdown dialog appearance and button visibility.

### DataManager Enhancements
- Tracks search history and rewards points for plotting and logic.
- Provides methods to mark completion and reset state for new runs.

## Business Logic Summary
- Automated Bing searches maximize rewards points.
- All progress and stats are tracked and visualized in real time.
- Shutdown is only triggered when all conditions are met and can be cancelled by the user.
- The workflow is modular, robust, and user-friendly.

---

For more details, see the docstrings in each module and the comments in the code.
