# gui_module.py

# At the top of each module
print(f"Loading {__name__} module") 

# gui_module.py
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from threading import Thread
from tkinter import ttk

class GUI:
    def __init__(self, data_manager, browser_controller):
        self.data_manager = data_manager
        self.browser_controller = browser_controller
        self.root = tk.Tk()
        self.root.title("Bing Search Automator")
        
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

        # Progress Frame
        progress_frame = ttk.LabelFrame(main_frame, text="Search Progress")
        progress_frame.pack(expand=True, fill=tk.BOTH, pady=5)

        fig = Figure(figsize=(6, 4), dpi=100)
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(fig, master=progress_frame)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    def set_current_topic(self, topic):
        if hasattr(self, 'topic_label'):
            self.topic_label.config(text=f"Topic: {topic}")
        
    def start_searching(self):
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        Thread(target=self.browser_controller.start_searching, daemon=True).start()
        
    def stop_searching(self):
        self.browser_controller.stop_searching()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
    def update_display(self):
        counts = self.data_manager.get_current_counts()
        self.total_label.config(text=f"Total Searches: {counts['total']}")
        self.rewards_label.config(text=f"Rewards Points: {counts['rewards']}")
        
        # Update graph: X axis = rewards points, Y axis = searches completed
        self.ax.clear()
        # Use search_history to get actual rewards values
        data = self.data_manager.search_history
        if data:
            rewards = [entry['rewards'] for entry in data]
            counts = list(range(1, len(rewards) + 1))
            self.ax.plot(rewards, counts, marker='o', linestyle='-', color='b')
            self.ax.set_xlabel('Rewards Points')
            self.ax.set_ylabel('Searches Completed')
            self.ax.grid(True)
            # Set X and Y axes to use integer ticks only
            from matplotlib.ticker import MaxNLocator
            self.ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            # Set X axis to start at 0 and auto-adjust max
            min_x = 0
            max_x = max(rewards) if rewards else 10
            self.ax.set_xlim(left=min_x, right=max_x + 10)
            # Set Y axis to start at 0 and auto-adjust max
            min_y = 0
            max_y = max(counts) if counts else 10
            self.ax.set_ylim(bottom=min_y, top=max_y + 10)
            self.canvas.draw()
            
    def schedule_update(self):
        self.update_display()
        self.root.after(1000, self.schedule_update)
        
    def start(self):
        self.root.mainloop()