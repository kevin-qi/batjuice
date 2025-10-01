"""
Enhanced 3D flight path display widget using matplotlib.
"""
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import threading
import time
import math
from collections import defaultdict, deque
from typing import Dict, Any, Optional


class FlightDisplay3D:
    """Real-time 3D flight path display with camera controls"""
    
    def __init__(self, parent, gui_config: Dict[str, Any], room_config: Dict[str, Any], feeder_configs: list):
        """
        Initialize 3D flight display
        
        Args:
            parent: Parent tkinter widget
            gui_config: GUI configuration dictionary
            room_config: Room configuration with bounds
            feeder_configs: List of feeder configurations
        """
        self.parent = parent
        self.gui_config = gui_config
        self.room_config = room_config
        self.feeder_configs = feeder_configs
        self.max_points = 10000  # Maximum flight trail points

        # Data storage
        self.flight_data = defaultdict(lambda: {'x': deque(maxlen=self.max_points),
                                              'y': deque(maxlen=self.max_points),
                                              'z': deque(maxlen=self.max_points),
                                              'timestamps': deque(maxlen=self.max_points)})
        
        # Display control
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        self.selected_bat = tk.StringVar(value="All")
        self.show_trigger_radius = tk.BooleanVar(value=True)
        self.show_reactivation_radius = tk.BooleanVar(value=False)
        self.show_labels = tk.BooleanVar(value=True)
        
        # Colors for different bats (highly distinct, deutanopia-friendly, vibrant for dark background)
        # Maximum contrast palette with very different hues and brightness
        self.bat_colors = [
            '#00FFFF',  # Cyan - bright and cool
            '#FF00FF',  # Magenta - bright and warm
            '#FFFF00',  # Yellow - extremely bright
            '#0080FF',  # Blue - medium brightness
            '#FF6600',  # Orange - warm and distinct
            '#9900FF',  # Purple - cool and dark
            '#00FF00',  # Lime green - very bright
            '#FF0080'   # Rose/pink - warm mid-tone
        ]
        
        # Static elements (drawn once)
        self.static_elements_drawn = False
        self.feeder_text_elements = []  # Track text labels for removal
        self.feeder_trigger_sphere_collections = []  # Track trigger radius spheres
        self.feeder_reactivation_sphere_collections = []  # Track reactivation radius spheres
        self.feeder_square_collections = []  # Track square collections for removal
        
        # Performance monitoring
        self.frame_times = deque(maxlen=30)  # Track last 30 frame times
        self.last_frame_time = time.time()
        self.fps_text = None
        
        # Intelligent caching for performance
        self.cached_collections = {}  # bat_id -> Line3DCollection
        self.cache_dirty = {}  # bat_id -> bool (needs update)
        self.last_data_lengths = {}  # bat_id -> int (for change detection)
        
        # Display subsampling (show every Nth point)
        self.display_subsample_rate = 10  # Show every 10th point (100Hz -> 10Hz display)
        
        # Point reduction tracking
        self.last_cleanup_time = time.time()
        self.cleanup_interval = 5.0  # Clean up every 5 seconds
        self.stationary_threshold = gui_config.get('stationary_threshold', 0.5)  # meters
        self.stationary_time_window = 1.0  # seconds
        
        # Setup display
        self._setup_display()
        
    def _setup_display(self):
        """Setup the 3D flight display layout"""
        # Control frame
        control_frame = ttk.Frame(self.parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Bat selection
        ttk.Label(control_frame, text="Display Bat:").pack(side=tk.LEFT)
        self.bat_combobox = ttk.Combobox(control_frame, textvariable=self.selected_bat, width=15)
        self.bat_combobox.pack(side=tk.LEFT, padx=(5, 20))

        # Camera controls
        ttk.Label(control_frame, text="View:").pack(side=tk.LEFT)

        # Reset view button
        reset_btn = ttk.Button(control_frame, text="Reset View", command=self._reset_camera)
        reset_btn.pack(side=tk.LEFT, padx=(5, 10))

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
        
        # Matplotlib figure with 3D - dark theme
        self.fig = plt.figure(figsize=(7, 7))
        self.ax = self.fig.add_subplot(111, projection='3d')

        # Dark theme colors
        bg_color = '#2B2D31'
        pane_color = '#36393F'
        grid_color = '#505050'  # Light grey for subtle grid
        text_color = '#DCDDDE'

        self.fig.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)

        # Reduce white space around plot
        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        # Dark panes with subtle depth
        self.ax.xaxis.pane.set_facecolor(pane_color)
        self.ax.yaxis.pane.set_facecolor(pane_color)
        self.ax.zaxis.pane.set_facecolor(pane_color)
        self.ax.xaxis.pane.set_edgecolor(grid_color)
        self.ax.yaxis.pane.set_edgecolor(grid_color)
        self.ax.zaxis.pane.set_edgecolor(grid_color)
        self.ax.xaxis.pane.set_alpha(0.3)
        self.ax.yaxis.pane.set_alpha(0.3)
        self.ax.zaxis.pane.set_alpha(0.3)

        # Grid styling - very subtle, thin grey lines
        self.ax.grid(True, color='#606060', alpha=0.15, linestyle='-', linewidth=0.3)

        # Axis colors
        self.ax.xaxis.line.set_color(text_color)
        self.ax.yaxis.line.set_color(text_color)
        self.ax.zaxis.line.set_color(text_color)

        # Tick colors
        self.ax.tick_params(axis='x', colors=text_color)
        self.ax.tick_params(axis='y', colors=text_color)
        self.ax.tick_params(axis='z', colors=text_color)
        
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
        self.selected_bat.trace('w', self._on_selection_change)
        
    def _init_plot(self):
        """Initialize the 3D plot"""
        self.ax.clear()
        
        # Draw static elements
        self._draw_static_elements()
        
        # Set default camera angle
        elev = self.gui_config.get('default_camera_elevation', 30)
        azim = self.gui_config.get('default_camera_azimuth', 225)
        self.ax.view_init(elev=elev, azim=azim)
        
        self.static_elements_drawn = True
        self.canvas.draw()
        
    def _draw_room_boundaries(self):
        """Draw room boundary - floor only to avoid occlusion"""
        bounds = self.room_config.get('bounds', {})
        x_min, x_max = bounds.get('x_min', -3), bounds.get('x_max', 3)
        y_min, y_max = bounds.get('y_min', -3), bounds.get('y_max', 3)
        z_min, z_max = bounds.get('z_min', 0), bounds.get('z_max', 3)

        # Draw only floor outline to avoid occlusion (light gray for dark theme)
        self.ax.plot([x_min, x_max, x_max, x_min, x_min],
                     [y_min, y_min, y_max, y_max, y_min],
                     [z_min, z_min, z_min, z_min, z_min],
                     color='#6B7280', alpha=0.5, linewidth=1.5)
    
    def _draw_feeders(self):
        """Draw feeder positions using current dynamic positions"""
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        for feeder in self.feeder_configs:
            # Use current position instead of static x,y,z
            x, y, z = feeder.get_current_position()

            # Draw feeder as a flat 30cm x 30cm square (0.3m x 0.3m)
            size = 0.15  # Half-size for centering (30cm / 2 = 15cm = 0.15m)

            # Define square corners
            square_corners = np.array([
                [x - size, y - size, z],
                [x + size, y - size, z],
                [x + size, y + size, z],
                [x - size, y + size, z]
            ])

            # Draw filled square (minimalistic, muted orange)
            square = Poly3DCollection([square_corners], alpha=0.6, facecolor='#CC7000', edgecolor='#D97E00', linewidth=1.0)
            self.ax.add_collection3d(square)
            self.feeder_square_collections.append(square)

            # Add feeder label (minimalistic text, no box) - only if enabled
            if self.show_labels.get():
                label = f'F{feeder.feeder_id}'
                text_elem = self.ax.text(x, y, z + 0.15, label,
                                        fontsize=8, fontweight='normal', ha='center',
                                        color='white')
                self.feeder_text_elements.append(text_elem)

            # Draw trigger radius sphere (activation_radius) - subtle grey-blue
            if self.show_trigger_radius.get():
                trigger_radius = feeder.activation_radius
                u = np.linspace(0, 2 * np.pi, 20)
                v = np.linspace(0, np.pi, 20)
                x_sphere = x + trigger_radius * np.outer(np.cos(u), np.sin(v))
                y_sphere = y + trigger_radius * np.outer(np.sin(u), np.sin(v))
                z_sphere = z + trigger_radius * np.outer(np.ones(np.size(u)), np.cos(v))

                trigger_surface = self.ax.plot_surface(x_sphere, y_sphere, z_sphere,
                                                       alpha=0.12, color='#708090', linewidth=0)
                self.feeder_trigger_sphere_collections.append(trigger_surface)

            # Draw reactivation radius sphere - same subtle grey-blue
            if self.show_reactivation_radius.get():
                reactivation_radius = feeder.reactivation_distance
                u = np.linspace(0, 2 * np.pi, 20)
                v = np.linspace(0, np.pi, 20)
                x_sphere = x + reactivation_radius * np.outer(np.cos(u), np.sin(v))
                y_sphere = y + reactivation_radius * np.outer(np.sin(u), np.sin(v))
                z_sphere = z + reactivation_radius * np.outer(np.ones(np.size(u)), np.cos(v))

                reactivation_surface = self.ax.plot_surface(x_sphere, y_sphere, z_sphere,
                                                            alpha=0.12, color='#708090', linewidth=0)
                self.feeder_reactivation_sphere_collections.append(reactivation_surface)

    
    def update_feeder_positions(self, updated_feeder_configs):
        """
        Update feeder positions in the display
        
        Args:
            updated_feeder_configs: List of updated FeederConfig objects
        """
        self.feeder_configs = updated_feeder_configs
        
        # Force redraw of static elements (including feeders)
        self.static_elements_drawn = False
        
        # Schedule a redraw on the next update
        if hasattr(self, '_schedule_redraw'):
            self._schedule_redraw = True
        
        print("Flight display: Feeder positions updated")
    
    def update_positions(self, bat_states: Dict):
        """Update flight paths with new position data (subsampled for display)"""
        for bat_id, bat_state in bat_states.items():
            if bat_state.last_position:
                pos = bat_state.last_position
                
                # Skip NaN positions
                if any(math.isnan(val) for val in [pos.x, pos.y, pos.z]):
                    continue
                
                # Subsample for display (only add every Nth point)
                if not hasattr(self, '_point_counters'):
                    self._point_counters = {}
                if bat_id not in self._point_counters:
                    self._point_counters[bat_id] = 0
                
                self._point_counters[bat_id] += 1
                
                # Only add to display every Nth point
                if self._point_counters[bat_id] % self.display_subsample_rate == 0:
                    # Add to flight data
                    self.flight_data[bat_id]['x'].append(pos.x)
                    self.flight_data[bat_id]['y'].append(pos.y)
                    self.flight_data[bat_id]['z'].append(pos.z)
                    self.flight_data[bat_id]['timestamps'].append(pos.timestamp)
                    
                    # Mark cache as dirty
                    self.cache_dirty[bat_id] = True
                
                # Periodic cleanup of stationary points
                current_time = time.time()
                if current_time - self.last_cleanup_time > self.cleanup_interval:
                    self._cleanup_stationary_points()
                    self.last_cleanup_time = current_time
        
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
                time.sleep(0.1)  # Update at 10 Hz
            except Exception as e:
                import traceback
                print(f"Flight display update error in {__file__}:")
                print(f"Error: {e}")
                traceback.print_exc()
                refresh_rate_hz = self.gui_config.get('refresh_rate_hz', 10)
                update_interval = 1.0 / refresh_rate_hz  # Convert Hz to seconds
                time.sleep(update_interval)
    
    def _update_plot(self):
        """Update the 3D plot (called on main thread)"""
        try:
            # Performance monitoring
            current_time = time.time()
            if self.last_frame_time:
                frame_time = current_time - self.last_frame_time
                self.frame_times.append(frame_time)
            self.last_frame_time = current_time
            
            # Only draw static elements once or when needed
            if not self.static_elements_drawn:
                self._draw_static_elements()
                self.static_elements_drawn = True
            
            # Clear only the dynamic bat trail elements
            self._clear_dynamic_elements()
            
            selected_bat = self.selected_bat.get()
            trail_length = self.max_points  # Use hardcoded max points
            
            # Plot data
            if selected_bat == "All":
                # Plot all bats with their distinct colors
                for i, (bat_id, data) in enumerate(self.flight_data.items()):
                    if len(data['x']) > 1:
                        color = self.bat_colors[i % len(self.bat_colors)]
                        self._plot_bat_path_3d(data, bat_id, color, trail_length)
            else:
                # Plot all bats: selected in bright highlight color, others in grey
                highlight_color = '#FF00FF'  # Bright magenta for maximum visibility and contrast with grey
                grey_color = '#606060'  # Medium grey for background bats

                for bat_id, data in self.flight_data.items():
                    if len(data['x']) > 1:
                        if bat_id == selected_bat:
                            # Highlight the selected bat
                            self._plot_bat_path_3d(data, bat_id, highlight_color, trail_length)
                        else:
                            # Show other bats in grey
                            self._plot_bat_path_3d(data, bat_id, grey_color, trail_length)
            
            # Add legend ONCE (not every frame!)
            if selected_bat == "All" and len(self.flight_data) > 1:
                # Clear existing legend
                if self.ax.get_legend():
                    self.ax.get_legend().remove()
                
                # Create new legend with bat colors
                legend_elements = []
                for i, bat_id in enumerate(self.flight_data.keys()):
                    color = self.bat_colors[i % len(self.bat_colors)]
                    from matplotlib.lines import Line2D
                    legend_elements.append(Line2D([0], [0], color=color, lw=2, label=bat_id))
                
                if legend_elements:
                    self.ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Add FPS counter
            self._draw_fps_counter()
            
            # Use blit for better performance
            self.canvas.draw_idle()
            
        except Exception as e:
            import traceback
            print(f"Error updating 3D flight plot in {__file__}:")
            print(f"Error: {e}")
            traceback.print_exc()
    
    def _draw_static_elements(self):
        """Draw static room elements that don't change"""
        # Clear ALL collections and texts when redrawing static elements
        from mpl_toolkits.mplot3d.art3d import Line3DCollection

        # Clear old feeder elements
        for collection in self.feeder_square_collections:
            try:
                collection.remove()
            except:
                pass
        self.feeder_square_collections.clear()

        for collection in self.feeder_trigger_sphere_collections:
            try:
                collection.remove()
            except:
                pass
        self.feeder_trigger_sphere_collections.clear()

        for collection in self.feeder_reactivation_sphere_collections:
            try:
                collection.remove()
            except:
                pass
        self.feeder_reactivation_sphere_collections.clear()

        for text_elem in self.feeder_text_elements:
            try:
                text_elem.remove()
            except:
                pass
        self.feeder_text_elements.clear()

        # Set labels (no title) with light color for dark theme
        text_color = '#DCDDDE'
        self.ax.set_xlabel('X (m)', color=text_color)
        self.ax.set_ylabel('Y (m)', color=text_color)
        self.ax.set_zlabel('Z (m)', color=text_color)

        # Set room bounds
        bounds = self.room_config.get('bounds', {})
        x_min, x_max = bounds.get('x_min', -3), bounds.get('x_max', 3)
        y_min, y_max = bounds.get('y_min', -3), bounds.get('y_max', 3)
        z_min, z_max = bounds.get('z_min', 0), bounds.get('z_max', 3)

        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)
        self.ax.set_zlim(z_min, z_max)

        # Set ticks to show only min, 0, and max
        self.ax.set_xticks([x_min, 0, x_max])
        self.ax.set_yticks([y_min, 0, y_max])
        self.ax.set_zticks([z_min, 0, z_max])

        # Set equal aspect ratio for all axes
        x_range = x_max - x_min
        y_range = y_max - y_min
        z_range = z_max - z_min
        self.ax.set_box_aspect([x_range, y_range, z_range])

        # Draw room boundaries
        self._draw_room_boundaries()

        # Draw feeders
        self._draw_feeders()
    
    def _clear_dynamic_elements(self):
        """Clear only dynamic elements, preserve static ones and cached collections"""
        from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

        artists_to_remove = []

        # Remove ALL collections except static ones and current cached collections
        for collection in self.ax.collections:
            # Keep feeder elements (squares and spheres tracked in lists)
            if (collection in self.feeder_square_collections or
                collection in self.feeder_trigger_sphere_collections or
                collection in self.feeder_reactivation_sphere_collections):
                continue
            # Keep current cached Line3DCollections for bat trails
            if isinstance(collection, Line3DCollection) and collection in self.cached_collections.values():
                continue
            # Remove scatter points and other temporary collections
            artists_to_remove.append(collection)

        # Remove temporary elements (scatter points will be redrawn)
        for artist in artists_to_remove:
            try:
                artist.remove()
            except:
                pass
    
    def _plot_bat_path_3d(self, data: Dict, bat_id: str, color: str, trail_length: int):
        """Plot 3D path using intelligent caching for high performance"""
        import numpy as np
        import matplotlib.colors as mcolors
        from mpl_toolkits.mplot3d.art3d import Line3DCollection
        
        x_data = list(data['x'])
        y_data = list(data['y'])
        z_data = list(data['z'])
        
        if len(x_data) < 2:
            return
        
        # Limit trail length if specified
        if len(x_data) > trail_length:
            x_data = x_data[-trail_length:]
            y_data = y_data[-trail_length:]
            z_data = z_data[-trail_length:]
        
        current_length = len(x_data)
        
        # TRUE CACHING: Check if we can reuse cached collection
        if (bat_id in self.cached_collections and
            not self.cache_dirty.get(bat_id, True) and
            self.last_data_lengths.get(bat_id, 0) == current_length):
            # Collection exists and is current - just add current position marker
            self.ax.scatter([x_data[-1]], [y_data[-1]], [z_data[-1]],
                          c=color, s=120, alpha=1.0, edgecolors='#2B2D31',
                          linewidth=2.5, marker='o')
            return
        
        # Remove old cached collection if exists
        if bat_id in self.cached_collections:
            try:
                self.cached_collections[bat_id].remove()
            except:
                pass
            del self.cached_collections[bat_id]
        
        # Create new trail ONLY (no dots along path)
        if len(x_data) > 1:
            # Convert to numpy arrays for efficiency
            x_array = np.array(x_data)
            y_array = np.array(y_data)
            z_array = np.array(z_data)
            
            # Check for NaN values and skip if any are present
            if np.isnan(x_array).any() or np.isnan(y_array).any() or np.isnan(z_array).any():
                return
            
            # Create line segments - optimized for large datasets
            points = np.array([x_array, y_array, z_array]).T
            segments = np.array([points[:-1], points[1:]]).transpose(1, 0, 2)
            
            n_segments = len(segments)
            
            # Skip if no segments to draw
            if n_segments == 0:
                return
            
            # Convert color to RGB tuple (handles hex colors and named colors)
            if isinstance(color, str):
                color_rgb = mcolors.to_rgb(color)
            else:
                color_rgb = color

            # Check if this is a grey/unhighlighted trajectory (for lower opacity)
            is_grey = (color_rgb[0] == color_rgb[1] == color_rgb[2])  # Grey has equal RGB values

            # Minimal fading - keep colors strong throughout the trail
            fade_samples = min(20, n_segments)
            if is_grey:
                # Grey trajectories are more transparent
                alphas = np.full(n_segments, 0.3)  # Lower base visibility for background bats
                # Apply subtle fade to RECENT samples
                if fade_samples > 1:
                    fade_indices = np.arange(fade_samples)
                    alphas[-fade_samples:] = 0.3 + 0.3 * (fade_indices / (fade_samples - 1))
                elif fade_samples == 1:
                    alphas[-1:] = 0.6
            else:
                # Colored trajectories stay strong
                alphas = np.full(n_segments, 0.75)  # Higher base visibility throughout
                # Apply subtle fade to RECENT samples (end of trail slightly more visible)
                if fade_samples > 1:
                    fade_indices = np.arange(fade_samples)
                    alphas[-fade_samples:] = 0.75 + 0.25 * (fade_indices / (fade_samples - 1))
                elif fade_samples == 1:
                    alphas[-1:] = 1.0  # Single point gets full alpha

            # Simple linewidth progression (recent = thicker)
            linewidths = np.linspace(1.0, 2.5, n_segments)

            # Create colors array efficiently
            colors = [(color_rgb[0], color_rgb[1], color_rgb[2], alpha) for alpha in alphas]
            
            # Create and cache Line3DCollection (ONLY TRAILS - NO DOTS)
            # Additional safety check for empty arrays
            if (len(colors) > 0 and len(linewidths) > 0 and len(segments) > 0 and 
                segments.size > 0 and len(alphas) > 0):
                lc = Line3DCollection(segments, colors=colors, linewidths=linewidths, 
                                    capstyle='round', joinstyle='round')
                self.ax.add_collection3d(lc)
                
                # Cache the collection properly
                self.cached_collections[bat_id] = lc
                self.cache_dirty[bat_id] = False
                self.last_data_lengths[bat_id] = current_length
        
        # Only current position marker (SINGLE DOT ONLY) - dark theme edge
        self.ax.scatter([x_data[-1]], [y_data[-1]], [z_data[-1]],
                      c=color, s=120, alpha=1.0, edgecolors='#2B2D31',
                      linewidth=2.5, marker='o')
    
    def _draw_fps_counter(self):
        """Draw FPS counter with performance metrics"""
        if len(self.frame_times) > 5:  # Need some samples
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
            
            # Calculate total points being rendered
            total_points = sum(len(data['x']) for data in self.flight_data.values())
            
            # Remove old FPS text
            if self.fps_text:
                try:
                    self.fps_text.remove()
                except:
                    pass
            
            # Clean performance display (dark theme)
            perf_text = f'FPS: {fps:.1f} | Points: {total_points:,}'

            self.fps_text = self.ax.text2D(0.02, 0.98, perf_text,
                                          transform=self.ax.transAxes,
                                          fontsize=10, color='#DCDDDE',
                                          bbox=dict(boxstyle='round,pad=0.3',
                                                   facecolor='#2B2D31', alpha=0.7, edgecolor='#4A5568'))
    
    def _cleanup_stationary_points(self):
        """Remove stationary points to improve performance"""
        for bat_id, data in self.flight_data.items():
            if len(data['x']) < 100:  # Need enough points to analyze
                continue
            
            x_data = list(data['x'])
            y_data = list(data['y'])
            z_data = list(data['z'])
            timestamps = list(data['timestamps'])
            
            # Find stationary sequences
            keep_indices = []
            for i in range(len(x_data)):
                if i == 0 or i == len(x_data) - 1:  # Always keep first and last
                    keep_indices.append(i)
                    continue
                
                # Check displacement over time window
                start_time = timestamps[i] - self.stationary_time_window
                displacement = 0
                
                for j in range(i-1, -1, -1):
                    if timestamps[j] < start_time:
                        break
                    dx = x_data[i] - x_data[j]
                    dy = y_data[i] - y_data[j]
                    dz = z_data[i] - z_data[j]
                    displacement = max(displacement, math.sqrt(dx*dx + dy*dy + dz*dz))
                
                # Keep point if significant movement or key position
                if displacement > self.stationary_threshold or i % 10 == 0:  # Keep every 10th for continuity
                    keep_indices.append(i)
            
            # Rebuild data with filtered points
            if len(keep_indices) < len(x_data) * 0.8:  # Only if significant reduction
                filtered_x = [x_data[i] for i in keep_indices]
                filtered_y = [y_data[i] for i in keep_indices]
                filtered_z = [z_data[i] for i in keep_indices]
                filtered_timestamps = [timestamps[i] for i in keep_indices]
                
                # Replace data
                data['x'].clear()
                data['y'].clear()
                data['z'].clear()
                data['timestamps'].clear()
                
                data['x'].extend(filtered_x)
                data['y'].extend(filtered_y)
                data['z'].extend(filtered_z)
                data['timestamps'].extend(filtered_timestamps)
                
                # Mark cache as dirty
                self.cache_dirty[bat_id] = True

    def _clear_paths_with_confirmation(self):
        """Clear all flight paths with confirmation dialog"""
        from tkinter import messagebox
        if messagebox.askyesno("Clear Paths", "Are you sure you want to clear all flight paths?"):
            self._clear_paths()

    def _clear_paths(self):
        """Clear all flight paths"""
        self.flight_data.clear()
        # Force redraw of static elements
        self.static_elements_drawn = False
        self._update_plot()

    def _reset_camera(self):
        """Reset camera to default view"""
        elev = self.gui_config.get('default_camera_elevation', 30)
        azim = self.gui_config.get('default_camera_azimuth', 225)
        self.ax.view_init(elev=elev, azim=azim)
        self.canvas.draw_idle()

    def _toggle_display(self):
        """Handle toggle changes for spheres and labels"""
        # Force redraw of static elements
        self.static_elements_drawn = False
        self._update_plot()

    def _on_selection_change(self, *args):
        """Handle bat selection change"""
        # Don't redraw static elements when selection changes
        self._update_plot()