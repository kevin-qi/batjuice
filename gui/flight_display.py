"""
Flight path display widget using matplotlib.
"""
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading
import time
from collections import defaultdict, deque
from typing import Dict, Any, Optional


class FlightDisplay:
    """Real-time flight path display"""
    
    def __init__(self, parent, gui_config: Dict[str, Any]):
        """
        Initialize flight display
        
        Args:
            parent: Parent tkinter widget
            gui_config: GUI configuration dictionary
        """
        self.parent = parent
        self.gui_config = gui_config
        self.max_points = gui_config.get('max_flight_points', 1000)
        
        # Data storage
        self.flight_data = defaultdict(lambda: {'x': deque(maxlen=self.max_points), 
                                              'y': deque(maxlen=self.max_points),
                                              'z': deque(maxlen=self.max_points),
                                              'timestamps': deque(maxlen=self.max_points)})
        
        # Display control
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        self.selected_bat = tk.StringVar(value="All")
        
        # Colors for different bats
        self.bat_colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        # Setup display
        self._setup_display()
    
    def _setup_display(self):
        """Setup the flight display layout"""
        # Control frame
        control_frame = ttk.Frame(self.parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Bat selection
        ttk.Label(control_frame, text="Display Bat:").pack(side=tk.LEFT)
        self.bat_combobox = ttk.Combobox(control_frame, textvariable=self.selected_bat, width=15)
        self.bat_combobox.pack(side=tk.LEFT, padx=(5, 20))
        
        # View controls
        ttk.Label(control_frame, text="View:").pack(side=tk.LEFT)
        self.view_var = tk.StringVar(value="2D (X-Y)")
        view_combo = ttk.Combobox(control_frame, textvariable=self.view_var, 
                                 values=["2D (X-Y)", "2D (X-Z)", "2D (Y-Z)", "3D"], width=10)
        view_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        # Clear button
        clear_btn = ttk.Button(control_frame, text="Clear Paths", command=self._clear_paths)
        clear_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.fig.patch.set_facecolor('white')
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, self.parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize plot
        self._init_plot()
        
        # Bind events
        self.selected_bat.trace('w', self._on_selection_change)
        self.view_var.trace('w', self._on_view_change)
    
    def _init_plot(self):
        """Initialize the plot"""
        self.ax.clear()
        self.ax.set_xlabel('X (cm)')
        self.ax.set_ylabel('Y (cm)')
        self.ax.set_title('Bat Flight Paths')
        self.ax.grid(True, alpha=0.3)
        
        # Set equal aspect ratio
        self.ax.set_aspect('equal')
        
        # Initial limits
        self.ax.set_xlim(-250, 250)
        self.ax.set_ylim(-250, 250)
        
        self.canvas.draw()
    
    def update_positions(self, bat_states: Dict):
        """Update flight paths with new position data"""
        for bat_id, bat_state in bat_states.items():
            if bat_state.last_position:
                pos = bat_state.last_position
                
                # Add to flight data
                self.flight_data[bat_id]['x'].append(pos.x)
                self.flight_data[bat_id]['y'].append(pos.y)
                self.flight_data[bat_id]['z'].append(pos.z)
                self.flight_data[bat_id]['timestamps'].append(pos.timestamp)
        
        # Update bat selection combobox
        current_bats = list(self.flight_data.keys())
        current_bats.insert(0, "All")
        self.bat_combobox['values'] = current_bats
    
    def start_updates(self):
        """Start update thread"""
        if self.running:
            return
            
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def stop_updates(self):
        """Stop update thread"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)
    
    def _update_loop(self):
        """Update loop for flight display"""
        while self.running:
            try:
                # Schedule update on main thread
                if self.parent.winfo_exists():
                    self.parent.after_idle(self._update_plot)
                time.sleep(1.0)  # Update at 1 Hz
            except Exception as e:
                print(f"Flight display update error: {e}")
                time.sleep(0.2)
    
    def _update_plot(self):
        """Update the plot (called on main thread)"""
        try:
            self.ax.clear()
            
            view_mode = self.view_var.get()
            selected_bat = self.selected_bat.get()
            
            # Setup axes based on view mode
            if view_mode == "2D (X-Y)":
                self.ax.set_xlabel('X (cm)')
                self.ax.set_ylabel('Y (cm)')
            elif view_mode == "2D (X-Z)":
                self.ax.set_xlabel('X (cm)')
                self.ax.set_ylabel('Z (cm)')
            elif view_mode == "2D (Y-Z)":
                self.ax.set_xlabel('Y (cm)')
                self.ax.set_ylabel('Z (cm)')
            
            self.ax.set_title('Bat Flight Paths')
            self.ax.grid(True, alpha=0.3)
            
            # Plot data
            if selected_bat == "All":
                # Plot all bats
                for i, (bat_id, data) in enumerate(self.flight_data.items()):
                    if len(data['x']) > 1:
                        color = self.bat_colors[i % len(self.bat_colors)]
                        self._plot_bat_path(data, bat_id, color, view_mode)
            else:
                # Plot selected bat only
                if selected_bat in self.flight_data:
                    data = self.flight_data[selected_bat]
                    if len(data['x']) > 1:
                        self._plot_bat_path(data, selected_bat, 'blue', view_mode)
            
            # Add legend if multiple bats
            if selected_bat == "All" and len(self.flight_data) > 1:
                self.ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Auto-scale with some padding
            if self.flight_data:
                self._auto_scale_plot(view_mode)
            
            # Use blitting for better performance
            self.canvas.draw_idle()
            
        except Exception as e:
            print(f"Error updating flight plot: {e}")
    
    def _plot_bat_path(self, data: Dict, bat_id: str, color: str, view_mode: str):
        """Plot path for a single bat"""
        x_data = list(data['x'])
        y_data = list(data['y'])
        z_data = list(data['z'])
        
        if view_mode == "2D (X-Y)":
            plot_x, plot_y = x_data, y_data
        elif view_mode == "2D (X-Z)":
            plot_x, plot_y = x_data, z_data
        elif view_mode == "2D (Y-Z)":
            plot_x, plot_y = y_data, z_data
        else:
            plot_x, plot_y = x_data, y_data  # Default to X-Y
        
        # Plot trail (fading effect)
        if len(plot_x) > 1:
            # Recent points are more opaque
            for i in range(1, len(plot_x)):
                alpha = 0.1 + 0.9 * (i / len(plot_x))
                self.ax.plot(plot_x[i-1:i+1], plot_y[i-1:i+1], 
                           color=color, alpha=alpha, linewidth=1)
            
            # Current position marker
            self.ax.plot(plot_x[-1], plot_y[-1], 'o', color=color, 
                        markersize=8, label=bat_id, markeredgecolor='black', markeredgewidth=1)
    
    def _auto_scale_plot(self, view_mode: str):
        """Auto-scale the plot based on data"""
        all_x, all_y = [], []
        
        for data in self.flight_data.values():
            if view_mode == "2D (X-Y)":
                all_x.extend(data['x'])
                all_y.extend(data['y'])
            elif view_mode == "2D (X-Z)":
                all_x.extend(data['x'])
                all_y.extend(data['z'])
            elif view_mode == "2D (Y-Z)":
                all_x.extend(data['y'])
                all_y.extend(data['z'])
        
        if all_x and all_y:
            x_min, x_max = min(all_x), max(all_x)
            y_min, y_max = min(all_y), max(all_y)
            
            # Add padding
            x_padding = (x_max - x_min) * 0.1 or 10
            y_padding = (y_max - y_min) * 0.1 or 10
            
            self.ax.set_xlim(x_min - x_padding, x_max + x_padding)
            self.ax.set_ylim(y_min - y_padding, y_max + y_padding)
    
    def _clear_paths(self):
        """Clear all flight paths"""
        self.flight_data.clear()
        self._init_plot()
    
    def _on_selection_change(self, *args):
        """Handle bat selection change"""
        self._update_plot()
    
    def _on_view_change(self, *args):
        """Handle view mode change"""
        self._update_plot()