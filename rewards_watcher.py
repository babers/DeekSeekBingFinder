import logging
import platform
import subprocess
import threading
import time
import tkinter as tk
from enum import Enum
from typing import Optional

from config import Config
from data_manager import DataManager

class WatcherState(Enum):
    IDLE = "idle"
    MONITORING = "monitoring"
    SHUTDOWN_PENDING = "shutdown_pending"
    SHUTDOWN_CANCELLED = "shutdown_cancelled"

class RewardsWatcher:
    def __init__(self, config: Config, data_manager: DataManager, gui: Optional[object] = None):
        self.config = config
        self.data_manager = data_manager
        self.gui = gui
        self.logger = logging.getLogger(__name__)
        
        self.state = WatcherState.IDLE
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.logger.info("RewardsWatcher initialized.")

    def start(self):
        if not self._thread.is_alive():
            self.state = WatcherState.MONITORING
            self._thread.start()
            self.logger.info("RewardsWatcher started.")

    def stop(self, timeout: float = 2.0):
        self.state = WatcherState.IDLE
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self.logger.info("RewardsWatcher stopped.")

    def _gui_shutdown_enabled(self) -> bool:
        if not self.gui:
            return False
        try:
            return self.gui.is_shutdown_enabled()
        except Exception as e:
            self.logger.error(f"Error checking GUI shutdown status: {e}")
            return False

    def _run(self):
        while not self._stop_event.is_set():
            if self.state == WatcherState.MONITORING:
                rewards_complete = self.data_manager.rewards_completed
                loop_complete = self.data_manager.loop_completed
                shutdown_enabled = self._gui_shutdown_enabled()

                self.logger.debug(
                    f"State: {self.state}, Rewards: {rewards_complete}, "
                    f"Loop: {loop_complete}, Shutdown Enabled: {shutdown_enabled}"
                )

                if rewards_complete and loop_complete and shutdown_enabled:
                    self._transition_to_shutdown_pending()
            
            time.sleep(self.config.poll_interval)

    def _transition_to_shutdown_pending(self):
        self.logger.info("Conditions met, transitioning to SHUTDOWN_PENDING.")
        self.state = WatcherState.SHUTDOWN_PENDING
        if hasattr(self.gui, "root"):
            self.gui.root.after(0, self._show_shutdown_dialog)
        else:
            self._execute_shutdown()

    def _show_shutdown_dialog(self):
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("System Shutdown Scheduled")
        dialog.geometry("440x260")
        dialog.configure(bg="#f5f5f5")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        header = tk.Label(dialog, text="⚠️ Scheduled Shutdown", font=("Segoe UI", 16, "bold"), fg="#d9534f", bg="#f5f5f5")
        header.pack(pady=(18, 6))

        msg = tk.Label(dialog, text="Your system will automatically shutdown in 60 seconds.\nClick the button below to cancel.", font=("Segoe UI", 12), fg="#333", bg="#f5f5f5", justify="center")
        msg.pack(pady=(0, 10))

        countdown_var = tk.StringVar(value="60")
        countdown_frame = tk.Frame(dialog, bg="#f5f5f5")
        countdown_frame.pack(pady=(0, 10))
        
        tk.Label(countdown_frame, text="Time remaining:", font=("Segoe UI", 11), fg="#555", bg="#f5f5f5").pack(side="left")
        tk.Label(countdown_frame, textvariable=countdown_var, font=("Segoe UI", 14, "bold"), fg="#d9534f", bg="#f5f5f5", width=4).pack(side="left", padx=(8, 0))

        def cancel_shutdown():
            self.logger.info("Shutdown cancelled by user.")
            self.state = WatcherState.SHUTDOWN_CANCELLED
            dialog.destroy()

        cancel_btn = tk.Button(dialog, text="Cancel Shutdown", command=cancel_shutdown, font=("Segoe UI", 12, "bold"), bg="#5bc0de", fg="white", activebackground="#31b0d5", activeforeground="white", relief="raised", bd=2, cursor="hand2", width=20)
        cancel_btn.pack(pady=(18, 24))

        def countdown(secs):
            if self.state != WatcherState.SHUTDOWN_PENDING:
                return
            countdown_var.set(str(secs))
            if secs > 0:
                dialog.after(1000, countdown, secs - 1)
            else:
                dialog.destroy()
                if self.state == WatcherState.SHUTDOWN_PENDING:
                    self._execute_shutdown()

        countdown(60)

    def _execute_shutdown(self):
        self.logger.info("Executing system shutdown.")
        system = platform.system().lower()
        try:
            if system.startswith("win"):
                subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
            elif system.startswith("linux") or system.startswith("darwin"):
                subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
            else:
                self.logger.warning(f"Unsupported platform for shutdown: {system}")
        except Exception as e:
            self.logger.error(f"Failed to execute shutdown: {e}")

    def reset(self):
        self.logger.info("Resetting watcher state to MONITORING.")
        self.state = WatcherState.MONITORING