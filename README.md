# DeekSeekBingFinder

Automate Bing searches to maximize Microsoft Rewards points using Selenium and a Tkinter GUI. Includes automatic shutdown logic, an auto-updated Edge WebDriver, and a professional user interface.

## Features

- Automated Bing searches with random or daily topics
- Tracks and displays current rewards points and search count
- Real-time GUI with progress graph (Rewards Points vs Searches)
- Edge WebDriver auto-update at startup by parsing the official Microsoft developer portal
  - Uses robust XPath parsing (with lxml) and logs detailed parse results (counts, href, parsed version)
  - Falls back to a regex-based portal parse if XPath isn’t available
  
### Recent driver manager fixes (pre-last-commit)

- Retry/backoff: portal fetches and driver ZIP downloads now retry with exponential backoff to handle transient network failures.
- Platform-verified URLs: XPath-extracted links are only accepted when they match the detected platform (e.g., `edgedriver_win64.zip`). If XPath yields a different-platform link (mac64, etc.), the manager now builds and verifies a platform-specific candidate URL before accepting it.
- Safer download/install: improved verification prevents downloading mismatched platform ZIPs and reduces false negatives.
- API change (richer return): `ensure_latest_msedgedriver()` now returns a tuple `(installed_path, installed_version, latest_available)`; `main.py` was updated to handle both the new tuple and the legacy string return for compatibility.
- Diagnostics added: small helper scripts under `tools/` (`diag_*`) were added to inspect portal parsing and to force-run the installer for debugging.

- GUI improvements
  - Window title shows the installed WebDriver version (e.g., “WebDriver 139.0.3405.111”)
  - “Shutdown PC when finished” checkbox controls post-completion shutdown
- Shutdown automation with a 60-second, cancelable dialog (only after targets are met)
- Config-driven, well-logged, and modular

## Requirements

- Python 3.8+
- Microsoft Edge browser
- Required Python packages (see requirements.txt)
  - selenium, matplotlib, lxml (tkinter is built-in on Windows)

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

3. No manual driver setup needed — the app will download/refresh `msedgedriver.exe` at startup.

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

Optional overrides at startup:

- Force a specific WebDriver URL:
  - `--driver-url https://msedgedriver.microsoft.com/<ver>/edgedriver_win64.zip`
- Force a specific WebDriver version:
  - `--driver-version 139.0.3405.111`

## Project Structure

- `main.py` — Entry point, initializes modules and GUI
- `browser_controller.py` — Handles browser automation and search logic
- `data_manager.py` — Tracks search history and rewards, provides completion flags and plotting data (SQLite-backed)
- `gui_module.py` — Tkinter GUI for user interaction, visualization, shutdown control, and graphing (title shows WebDriver version)
- `rewards_watcher.py` — Monitors completion, triggers shutdown sequence, manages shutdown dialog
- `utils/edge_driver_manager.py` — Resolves and installs the correct Edge WebDriver via Microsoft portal (XPath + regex fallback)
- `utils/logger.py` — Central logging setup (console + rotating file)
- `utils/exceptions.py` — Structured exception types
- `daily_topics.py` — Provides daily search topics
- `config.yaml` — App configuration (URLs, selectors, paths, logging; optional WebDriver overrides)
- `requirements.txt` — Python dependencies
- `msedgedriver.exe` — Edge WebDriver binary (auto-managed)

## Configuration & Customization

- Edit `config.yaml` to change:
  - URLs/selectors
  - Paths (WebDriver, database, log file)
  - Search settings (targets, pauses, polling)
  - Logging (level and format)

- CLI flags `--driver-url` and `--driver-version` override config and force an install before startup.
- Edit `daily_topics.py` to change or expand search topics.

## Troubleshooting

- Logs are written to `app.log`. Look for lines like:
  - `Using XPaths -> link: '...', version: '...'`
  - `XPath link nodes count: N`, `XPath version nodes count: M`
  - `XPath parse results -> version: X.Y.Z.W, url: https://.../edgedriver_win64.zip`
- If lxml isn’t installed, the app logs it and falls back to regex-based parsing.
- For Selenium errors, ensure Edge is installed and up to date; the driver should auto-match via portal download.
- If shutdown does not trigger, confirm both rewards and loop are complete and the checkbox is enabled. The startup prompt was removed; shutdown only appears on completion.

## Workflow & Module Summary

### Workflow Overview

1. Startup: Run `main.py` to launch the Tkinter GUI and initialize all modules. Before the GUI, the app ensures the correct Edge WebDriver is installed by parsing the Microsoft portal.
2. User Action: Click "Start Searching" in the GUI to begin automated Bing searches.
3. Search Automation: `BrowserController` uses Selenium to perform Bing searches with daily/random topics.
4. Progress Tracking: `DataManager` records each search and updates rewards points.
5. Visualization: The GUI displays current stats and plots rewards points (X-axis) vs. searches (Y-axis) in real time.
6. Shutdown Automation: When all rewards and search loop conditions are met, and the shutdown checkbox is enabled, a professional dialog box appears allowing the user to cancel the scheduled shutdown within 60 seconds. If not cancelled, the PC will shut down automatically.
7. User Control: The user can stop the search process or cancel the shutdown sequence at any time.

### Newly Added/Updated Modules

- `rewards_watcher.py`: Monitors completion of rewards and search loop, triggers shutdown sequence, presents styled dialog box, allows shutdown to be retried if the checkbox is toggled.
- GUI Enhancements: Title shows WebDriver version; shutdown checkbox; improved shutdown dialog; graph plots rewards points vs searches.
- DataManager Enhancements: Tracks search history and rewards points, provides completion flags and reset methods; persists to SQLite.
- Edge WebDriver Manager: Auto-resolves and downloads correct `msedgedriver.exe` by parsing the official portal (XPath + regex fallback), logs the exact URL/version used.

### Business Logic Summary

- Automated Bing searches maximize rewards points.
- All progress and stats are tracked and visualized in real time.
- Shutdown is only triggered when all conditions are met and can be cancelled by the user.
- The workflow is modular, robust, and user-friendly.

## License

MIT License

---

## Created by babers
