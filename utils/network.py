import socket
import logging
import time
from typing import Optional


def is_connected(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
    """Quick TCP-connect check to determine if we have network connectivity.

    Tries to open a socket to a well-known DNS server (Google DNS by default).
    Returns True when the connect succeeds, False otherwise.
    This avoids extra dependencies and is firewall-friendly for basic checks.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except Exception:
        return False


def wait_for_connection(retry_seconds: int = 5, logger: Optional[logging.Logger] = None):
    """Block until network connectivity is available. Logs status if logger provided."""
    log = logger or logging.getLogger(__name__)
    while True:
        if is_connected():
            log.info("Network connectivity established.")
            return
        log.warning(f"No internet connectivity detected. Retrying in {retry_seconds} seconds...")
        time.sleep(retry_seconds)
