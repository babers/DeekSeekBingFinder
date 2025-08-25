# gui_module.py

# At the top of each module
print(f"Loading {__name__} module") 

# gui_module.py
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from threading import Thread
from tkinter import ttk
from tkinter import messagebox
import subprocess
from utils.edge_driver_manager import get_local_driver_version

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
        self.ax.set_xlabel('Search Number')
        self.ax.set_ylabel('Rewards Points')
        self.ax.set_title('Searches vs Rewards Points')
        self.ax.grid(True)
        from matplotlib.ticker import MaxNLocator
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
        if hasattr(self, 'pause_timer_label'):
            mins, secs = divmod(seconds, 60)
            self.pause_timer_label.config(text=f"Paused: {mins:02d}:{secs:02d} remaining")

    def update_pause_timer(self, seconds):
        if hasattr(self, 'pause_timer_label'):
            mins, secs = divmod(seconds, 60)
            self.pause_timer_label.config(text=f"Paused: {mins:02d}:{secs:02d} remaining")

    def clear_pause_timer(self):
        if hasattr(self, 'pause_timer_label'):
            self.pause_timer_label.config(text="")
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
        # Reset rewards watcher shutdown flag if present
        if hasattr(self, "rewards_watcher"):
            self.rewards_watcher.reset()
        Thread(target=self.browser_controller.start_searching, daemon=True).start()
        
    def stop_searching(self):
        self.browser_controller.stop_searching()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
    def update_display(self):
        counts = self.data_manager.get_current_counts()
        # Show 0 until search started, then show at least 1 after first search
        if self.search_started and counts['total'] == 0:
            total_searches_display = 1
        else:
            total_searches_display = counts['total']
        self.total_label.config(text=f"Total Searches: {total_searches_display}")
        self.rewards_label.config(text=f"Rewards Points: {counts['rewards']}")

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
        from matplotlib.ticker import MaxNLocator
        self.ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        self.canvas.draw()
            
    def schedule_update(self):
        self.update_display()
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