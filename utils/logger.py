"""Logging utilities for the application.

Provides a single entrypoint `setup_logging` to configure root logging
with optional console and rotating file handlers.
"""

from __future__ import annotations

import logging
import logging.handlers
from typing import Optional


_LEVELS = {
	"CRITICAL": logging.CRITICAL,
	"ERROR": logging.ERROR,
	"WARNING": logging.WARNING,
	"INFO": logging.INFO,
	"DEBUG": logging.DEBUG,
	"NOTSET": logging.NOTSET,
}


def setup_logging(
	log_level: str | int = "INFO",
	log_file: Optional[str] = None,
	log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
	"""Configure application logging.

	Parameters:
	- log_level: Log level as string (e.g., "INFO") or int (e.g., logging.INFO)
	- log_file: Optional path to a log file. If provided, a RotatingFileHandler is added.
	- log_format: Formatter pattern for all handlers.
	"""

	# Resolve level
	if isinstance(log_level, str):
		level = _LEVELS.get(log_level.upper(), logging.INFO)
	else:
		level = int(log_level)

	root = logging.getLogger()

	# Avoid duplicate handlers if called multiple times
	if root.handlers:
		for h in list(root.handlers):
			root.removeHandler(h)
			try:
				h.close()
			except Exception:
				pass

	root.setLevel(level)

	formatter = logging.Formatter(log_format)

	# Console handler
	ch = logging.StreamHandler()
	ch.setLevel(level)
	ch.setFormatter(formatter)
	root.addHandler(ch)

	# Optional rotating file handler
	if log_file:
		try:
			fh = logging.handlers.RotatingFileHandler(
				log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
			)
			fh.setLevel(level)
			fh.setFormatter(formatter)
			root.addHandler(fh)
		except Exception as e:
			# Fall back gracefully to console-only logging
			logging.getLogger(__name__).warning(
				f"Failed to attach file handler '{log_file}': {e}"
			)

	# Reduce verbosity of noisy third-party loggers if desired
	for noisy in ("selenium", "urllib3", "matplotlib"):
		logging.getLogger(noisy).setLevel(max(level, logging.WARNING))

