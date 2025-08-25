# DeekSeekBingFinder


Automate Bing searches to maximize Microsoft Rewards points using Selenium and a Tkinter GUI. Includes automatic shutdown logic and a professional user interface.

## Features

- Automated Bing searches with random or daily topics
- Tracks and displays current rewards points and search count
- Real-time GUI with progress graph (Rewards Points vs Searches)
- Shutdown automation: When all conditions are met, a dialog box appears allowing user to cancel scheduled shutdown
- User can enable/disable shutdown via GUI checkbox
- Modular code: easy to extend or adapt

## Requirements

- Python 3.8+
- Microsoft Edge browser
- Edge WebDriver (msedgedriver.exe) matching your Edge version
- Required Python packages (see requirements.txt)

## Installation

1. Clone this repository:

   ```sh
   git clone https://github.com/babers/DeekSeekBingFinder.git
   cd DeekSeekBingFinder
   ```

2. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

3. Place `msedgedriver.exe` in the project root (download from Microsoft if needed).

## Usage


Run the main script:

```sh
python main.py
```

- The GUI will open, showing search stats and a graph (Rewards Points vs Searches).
- Click "Start Searching" to begin automated Bing searches.
- The current topic being searched is displayed in the GUI.
- Click "Stop" to halt the process.
- Enable the "Shutdown PC when finished" checkbox to allow automatic shutdown when all rewards and searches are complete.
- When shutdown is triggered, a dialog box appears with a 60-second countdown and a Cancel button. If not cancelled, the PC will shut down automatically.

## Project Structure

- `main.py` — Entry point, initializes modules and GUI
- `browser_controller.py` — Handles browser automation and search logic
- `data_manager.py` — Tracks search history and rewards, provides completion flags and plotting data
- `gui_module.py` — Tkinter GUI for user interaction, visualization, shutdown control, and graphing
- `rewards_watcher.py` — Monitors completion, triggers shutdown sequence, manages shutdown dialog
- `daily_topics.py` — Provides daily search topics
- `msedgedriver.exe` — Edge WebDriver binary


## Customization

- Edit `daily_topics.py` to change or expand the list of search topics.
- You can adapt the browser controller to use Chrome or Firefox by changing the driver setup.
- Adjust shutdown logic or dialog appearance in `rewards_watcher.py` as needed.


## Troubleshooting

- Ensure your Edge browser and msedgedriver.exe versions match.
- If you see browser or Selenium errors, check the console for details and update selectors if Bing's page layout changes.
- For GUI issues, ensure all required Python packages are installed.
- If shutdown does not trigger, check that both rewards and loop are marked complete and the checkbox is enabled.
- If the shutdown dialog does not appear, verify the GUI and watcher modules are correctly wired.


## Workflow & Module Summary

### Workflow Overview
1. Startup: Run `main.py` to launch the Tkinter GUI and initialize all modules.
2. User Action: Click "Start Searching" in the GUI to begin automated Bing searches.
3. Search Automation: `BrowserController` uses Selenium to perform Bing searches with daily/random topics.
4. Progress Tracking: `DataManager` records each search and updates rewards points.
5. Visualization: The GUI displays current stats and plots rewards points (X-axis) vs. searches (Y-axis) in real time.
6. Shutdown Automation: When all rewards and search loop conditions are met, and the shutdown checkbox is enabled, a professional dialog box appears allowing the user to cancel the scheduled shutdown within 60 seconds. If not cancelled, the PC will shut down automatically.
7. User Control: The user can stop the search process or cancel the shutdown sequence at any time.

### Newly Added/Updated Modules
- `rewards_watcher.py`: Monitors completion of rewards and search loop, triggers shutdown sequence, presents styled dialog box, allows shutdown to be retried if the checkbox is toggled.
- GUI Enhancements: Shutdown checkbox, improved shutdown dialog, graph plots rewards points vs searches.
- DataManager Enhancements: Tracks search history and rewards points, provides completion flags and reset methods.

### Business Logic Summary
- Automated Bing searches maximize rewards points.
- All progress and stats are tracked and visualized in real time.
- Shutdown is only triggered when all conditions are met and can be cancelled by the user.
- The workflow is modular, robust, and user-friendly.

## License

MIT License

---

## Created by babers
