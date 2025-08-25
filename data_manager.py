# data_manager.py
print(f"Loading {__name__} module")

import sqlite3
import logging
from datetime import datetime
from config import Config


class DataManager:
    def __init__(self, config: Config):
        self.config = config
        self.db_path = self.config.database_path
        self.logger = logging.getLogger(__name__)
        self._initialize_database()

        # Session data
        self.session_search_history = []
        self.rewards_points = 0
        self.total_searches_session = 0
        self.rewards_completed = False
        self.loop_completed = False
        self.logger.info(f"DataManager initialized with database at {self.db_path}")

    def _initialize_database(self):
        """Creates the database and table if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS searches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        term TEXT NOT NULL,
                        rewards_points INTEGER NOT NULL
                    )
                ''')
                conn.commit()
            self.logger.info("Database initialized successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            raise

    def reset(self):
        """Resets the in-memory session data for a new run."""
        self.session_search_history = []
        self.rewards_points = 0
        self.total_searches_session = 0
        self.rewards_completed = False
        self.loop_completed = False
        self.logger.info("Session data has been reset.")

    def update_rewards(self, points):
        self.rewards_points = points
        if self.rewards_points >= self.config.target_points:
            self.rewards_completed = True
            self.logger.info(f"Target points of {self.config.target_points} reached.")

    def mark_loop_complete(self):
        self.loop_completed = True
        self.logger.info("Search loop marked as complete.")

    def mark_rewards_complete(self):
        self.rewards_completed = True
        self.logger.info("Rewards marked as complete.")

    def get_current_counts(self):
        """Returns a dictionary with current session's total searches and rewards points."""
        return {
            'total': self.total_searches_session,
            'rewards': self.rewards_points
        }

    def add_search(self, term, rewards):
        """Adds a search to the session history and persists it to the database."""
        self.total_searches_session += 1
        self.session_search_history.append((self.total_searches_session, rewards))

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO searches (timestamp, term, rewards_points) VALUES (?, ?, ?)",
                    (datetime.now().isoformat(), term, rewards)
                )
                conn.commit()
            self.logger.debug(f"Persisted search for term '{term}' with {rewards} points.")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to persist search data: {e}")

    def get_all_time_history(self):
        """Retrieves the full search history from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, rewards_points FROM searches ORDER BY id ASC")
                return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve search history: {e}")
            return []