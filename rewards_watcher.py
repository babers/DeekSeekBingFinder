import threading
import time
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox
from typing import Optional

class RewardsWatcher:
    """
    Background watcher that polls the data_manager for:
      - rewards completion (various candidate names checked)
      - loop completion (various candidate names checked)

    When both are detected and the GUI indicates shutdown is enabled, schedules a shutdown.
    """

    def __init__(self, data_manager, gui: Optional[object] = None, poll_interval: float = 5.0):
        self.data_manager = data_manager
        self.gui = gui
        self.poll_interval = float(poll_interval)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._shutdown_scheduled = False

    def start(self):
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self, timeout: float = 2.0):
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _call_or_get_bool(self, obj, candidates):
        for name in candidates:
            if hasattr(obj, name):
                val = getattr(obj, name)
                try:
                    if callable(val):
                        return bool(val())
                    return bool(val)
                except Exception:
                    continue
        return False

    def _gui_shutdown_enabled(self) -> bool:
        # Prefer the stable GUI API if available
        if not self.gui:
            return False

        try:
            is_shutdown = getattr(self.gui, "is_shutdown_enabled", None)
            if callable(is_shutdown):
                return bool(is_shutdown())
        except Exception:
            pass

        # Fallback to previous heuristics if GUI does not expose the stable API
        enabled = self._call_or_get_bool(self.gui, [
            "shutdown_on_complete", "shutdown_checkbox_enabled",
            "shutdown_enabled", "get_shutdown_enabled"
        ])
        if enabled:
            return True

        # also try common tkinter variable patterns: gui.shutdown_var.get()
        if hasattr(self.gui, "shutdown_var"):
            var = getattr(self.gui, "shutdown_var")
            try:
                return bool(var.get())
            except Exception:
                try:
                    return bool(var)
                except Exception:
                    pass

        # try attribute directly named 'shutdown' or 'shutdown_checkbox'
        enabled = self._call_or_get_bool(self.gui, ["shutdown", "shutdown_checkbox"])
        return enabled

    def _run(self):
        while not self._stop_event.is_set():
            rewards_complete = getattr(self.data_manager, "rewards_completed", False)
            loop_complete = getattr(self.data_manager, "loop_completed", False)
            shutdown_enabled = self._gui_shutdown_enabled()
            print(f"[Watcher] rewards_complete={rewards_complete}, loop_complete={loop_complete}, shutdown_enabled={shutdown_enabled}, shutdown_scheduled={self._shutdown_scheduled}")

            # If shutdown checkbox is disabled, always allow shutdown to be retried
            if not shutdown_enabled:
                if self._shutdown_scheduled:
                    print("[Watcher] Shutdown checkbox disabled, resetting shutdown_scheduled to False.")
                self._shutdown_scheduled = False

            if rewards_complete and loop_complete and shutdown_enabled and not self._shutdown_scheduled:
                self._schedule_shutdown()

            time.sleep(self.poll_interval)

    def _schedule_shutdown(self):
        print("DEBUG: Entered _schedule_shutdown()")
        self._shutdown_scheduled = True
        print("RewardsWatcher: scheduling system shutdown (60s delay).")
        # Start the cancellation dialog in the GUI thread
        if hasattr(self.gui, "root"):
            self.gui.root.after(0, self._show_shutdown_dialog)
        else:
            # Fallback: run shutdown immediately if no GUI root
            self._execute_shutdown()

    def _show_shutdown_dialog(self):
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("System Shutdown Scheduled")
        dialog.geometry("440x260")
        dialog.configure(bg="#f5f5f5")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Disable close button

        # Header
        header = tk.Label(dialog, text="⚠️ Scheduled Shutdown", font=("Segoe UI", 16, "bold"), fg="#d9534f", bg="#f5f5f5")
        header.pack(pady=(18, 6))

        # Message
        msg = tk.Label(
            dialog,
            text="Your system will automatically shutdown in 60 seconds.\nClick the button below to cancel.",
            font=("Segoe UI", 12),
            fg="#333",
            bg="#f5f5f5",
            justify="center"
        )
        msg.pack(pady=(0, 10))

        # Countdown
        countdown_var = tk.StringVar(value="60")
        countdown_frame = tk.Frame(dialog, bg="#f5f5f5")
        countdown_frame.pack(pady=(0, 10))
        countdown_label = tk.Label(
            countdown_frame,
            text="Time remaining:",
            font=("Segoe UI", 11),
            fg="#555",
            bg="#f5f5f5"
        )
        countdown_label.pack(side="left")
        countdown_time = tk.Label(
            countdown_frame,
            textvariable=countdown_var,
            font=("Segoe UI", 14, "bold"),
            fg="#d9534f",
            bg="#f5f5f5",
            width=4
        )
        countdown_time.pack(side="left", padx=(8, 0))

        # Cancel button
        cancel_flag = {"cancelled": False}

        def cancel_shutdown():
            cancel_flag["cancelled"] = True
            dialog.destroy()
            print("Shutdown cancelled by user.")

        cancel_btn = tk.Button(
            dialog,
            text="Cancel Shutdown",
            command=cancel_shutdown,
            font=("Segoe UI", 12, "bold"),
            bg="#5bc0de",
            fg="white",
            activebackground="#31b0d5",
            activeforeground="white",
            relief="raised",
            bd=2,
            cursor="hand2",
            width=20
        )
        cancel_btn.pack(pady=(18, 24))

        # Add a subtle border
        dialog.update_idletasks()
        dialog.after(100, lambda: dialog.configure(highlightbackground="#d9d9d9", highlightthickness=1))

        def countdown(secs):
            if cancel_flag["cancelled"]:
                return
            countdown_var.set(str(secs))
            if secs > 0:
                dialog.after(1000, countdown, secs - 1)
            else:
                dialog.destroy()
                if not cancel_flag["cancelled"]:
                    self._execute_shutdown()

        countdown(60)

    def _execute_shutdown(self):
        system = platform.system().lower()
        print(f"DEBUG: platform.system().lower() returned '{system}'")
        try:
            if system.startswith("win"):
                print("RewardsWatcher: Running Windows shutdown command...")
                result = subprocess.run(["shutdown", "/s", "/t", "0"], capture_output=True, text=True)
                print(f"Shutdown command result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}")
            elif system.startswith("linux") or system.startswith("darwin"):
                print("RewardsWatcher: Running Unix shutdown command...")
                try:
                    result = subprocess.run(["shutdown", "-h", "now"], capture_output=True, text=True)
                    print(f"Shutdown command result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}")
                except Exception:
                    result = subprocess.run(["sudo", "shutdown", "-h", "now"], capture_output=True, text=True)
                    print(f"Shutdown command result: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}")
            else:
                print("RewardsWatcher: unknown platform, cannot schedule shutdown automatically.")
        except Exception as exc:
            print("RewardsWatcher: failed to schedule shutdown:", exc)

    def reset(self):
        """Reset shutdown state so watcher can trigger again after a new search."""
        self._shutdown_scheduled = False