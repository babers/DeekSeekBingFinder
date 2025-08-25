"""Custom exception hierarchy for DeekSeekBingFinder.

Keeps error handling expressive and consistent across modules.
Import and raise these where appropriate instead of generic Exceptions.
"""

from __future__ import annotations


class ApplicationError(Exception):
	"""Base class for all custom exceptions in this app."""


class ConfigError(ApplicationError):
	"""Raised when configuration loading or validation fails."""


class BrowserSetupError(ApplicationError):
	"""Raised when the WebDriver cannot be created or initialized."""


class RewardsPageError(ApplicationError):
	"""Raised when scraping or parsing the rewards page fails persistently."""


class SearchExecutionError(ApplicationError):
	"""Raised when a search action fails after retries."""


class PersistenceError(ApplicationError):
	"""Raised when database operations fail in DataManager."""


class ShutdownError(ApplicationError):
	"""Raised when system shutdown scheduling or execution fails."""

