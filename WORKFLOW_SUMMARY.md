# Workflow & Module Summary

## Workflow Overview

1. **Startup**: Run `main.py` to launch the Tkinter GUI and initialize all modules.

- Before the GUI starts, the app ensures the correct Edge WebDriver is installed by parsing the Microsoft developer portal.
- Preferred method: XPath-based parsing with `lxml`; logs matched node counts, extracted href, and parsed version.
- Fallback: Regex-based portal parsing filtered by platform (`win64`/`win32`).

1. **User Action**: Click "Start Searching" in the GUI to begin automated Bing searches.
1. **Search Automation**: `BrowserController` uses Selenium to perform Bing searches with daily/random topics.
1. **Progress Tracking**: `DataManager` records each search and updates rewards points.
1. **Visualization**: The GUI displays current stats and plots rewards points (X-axis) vs. searches (Y-axis) in real time.
1. **Shutdown Automation**: When all rewards and search loop conditions are met, and the shutdown checkbox is enabled, a professional dialog box appears allowing the user to cancel the scheduled shutdown within 60 seconds. If not cancelled, the PC will shut down automatically.
1. **User Control**: The user can stop the search process or cancel the shutdown sequence at any time.

## Newly Added/Updated Modules

### `rewards_watcher.py`

- Monitors completion of rewards and search loop.
- Triggers a shutdown sequence if the GUI checkbox is enabled.
- Presents a styled dialog box with a 60-second countdown and a "Cancel Shutdown" button.
- Allows shutdown to be retried if the checkbox is toggled.

### GUI Enhancements

- Window title shows installed WebDriver version (when available).
- Shutdown checkbox added to the GUI for user control.
- Graph now plots rewards points on the X-axis and searches on the Y-axis.
- Improved shutdown dialog appearance and button visibility.
 - Network indicator: a colorized (green/red) network status indicator was added to the stats panel and is refreshed every second.

### DataManager Enhancements

- Tracks search history and rewards points for plotting and logic (with SQLite persistence).
- Provides methods to mark completion and reset state for new runs.

### Edge WebDriver Manager (`utils/edge_driver_manager.py`)

- Resolves the latest driver from the official portal.
- Builds canonical Microsoft download URLs and installs/replaces `msedgedriver.exe`.
- Exposes `--driver-url` and `--driver-version` overrides via CLI; also supports optional `webdriver:` overrides in `config.yaml`.
- Logs XPath counts, extracted href, combined version text (truncated), and parsed version for debugging.

### `utils/network.py`
- Provides `is_connected()` and a `wait_for_connection()` helper used at startup and by the `BrowserController`.

### `browser_controller.py` (behavior changes)
- Pause logic: fixed so the pause timer is only triggered when rewards points remain unchanged for the configured number of consecutive searches (`searches_before_pause` in `config.yaml`).
- `get_current_points()` no longer mutates internal comparison state; it returns the raw parsed points and the search loop handles comparisons. This prevents accidental resets of the pause counter.
- Network resilience: the controller will wait for connectivity before performing searches or fetching points, preserving GUI/backend state during outages.

## Business Logic Summary

- Automated Bing searches maximize rewards points.
- All progress and stats are tracked and visualized in real time.
- Shutdown prompt was removed from startup; shutdown is only triggered when all conditions are met and can be cancelled by the user.
- The workflow is modular, robust, and user-friendly.

## Recent Changes and Notes
- The app now waits for network connectivity at startup and will retry until connected.
- During network outages the app pauses network-dependent operations (searches, point lookups) without resetting session state or counters.
- The pause-on-no-increase logic now uses consecutive unchanged reads (configurable via `config.yaml`).
 
### Driver manager fixes (pre-last-commit)

- Retry/backoff on portal and download: The developer portal fetch (XPath/regex) and the ZIP download now perform limited retries with exponential backoff to tolerate transient network/DNS failures.
- Platform URL verification: If XPath parsing returns a version link for a different platform (for example `edgedriver_mac64.zip`), the manager now constructs the matching platform URL (e.g., `edgedriver_win64.zip`) for that version and checks that it exists before using it. This prevents downloading the wrong platform artifact and avoids accepting non-matching XPath links.
- Richer return value: `ensure_latest_msedgedriver()` now returns `(path, installed_version, latest_available)` so callers can access both installed and available versions. Callers were updated (e.g., `main.py`) to remain compatible.
- Small diagnostic scripts added under `tools/` (e.g., `diag_edge_driver.py`, `run_ensure.py`) to reproducibly inspect portal parsing and to force a driver install for debugging.


---

For more details, see the docstrings in each module and the comments in the code.
