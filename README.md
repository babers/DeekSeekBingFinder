# DeekSeekBingFinder

Automate Bing searches to maximize Microsoft Rewards points using Selenium and a Tkinter GUI.

## Features

- Automated Bing searches with random or daily topics
- Tracks and displays current rewards points and search count
- Real-time GUI with progress graph and current topic display
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

- The GUI will open, showing search stats and a graph.
- Click "Start Searching" to begin automated Bing searches.
- The current topic being searched is displayed in the GUI.
- Click "Stop" to halt the process.

## Project Structure

- `main.py` — Entry point, initializes modules and GUI
- `browser_controller.py` — Handles browser automation and search logic
- `data_manager.py` — Tracks search history and rewards
- `gui_module.py` — Tkinter GUI for user interaction and visualization
- `daily_topics.py` — Provides daily search topics
- `msedgedriver.exe` — Edge WebDriver binary

## Customization

- Edit `daily_topics.py` to change or expand the list of search topics.
- You can adapt the browser controller to use Chrome or Firefox by changing the driver setup.

## Troubleshooting

- Ensure your Edge browser and msedgedriver.exe versions match.
- If you see browser or Selenium errors, check the console for details and update selectors if Bing's page layout changes.
- For GUI issues, ensure all required Python packages are installed.

## License

MIT License

---

## Created by babers
