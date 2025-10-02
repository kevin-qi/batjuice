"""
Real-time 2D flight path display widget using matplotlib Line2D for performance.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle, Circle
import threading
import time
from collections import deque
from typing import Dict, Any, Optional


class FlightDisplay2D:
    """Real-time 2D flight path display with Line2D for maximum performance"""

    def __init__(self, parent, gui_config: Dict[str, Any], room_config: Dict[str, Any],
                 feeder_configs: list, data_manager):
        """
        Initialize 2D flight display

        Args:
            parent: Parent tkinter widget
            gui_config: GUI configuration dictionary
            room_config: Room configuration with bounds
            feeder_configs: List of feeder configurations
            data_manager: FlightDataManager instance for shared data
        """
        self.parent = parent
        self.gui_config = gui_config
        self.room_config = room_config
        self.feeder_configs = feeder_configs
        self.data_manager = data_manager

        # Display control
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        self.selected_bat = tk.StringVar(value="All")
        self.view_plane = tk.StringVar(value="XY")  # XY, XZ, or YZ
        self.show_trigger_radius = tk.BooleanVar(value=True)
        self.show_reactivation_radius = tk.BooleanVar(value=False)
        self.show_labels = tk.BooleanVar(value=True)

        # Colors for different bats (same as 3D display)
        self.bat_colors = [
            '#00FFFF',  # Cyan
            '#FF00FF',  # Magenta
            '#FFFF00',  # Yellow
            '#0080FF',  # Blue
            '#FF6600',  # Orange
            '#9900FF',  # Purple
            '#00FF00',  # Lime green
            '#FF0080'   # Rose/pink
        ]

        # Static elements tracking
        self.static_elements_drawn = False
        self.feeder_patches = []  # Track feeder rectangles/circles
        self.feeder_text_elements = []  # Track text labels

        # Performance monitoring
        self.frame_times = deque(maxlen=30)
        self.last_frame_time = time.time()
        self.fps_text = None

        # High-performance plotting with single Line2D per bat
        self.bat_lines = {}  # bat_id -> Line2D object
        self.bat_scatter_artists = []  # Current position markers

        # Setup display
        self._setup_display()

    def _setup_display(self):
        """Setup the 2D flight display layout"""
        # Control frame
        control_frame = ttk.Frame(self.parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # View plane selection with radio buttons
        ttk.Label(control_frame, text="View:").pack(side=tk.LEFT, padx=(0, 5))
        view_frame = ttk.Frame(control_frame)
        view_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Radiobutton(view_frame, text="XY", variable=self.view_plane, value="XY").pack(side=tk.LEFT)
        ttk.Radiobutton(view_frame, text="XZ", variable=self.view_plane, value="XZ").pack(side=tk.LEFT)
        ttk.Radiobutton(view_frame, text="YZ", variable=self.view_plane, value="YZ").pack(side=tk.LEFT)

        # Clear button
        clear_btn = ttk.Button(control_frame, text="Clear Paths", command=self._clear_paths_with_confirmation)
        clear_btn.pack(side=tk.LEFT, padx=(5, 20))

        # Toggle controls
        ttk.Label(control_frame, text="Show:").pack(side=tk.LEFT)

        trigger_check = ttk.Checkbutton(control_frame, text="Trigger Radius",
                                        variable=self.show_trigger_radius,
                                        command=self._toggle_display)
        trigger_check.pack(side=tk.LEFT, padx=(5, 5))

        reactivation_check = ttk.Checkbutton(control_frame, text="Reactivation Radius",
                                             variable=self.show_reactivation_radius,
                                             command=self._toggle_display)
        reactivation_check.pack(side=tk.LEFT, padx=(5, 5))

        label_check = ttk.Checkbutton(control_frame, text="Labels",
                                      variable=self.show_labels,
                                      command=self._toggle_display)
        label_check.pack(side=tk.LEFT, padx=(5, 5))

        # Bat selection list frame (below controls)
        bat_selection_frame = ttk.LabelFrame(self.parent, text="Display Bat", padding=5)
        bat_selection_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Create scrollable list for bat selection
        bat_list_container = ttk.Frame(bat_selection_frame)
        bat_list_container.pack(fill=tk.BOTH, expand=True)
        
        self.bat_listbox = tk.Listbox(bat_list_container, height=3, 
                                      selectmode=tk.SINGLE, exportselection=False,
                                      bg='#2B2D31', fg='#DCDDDE', 
                                      selectbackground='#5865F2', selectforeground='white')
        self.bat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        bat_scrollbar = ttk.Scrollbar(bat_list_container, orient=tk.VERTICAL, 
                                      command=self.bat_listbox.yview)
        bat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.bat_listbox.config(yscrollcommand=bat_scrollbar.set)
        
        # Initialize with "All"
        self.bat_listbox.insert(tk.END, "All")
        self.bat_listbox.selection_set(0)
        
        # Bind selection event
        self.bat_listbox.bind('<<ListboxSelect>>', self._on_bat_list_select)

        # Matplotlib 2D figure - dark theme
        self.fig, self.ax = plt.subplots(figsize=(7, 7))

        # Dark theme colors
        bg_color = '#2B2D31'
        text_color = '#DCDDDE'

        self.fig.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)

        # Reduce white space
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)

        # Grid styling - hide axis lines at origin to prevent horizontal/vertical lines
        self.ax.grid(True, color='#606060', alpha=0.15, linestyle='-', linewidth=0.3)
        self.ax.axhline(y=0, color='#606060', alpha=0.15, linewidth=0.3)  # Match grid style
        self.ax.axvline(x=0, color='#606060', alpha=0.15, linewidth=0.3)  # Match grid style

        # Axis styling
        self.ax.spines['bottom'].set_color(text_color)
        self.ax.spines['top'].set_color(text_color)
        self.ax.spines['left'].set_color(text_color)
        self.ax.spines['right'].set_color(text_color)

        # Tick colors
        self.ax.tick_params(axis='x', colors=text_color)
        self.ax.tick_params(axis='y', colors=text_color)

        # Create canvas
        canvas_frame = ttk.Frame(self.parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = FigureCanvasTkAgg(self.fig, canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add navigation toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, canvas_frame)
        toolbar.update()

        # Initialize plot
        self._init_plot()

        # Bind events
        self.view_plane.trace('w', self._on_view_change)

    def _init_plot(self):
        """Initialize the 2D plot"""
        self._draw_static_elements()
        self.static_elements_drawn = True
        self.canvas.draw()

    def _draw_static_elements(self):
        """Draw static room elements"""
        # Clear old patches
        for patch in self.feeder_patches:
            try:
                patch.remove()
            except:
                pass
        self.feeder_patches.clear()

        for text_elem in self.feeder_text_elements:
            try:
                text_elem.remove()
            except:
                pass
        self.feeder_text_elements.clear()

        # Get current view plane
        view = self.view_plane.get()

        # Set labels and bounds based on view plane
        text_color = '#DCDDDE'
        bounds = self.room_config.get('bounds', {})

        if view == "XY":
            self.ax.set_xlabel('X (m)', color=text_color)
            self.ax.set_ylabel('Y (m)', color=text_color)
            axis1_min, axis1_max = bounds.get('x_min', -3), bounds.get('x_max', 3)
            axis2_min, axis2_max = bounds.get('y_min', -3), bounds.get('y_max', 3)
        elif view == "XZ":
            self.ax.set_xlabel('X (m)', color=text_color)
            self.ax.set_ylabel('Z (m)', color=text_color)
            axis1_min, axis1_max = bounds.get('x_min', -3), bounds.get('x_max', 3)
            axis2_min, axis2_max = bounds.get('z_min', 0), bounds.get('z_max', 3)
        else:  # YZ
            self.ax.set_xlabel('Y (m)', color=text_color)
            self.ax.set_ylabel('Z (m)', color=text_color)
            axis1_min, axis1_max = bounds.get('y_min', -3), bounds.get('y_max', 3)
            axis2_min, axis2_max = bounds.get('z_min', 0), bounds.get('z_max', 3)

        self.ax.set_xlim(axis1_min, axis1_max)
        self.ax.set_ylim(axis2_min, axis2_max)

        # Equal aspect ratio
        self.ax.set_aspect('equal')

        # Draw room boundary
        self.ax.plot([axis1_min, axis1_max, axis1_max, axis1_min, axis1_min],
                     [axis2_min, axis2_min, axis2_max, axis2_max, axis2_min],
                     color='#6B7280', alpha=0.5, linewidth=1.5)

        # Draw feeders
        self._draw_feeders()

    def _draw_feeders(self):
        """Draw feeder positions"""
        view = self.view_plane.get()

        for feeder in self.feeder_configs:
            x, y, z = feeder.get_current_position()
            size = 0.15  # 30cm square, half-size

            # Get 2D coordinates based on view plane
            if view == "XY":
                axis1, axis2 = x, y
            elif view == "XZ":
                axis1, axis2 = x, z
            else:  # YZ
                axis1, axis2 = y, z

            # Draw feeder square
            rect = Rectangle((axis1-size, axis2-size), 2*size, 2*size,
                           facecolor='#CC7000', edgecolor='#D97E00',
                           alpha=0.6, linewidth=1.0)
            self.ax.add_patch(rect)
            self.feeder_patches.append(rect)

            # Add label if enabled
            if self.show_labels.get():
                text_elem = self.ax.text(axis1, axis2, f'F{feeder.feeder_id}',
                                       ha='center', va='center',
                                       color='white', fontsize=8, fontweight='normal')
                self.feeder_text_elements.append(text_elem)

            # Trigger radius circle
            if self.show_trigger_radius.get():
                circle = Circle((axis1, axis2), feeder.activation_radius,
                              facecolor='none', edgecolor='#708090',
                              alpha=0.3, linewidth=1.5)
                self.ax.add_patch(circle)
                self.feeder_patches.append(circle)

            # Reactivation radius circle
            if self.show_reactivation_radius.get():
                circle = Circle((axis1, axis2), feeder.reactivation_distance,
                              facecolor='none', edgecolor='#708090',
                              alpha=0.3, linewidth=1.5, linestyle='--')
                self.ax.add_patch(circle)
                self.feeder_patches.append(circle)

    def update_feeder_positions(self, updated_feeder_configs):
        """Update feeder positions in the display"""
        self.feeder_configs = updated_feeder_configs
        self.static_elements_drawn = False

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
        """Update loop for flight display at 10 Hz"""
        while self.running:
            try:
                # Schedule update on main thread
                if self.parent.winfo_exists():
                    self.parent.after_idle(self._update_plot)
                time.sleep(0.1)  # 10 Hz
            except Exception as e:
                import traceback
                print(f"2D display update error: {e}")
                traceback.print_exc()
                time.sleep(0.1)

    def _update_plot(self):
        """Update the 2D plot (called on main thread)"""
        try:
            # Performance monitoring
            current_time = time.time()
            if self.last_frame_time:
                frame_time = current_time - self.last_frame_time
                self.frame_times.append(frame_time)
            self.last_frame_time = current_time

            # Redraw static elements if needed
            if not self.static_elements_drawn:
                self._draw_static_elements()
                self.static_elements_drawn = True

            # Clear dynamic elements (scatter points)
            for artist in self.bat_scatter_artists:
                try:
                    artist.remove()
                except:
                    pass
            self.bat_scatter_artists.clear()

            # Get data snapshot (thread-safe)
            flight_data = self.data_manager.get_snapshot()

            # Update bat listbox
            current_bats = list(flight_data.keys())
            current_bats.insert(0, "All")
            
            # Get current selection
            current_selection = self.bat_listbox.curselection()
            selected_value = self.bat_listbox.get(current_selection[0]) if current_selection else "All"
            
            # Update listbox contents
            self.bat_listbox.delete(0, tk.END)
            for bat in current_bats:
                self.bat_listbox.insert(tk.END, bat)
            
            # Restore selection
            try:
                idx = current_bats.index(selected_value)
                self.bat_listbox.selection_set(idx)
            except (ValueError, tk.TclError):
                # If previously selected bat no longer exists, select "All"
                self.bat_listbox.selection_set(0)
                self.selected_bat.set("All")

            # Plot bat paths
            selected_bat = self.selected_bat.get()

            if selected_bat == "All":
                # Plot all bats with distinct colors
                for i, (bat_id, data) in enumerate(flight_data.items()):
                    if len(data['x']) > 1:
                        color = self.bat_colors[i % len(self.bat_colors)]
                        self._plot_bat_path_2d(data, bat_id, color)
            else:
                # Plot in two passes: grey bats first, then highlighted bat on top
                highlight_color = '#FF00FF'
                grey_color = '#606060'

                # FIRST PASS: Plot unselected bats in grey (bottom layer)
                for bat_id, data in flight_data.items():
                    if len(data['x']) > 1 and bat_id != selected_bat:
                        self._plot_bat_path_2d(data, bat_id, grey_color)

                # SECOND PASS: Plot selected bat highlighted (top layer)
                if selected_bat in flight_data:
                    data = flight_data[selected_bat]
                    if len(data['x']) > 1:
                        self._plot_bat_path_2d(data, selected_bat, highlight_color)

            # Add legend
            if selected_bat == "All" and len(flight_data) > 1:
                if self.ax.get_legend():
                    self.ax.get_legend().remove()

                legend_elements = []
                from matplotlib.lines import Line2D
                for i, bat_id in enumerate(flight_data.keys()):
                    color = self.bat_colors[i % len(self.bat_colors)]
                    legend_elements.append(Line2D([0], [0], color=color, lw=2, label=bat_id))

                if legend_elements:
                    self.ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')

            # Add FPS counter
            self._draw_fps_counter()

            # Redraw
            self.canvas.draw_idle()

        except Exception as e:
            import traceback
            print(f"Error updating 2D flight plot: {e}")
            traceback.print_exc()

    def _plot_bat_path_2d(self, data: Dict, bat_id: str, color: str):
        """Plot bat flight path in 2D using Line2D for maximum performance"""
        view = self.view_plane.get()

        # Get appropriate data based on view plane
        if view == "XY":
            axis1_data = list(data['x'])
            axis2_data = list(data['y'])
        elif view == "XZ":
            axis1_data = list(data['x'])
            axis2_data = list(data['z'])
        else:  # YZ
            axis1_data = list(data['y'])
            axis2_data = list(data['z'])

        if len(axis1_data) < 1:
            return

        # Remove old line for this bat if it exists
        if bat_id in self.bat_lines:
            try:
                self.bat_lines[bat_id].remove()
            except:
                pass
            del self.bat_lines[bat_id]

        # Plot trajectory if we have at least 2 points
        if len(axis1_data) > 1:
            # Check if grey (for opacity)
            import matplotlib.colors as mcolors
            if isinstance(color, str):
                color_rgb = mcolors.to_rgb(color)
            else:
                color_rgb = color

            is_grey = (color_rgb[0] == color_rgb[1] == color_rgb[2])
            alpha = 0.4 if is_grey else 0.8
            linewidth = 2.0 if is_grey else 2.5

            # Create Line2D using ax.plot (fastest method)
            line, = self.ax.plot(axis1_data, axis2_data,
                                color=color,
                                alpha=alpha,
                                linewidth=linewidth,
                                solid_capstyle='round',
                                solid_joinstyle='round')
            self.bat_lines[bat_id] = line

        # Current position marker (always show if we have data)
        if len(axis1_data) > 0 and len(axis2_data) > 0:
            scatter = self.ax.scatter([axis1_data[-1]], [axis2_data[-1]],
                                    c=[color], s=120, alpha=1.0,
                                    edgecolors='#2B2D31', linewidth=2.5, marker='o')
            self.bat_scatter_artists.append(scatter)

    def _draw_fps_counter(self):
        """Draw FPS counter"""
        if len(self.frame_times) > 5:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0

            # Get total points
            total_points = sum(self.data_manager.get_data_length(bat_id)
                             for bat_id in self.data_manager.get_bat_ids())

            # Remove old text
            if self.fps_text:
                try:
                    self.fps_text.remove()
                except:
                    pass

            perf_text = f'FPS: {fps:.1f} | Points: {total_points:,}'
            self.fps_text = self.ax.text(0.02, 0.98, perf_text,
                                        transform=self.ax.transAxes,
                                        fontsize=10, color='#DCDDDE',
                                        bbox=dict(boxstyle='round,pad=0.3',
                                                facecolor='#2B2D31', alpha=0.7,
                                                edgecolor='#4A5568'))

    def _clear_paths_with_confirmation(self):
        """Clear all flight paths with confirmation"""
        if messagebox.askyesno("Clear Paths", "Are you sure you want to clear all flight paths?"):
            self._clear_paths()

    def _clear_paths(self):
        """Clear all flight paths"""
        # Clear data manager (shared data)
        self.data_manager.clear()

        # Clear local line objects
        for bat_id, line in self.bat_lines.items():
            try:
                line.remove()
            except:
                pass
        self.bat_lines.clear()

        # Force redraw
        self.static_elements_drawn = False
        self.canvas.draw()

    def _toggle_display(self):
        """Handle toggle changes"""
        self.static_elements_drawn = False

    def _on_selection_change(self, *args):
        """Handle bat selection change"""
        # Clear all line objects to force replot with new colors
        for bat_id, line in self.bat_lines.items():
            try:
                line.remove()
            except:
                pass
        self.bat_lines.clear()

    def _on_bat_list_select(self, event):
        """Handle bat selection from listbox"""
        selection = self.bat_listbox.curselection()
        if selection:
            selected_bat = self.bat_listbox.get(selection[0])
            self.selected_bat.set(selected_bat)
            
            # Clear all line objects to force replot with new colors
            for bat_id, line in self.bat_lines.items():
                try:
                    line.remove()
                except:
                    pass
            self.bat_lines.clear()

    def _on_view_change(self, *args):
        """Handle view plane change"""
        # Clear all line objects to force replot with new projection
        for bat_id, line in self.bat_lines.items():
            try:
                line.remove()
            except:
                pass
        self.bat_lines.clear()

        # Redraw static elements with new axis labels and bounds
        self._draw_static_elements()
        self.static_elements_drawn = True

        # Force canvas redraw
        self.canvas.draw()
