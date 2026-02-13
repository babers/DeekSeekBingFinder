# gui_module.py

# At the top of each module
print(f"Loading {__name__} module") 

# gui_module.py
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator
from threading import Thread
from tkinter import ttk
from tkinter import messagebox
import subprocess
from utils.edge_driver_manager import get_local_driver_version
from utils.network import is_connected
from utils import elapsed_timer
import logging

class GUI:
    def __init__(self, config, data_manager, browser_controller, *args, **kwargs):
        # Accept config for future use; keep a reference even if not used yet
        self.config = config
        self.data_manager = data_manager
        self.browser_controller = browser_controller

        # ensure there's a root window reference the rest of the GUI uses
        # (if your GUI uses a different name, keep that and adapt the var below)
        if not hasattr(self, "root"):
            self.root = tk.Tk()

        # Determine installed WebDriver version (if available)
        self.driver_version = None
        try:
            self.driver_version = get_local_driver_version(self.config.webdriver_path)
        except Exception:
            self.driver_version = None

        base_title = "Bing Search Automator"
        if self.driver_version:
            self.root.title(f"{base_title} (WebDriver {self.driver_version})")
        else:
            self.root.title(base_title)

        self.search_started = False
        self.setup_ui()
        self.schedule_update()
        # Pause timer state
        self._pause_after_id = None
        self._remaining_pause_seconds = 0
        
    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Stats Frame
        stats_frame = ttk.LabelFrame(main_frame, text="Current Status")
        stats_frame.pack(fill=tk.X, pady=5)

        self.total_label = ttk.Label(stats_frame, text="Total Searches: 0")
        self.total_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.rewards_label = ttk.Label(stats_frame, text="Rewards Points: 0")
        self.rewards_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Elapsed time label (updated from utils.elapsed_timer)
        try:
            self.elapsed_label = ttk.Label(stats_frame, text="Elapsed: 00:00:00")
            self.elapsed_label.pack(side=tk.LEFT, padx=10, pady=5)
        except Exception:
            self.elapsed_label = tk.Label(stats_frame, text="Elapsed: 00:00:00")
            self.elapsed_label.pack(side=tk.LEFT, padx=10, pady=5)

    # WebDriver version is shown in the window title only (no extra label here)

        # Control Frame
        control_frame = ttk.LabelFrame(main_frame, text="Controls")
        control_frame.pack(fill=tk.X, pady=5)

        self.start_btn = ttk.Button(
            control_frame,
            text="Start Searching",
            command=self.start_searching,
            width=15
        )
        self.start_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.stop_btn = ttk.Button(
            control_frame,
            text="Stop",
            command=self.stop_searching,
            state=tk.DISABLED,
            width=15
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Topic Frame (below buttons)
        topic_frame = ttk.LabelFrame(main_frame, text="Current Topic")
        topic_frame.pack(fill=tk.X, pady=5)
        self.topic_label = ttk.Label(topic_frame, text="Topic: None")
        self.topic_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Pause Timer Frame
        pause_frame = ttk.LabelFrame(main_frame, text="Pause Timer")
        pause_frame.pack(fill=tk.X, pady=5)
        self.pause_timer_label = ttk.Label(pause_frame, text="")
        self.pause_timer_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Network status indicator
        try:
            # Create a small text-based colored dot (Unicode) and a text label
            self.network_status_frame = tk.Frame(stats_frame, bg=stats_frame.cget('background'))
            # Use a tk.Label for the colored dot so fg/bg reliably change across themes
            self.network_status_dot = tk.Label(self.network_status_frame, text="\u25CF", fg="#808080", bg=stats_frame.cget('background'), font=("Segoe UI", 10))
            self.network_status_dot.pack(side=tk.LEFT)
            self.network_status_label = ttk.Label(self.network_status_frame, text="Network: Unknown")
            self.network_status_label.pack(side=tk.LEFT, padx=(6, 0))
            self.network_status_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        except Exception:
            # fallback - use a simple tk.Label if ttk fails for any reason
            self.network_status_label = tk.Label(stats_frame, text="Network: Unknown")
            self.network_status_label.pack(side=tk.RIGHT, padx=10, pady=5)

        # Progress Frame
        progress_frame = ttk.LabelFrame(main_frame, text="Search Progress")
        progress_frame.pack(expand=True, fill=tk.BOTH, pady=5)

        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Initialize graph with 30 points
        x_init = list(range(1, 31))
        y_init = [0] * 30
        self.ax.plot(x_init, y_init, marker='o', linestyle='-', color='b')
        self.ax.set_ylabel('Rewards Points')
        self.ax.set_title('Searches vs Rewards Points')
        self.ax.grid(True)
        self.ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.canvas.draw()

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Shutdown-on-complete checkbox (default: disabled)
        # This creates a BooleanVar the RewardsWatcher will read via is_shutdown_enabled().
        self.shutdown_var = tk.BooleanVar(value=False)
        self.shutdown_checkbox = tk.Checkbutton(
            self.root,
            text="Shutdown PC when finished",
            variable=self.shutdown_var
        )
        # Place the checkbox — adjust pack/grid options to match your layout
        try:
            # If the GUI uses a frame or a specific layout, you might change this
            self.shutdown_checkbox.pack(anchor="w", padx=8, pady=4)
        except Exception:
            # fallback if pack isn't appropriate in your layout
            pass

    def set_pause_timer(self, seconds):
        """Start or reset the GUI pause countdown safely from any thread."""
        def _start():
            # cancel any existing countdown
            try:
                if getattr(self, "_pause_after_id", None):
                    self.root.after_cancel(self._pause_after_id)
            except Exception:
                pass
            self._pause_after_id = None
            self._remaining_pause_seconds = int(max(0, seconds))
            # kick off the first tick immediately
            self._tick_pause_timer()

        # Schedule on the Tk main loop to stay thread-safe
        self.root.after(0, _start)

    def update_pause_timer(self, seconds):
        """Back-compat: update label once; prefer set_pause_timer for auto ticking."""
        def _update():
            if hasattr(self, 'pause_timer_label'):
                mins, secs = divmod(int(max(0, seconds)), 60)
                self.pause_timer_label.config(text=f"Paused: {mins:02d}:{secs:02d} remaining")
        self.root.after(0, _update)

    def clear_pause_timer(self):
        """Clear the pause countdown and label, safely from any thread."""
        def _clear():
            try:
                if getattr(self, "_pause_after_id", None):
                    self.root.after_cancel(self._pause_after_id)
            except Exception:
                pass
            self._pause_after_id = None
            self._remaining_pause_seconds = 0
            if hasattr(self, 'pause_timer_label'):
                self.pause_timer_label.config(text="")
        self.root.after(0, _clear)

    def _tick_pause_timer(self):
        """Internal: decrement and render countdown; reschedule next tick."""
        # If cleared or finished, stop ticking
        if self._remaining_pause_seconds <= 0:
            if hasattr(self, 'pause_timer_label'):
                self.pause_timer_label.config(text="")
            self._pause_after_id = None
            return
        # Update label
        mins, secs = divmod(int(self._remaining_pause_seconds), 60)
        if hasattr(self, 'pause_timer_label'):
            self.pause_timer_label.config(text=f"Paused: {mins:02d}:{secs:02d} remaining")
        # Decrement and schedule next tick
        self._remaining_pause_seconds -= 1
        self._pause_after_id = self.root.after(1000, self._tick_pause_timer)
    def set_current_topic(self, topic):
        if hasattr(self, 'topic_label'):
            self.topic_label.config(text=f"Topic: {topic}")
        # Update total searches in sync with topic update
        self.update_display()
        
    def start_searching(self):
        if hasattr(self, "data_manager"):
            self.data_manager.reset()
        if hasattr(self, "rewards_watcher"):
            self.rewards_watcher.reset()
        self.search_started = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        # start elapsed timer for the search session
        try:
            elapsed_timer.reset()
            elapsed_timer.start()
            logging.getLogger(__name__).info("Elapsed timer started for search session.")
        except Exception:
            pass
        # Reset rewards watcher shutdown flag if present
        if hasattr(self, "rewards_watcher"):
            self.rewards_watcher.reset()
        Thread(target=self.browser_controller.start_searching, daemon=True).start()
        
    def stop_searching(self):
        self.browser_controller.stop_searching()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        # stop elapsed timer and log elapsed time
        try:
            elapsed = elapsed_timer.stop()
            logging.getLogger(__name__).info(f"Search session stopped by user after {elapsed:.1f} seconds")
            elapsed_timer.reset()
        except Exception:
            pass
        
    def update_display(self):
        counts = self.data_manager.get_current_counts()
        # Show 0 until search started, then show at least 1 after first search
        if self.search_started and counts['total'] == 0:
            total_searches_display = 1
        else:
            total_searches_display = counts['total']
        self.total_label.config(text=f"Total Searches: {total_searches_display}")
        self.rewards_label.config(text=f"Rewards Points: {counts['rewards']}")

        # Update elapsed timer label
        try:
            elapsed = elapsed_timer.get_elapsed()
            hrs, rem = divmod(int(elapsed), 3600)
            mins, secs = divmod(rem, 60)
            if hasattr(self, 'elapsed_label'):
                self.elapsed_label.config(text=f"Elapsed: {hrs:02d}:{mins:02d}:{secs:02d}")
        except Exception:
            pass

        # Plot: X axis = rewards points, Y axis = search number
        self.ax.clear()
        # Use session_search_history from DataManager (list of (index, rewards))
        session_history = getattr(self.data_manager, 'session_search_history', [])
        rewards_points = [item[1] for item in session_history]
        search_indices = [item[0] for item in session_history]
        if rewards_points and search_indices:
            self.ax.plot(rewards_points, search_indices, marker='o', linestyle='-', color='b')
        self.ax.set_xlabel('Rewards Points')
        self.ax.set_ylabel('Search Number')
        self.ax.set_title('Rewards Points vs Searches')
        self.ax.grid(True)
        self.ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.canvas.draw()

    def update_network_status(self):
        """Check connectivity and update the network status label."""
        try:
            online = is_connected()
        except Exception:
            online = False

        text = "Network: Online" if online else "Network: Offline"
        # Schedule UI update on main loop
        def _update():
            try:
                if hasattr(self, 'network_status_label'):
                    self.network_status_label.config(text=text)
                # update colored dot if label available
                if hasattr(self, 'network_status_dot'):
                    color = "#2ecc71" if online else "#e74c3c"
                    try:
                        self.network_status_dot.config(fg=color)
                    except Exception:
                        pass
            except Exception:
                pass

        self.root.after(0, _update)
            
    def schedule_update(self):
        self.update_display()
        # update network status at the same cadence
        self.update_network_status()
        self.root.after(1000, self.schedule_update)
        
    def start(self):
        self.root.mainloop()

    def is_shutdown_enabled(self) -> bool:
        """
        Stable API for external callers (RewardsWatcher).
        Returns True when the shutdown checkbox is checked.
        """
        try:
            return bool(self.shutdown_var.get())
        except Exception:
            return False

    # Compatibility alias
    get_shutdown_enabled = is_shutdown_enabled

    # Removed legacy shutdown confirmation method to avoid unintended prompts at startup.