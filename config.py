"""Configuration loader with sane defaults for packaged builds.

If explicit paths are not provided in config.yaml, defaults are placed in a
per-user app data directory so the app remains writable when installed.
"""

import yaml
import logging
import os
from utils.paths import get_app_data_dir, resource_path

class Config:
    """
    A class to load and manage configuration from a YAML file.
    """
    def __init__(self, config_data):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Loading configuration...")
        
        # URLs
        self.rewards_url = config_data.get('urls', {}).get('rewards')
        self.search_url = config_data.get('urls', {}).get('search')
        
        # XPaths and Selectors
        self.points_xpath = config_data.get('xpaths', {}).get('points')
        self.search_box_name = config_data.get('selectors', {}).get('search_box_name')
        
        # Paths
        self.webdriver_path = config_data.get('paths', {}).get('webdriver')
        self.database_path = config_data.get('paths', {}).get('database')
        self.log_file_path = config_data.get('paths', {}).get('log_file')
        
        # Optional WebDriver overrides
        webdriver_cfg = config_data.get('webdriver', {})
        self.webdriver_url = webdriver_cfg.get('url')
        self.webdriver_version = webdriver_cfg.get('version')

        # Search Settings
        search_settings = config_data.get('search_settings', {})
        self.target_points = search_settings.get('target_points', 90)
        self.searches_before_pause = search_settings.get('searches_before_pause', 5)
        self.pause_duration_minutes = search_settings.get('pause_duration_minutes', 2)
        self.min_sleep_seconds = search_settings.get('min_sleep_seconds', 5)
        self.max_sleep_seconds = search_settings.get('max_sleep_seconds', 7)
        self.poll_interval = search_settings.get('poll_interval', 5)

        # Logging Settings
        logging_settings = config_data.get('logging', {})
        self.log_level = logging_settings.get('level', 'INFO')
        self.log_format = logging_settings.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        self.logger.info("Configuration loaded successfully.")

    @classmethod
    def from_yaml(cls, file_path: str | None = 'config.yaml'):
        """
        Loads configuration from a YAML file and creates a Config object.
        """
        try:
            # Resolve default config path for packaged builds
            path = resource_path(file_path) if file_path else resource_path('config.yaml')
            if not os.path.isfile(path):
                # Also try raw provided path if resource resolution failed
                path = file_path or 'config.yaml'
            with open(path, 'r') as f:
                config_data = yaml.safe_load(f)
            cfg = cls(config_data)

            # Apply default paths if missing
            app_dir = get_app_data_dir()
            if not cfg.database_path:
                cfg.database_path = os.path.join(app_dir, 'searches.db')
            if not cfg.log_file_path:
                cfg.log_file_path = os.path.join(app_dir, 'app.log')
            if not cfg.webdriver_path:
                cfg.webdriver_path = os.path.join(app_dir, 'msedgedriver.exe')

            return cfg
        except FileNotFoundError:
            logging.error(f"Configuration file not found at {file_path}")
            raise
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML file: {e}")
            raise
