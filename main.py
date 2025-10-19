import argparse
import logging
import sys
import os
import time
from config import Config
from utils.logger import setup_logging
from utils.edge_driver_manager import (
    ensure_latest_msedgedriver,
    ensure_msedgedriver_from_url,
    ensure_msedgedriver_version,
)
from utils.network import is_connected, wait_for_connection
from gui_module import GUI
from browser_controller import BrowserController
from data_manager import DataManager
from rewards_watcher import RewardsWatcher

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class Application:
    """
    Main application class to orchestrate the components of DeekSeekBingFinder.
    """
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing application components...")

        # Initialize components with dependency injection
        self.data_manager = DataManager(self.config)
        self.browser_controller = BrowserController(self.config, self.data_manager)
        self.gui = GUI(self.config, self.data_manager, self.browser_controller)
        self.rewards_watcher = RewardsWatcher(self.config, self.data_manager, self.gui)

        # Wire up dependencies between components
        self.browser_controller.gui = self.gui
        self.gui.rewards_watcher = self.rewards_watcher
        self.logger.info("Application components initialized successfully.")

    def run(self):
        """
        Start the application, including the rewards watcher and the main GUI loop.
        """
        self.logger.info("Starting Rewards Watcher...")
        self.rewards_watcher.start()

        try:
            self.logger.info("Starting GUI...")
            self.gui.start()
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user.")
        finally:
            self.logger.info("Stopping Rewards Watcher...")
            self.rewards_watcher.stop()
            self.logger.info("Application has been shut down gracefully.")

def main():
    """
    Entry point of the application.
    Parses arguments, sets up logging, loads configuration, and runs the app.
    """
    parser = argparse.ArgumentParser(description="DeekSeekBingFinder - Automate Bing searches for rewards.")
    parser.add_argument('--config', default='config.yaml', help='Path to the configuration file (default: config.yaml)')
    parser.add_argument('--driver-url', default=None, help='Direct URL to edgedriver zip (e.g., https://msedgedriver.microsoft.com/<ver>/edgedriver_win64.zip)')
    parser.add_argument('--driver-version', default=None, help='Specific Edge WebDriver version to install (e.g., 139.0.3405.111)')
    args = parser.parse_args()

    # Load configuration
    config = Config.from_yaml(args.config)

    # Set up logging
    setup_logging(log_level=config.log_level, log_file=config.log_file_path, log_format=config.log_format)

    # Ensure Edge WebDriver is present before starting anything else
    try:
        if args.driver_url:
            updated_path = ensure_msedgedriver_from_url(args.driver_url, config.webdriver_path or 'msedgedriver.exe')
        elif args.driver_version:
            updated_path = ensure_msedgedriver_version(args.driver_version, config.webdriver_path or 'msedgedriver.exe')
        elif getattr(config, 'webdriver_url', None):
            updated_path = ensure_msedgedriver_from_url(config.webdriver_url, config.webdriver_path or 'msedgedriver.exe')
        elif getattr(config, 'webdriver_version', None):
            updated_path = ensure_msedgedriver_version(config.webdriver_version, config.webdriver_path or 'msedgedriver.exe')
        else:
            res = ensure_latest_msedgedriver(config.webdriver_path or 'msedgedriver.exe')
            # Backwards compatible: function may return a string path or a tuple (path, installed_version, latest_available)
            if isinstance(res, tuple) and len(res) >= 1:
                updated_path = res[0]
            else:
                updated_path = res
        # Update config in-memory so BrowserController uses the latest path
        config.webdriver_path = updated_path
    except Exception as e:
        logging.getLogger(__name__).warning(f"Edge WebDriver precheck failed: {e}")

    # Verify that the driver file actually exists on disk. If the initial
    # precheck did not produce a driver (or it was removed), attempt a few
    # retries here at startup where the download/ensure logic already runs.
    try:
        # determine candidate path returned above or from config
        driver_candidate = None
        if 'updated_path' in locals() and updated_path:
            driver_candidate = updated_path
        elif getattr(config, 'webdriver_path', None):
            driver_candidate = config.webdriver_path

        def _normalize_return(res):
            if isinstance(res, tuple) and len(res) >= 1:
                return res[0]
            return res

        installed = False
        if driver_candidate and os.path.exists(os.path.abspath(driver_candidate)):
            # already present
            config.webdriver_path = os.path.abspath(driver_candidate)
            installed = True
            logging.getLogger(__name__).info(f"WebDriver present at startup: {config.webdriver_path}")
        else:
            # Try a few retries to fetch/install the driver at startup.
            retries = 3
            for attempt in range(1, retries + 1):
                try:
                    logging.getLogger(__name__).info(f"Startup WebDriver install attempt {attempt}/{retries}")
                    if args.driver_url:
                        res = ensure_msedgedriver_from_url(args.driver_url, config.webdriver_path or 'msedgedriver.exe')
                    elif args.driver_version:
                        res = ensure_msedgedriver_version(args.driver_version, config.webdriver_path or 'msedgedriver.exe')
                    elif getattr(config, 'webdriver_url', None):
                        res = ensure_msedgedriver_from_url(config.webdriver_url, config.webdriver_path or 'msedgedriver.exe')
                    elif getattr(config, 'webdriver_version', None):
                        res = ensure_msedgedriver_version(config.webdriver_version, config.webdriver_path or 'msedgedriver.exe')
                    else:
                        res = ensure_latest_msedgedriver(config.webdriver_path or 'msedgedriver.exe')

                    candidate_path = _normalize_return(res)
                    if candidate_path and os.path.exists(os.path.abspath(candidate_path)):
                        config.webdriver_path = os.path.abspath(candidate_path)
                        installed = True
                        logging.getLogger(__name__).info(f"WebDriver installed at startup: {config.webdriver_path}")
                        break
                    else:
                        logging.getLogger(__name__).warning(f"Attempt {attempt} did not produce a usable driver at {candidate_path}")
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Startup WebDriver install attempt {attempt} failed: {e}")

                # exponential backoff between attempts
                time.sleep(2 ** attempt)

        if not installed:
            logging.getLogger(__name__).warning(
                "msedgedriver.exe not found after startup attempts. The GUI will still start, "
                "but searches requiring the driver will fail until a valid driver is provided."
            )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to verify/install WebDriver at startup: {e}")

    # Create and run the application
    app = Application(config)
    # Ensure we have internet before starting the main GUI and search loop
    if not is_connected():
        logging.getLogger(__name__).warning("No internet detected at startup. Waiting for connectivity...")
        wait_for_connection(logger=logging.getLogger(__name__))

    app.run()

if __name__ == "__main__":
    main()