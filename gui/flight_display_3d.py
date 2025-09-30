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
        self.max_points = gui_config.get('max_flight_points', 2000)  # More points for longer trails
        
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
        
        # Static elements (drawn once)
        self.static_elements_drawn = False
        
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
        clear_btn = ttk.Button(control_frame, text="Clear Paths", command=self._clear_paths)
        clear_btn.pack(side=tk.LEFT, padx=(5, 20))
        
        # Trail length control
        ttk.Label(control_frame, text="Trail Length:").pack(side=tk.LEFT)
        self.trail_length = tk.IntVar(value=100000)
        trail_spinbox = ttk.Spinbox(control_frame, from_=50, to=500000, width=8,
                                   textvariable=self.trail_length)
        trail_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        
        # Matplotlib figure with 3D
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.fig.patch.set_facecolor('white')
        
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
        azim = self.gui_config.get('default_camera_azimuth', -45)
        self.ax.view_init(elev=elev, azim=azim)
        
        self.static_elements_drawn = True
        self.canvas.draw()
        
    def _draw_room_boundaries(self):
        """Draw room boundary wireframe"""
        bounds = self.room_config.get('bounds', {})
        x_min, x_max = bounds.get('x_min', -3), bounds.get('x_max', 3)
        y_min, y_max = bounds.get('y_min', -3), bounds.get('y_max', 3)
        z_min, z_max = bounds.get('z_min', 0), bounds.get('z_max', 3)
        
        # Define room corners
        corners = [
            [x_min, x_max, x_max, x_min, x_min],  # x coords
            [y_min, y_min, y_max, y_max, y_min],  # y coords
            [z_min, z_min, z_min, z_min, z_min]   # z coords (floor)
        ]
        
        # Draw floor
        self.ax.plot(corners[0], corners[1], corners[2], 'k-', alpha=0.3, linewidth=1)
        
        # Draw ceiling
        corners_ceiling = [
            [x_min, x_max, x_max, x_min, x_min],  # x coords
            [y_min, y_min, y_max, y_max, y_min],  # y coords
            [z_max, z_max, z_max, z_max, z_max]   # z coords (ceiling)
        ]
        self.ax.plot(corners_ceiling[0], corners_ceiling[1], corners_ceiling[2], 'k-', alpha=0.3, linewidth=1)
        
        # Draw vertical edges
        for x, y in [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]:
            self.ax.plot([x, x], [y, y], [z_min, z_max], 'k-', alpha=0.3, linewidth=1)
    
    def _draw_feeders(self):
        """Draw feeder positions using current dynamic positions"""
        for feeder in self.feeder_configs:
            # Use current position instead of static x,y,z
            x, y, z = feeder.get_current_position()
            
            # Draw feeder as a larger marker
            self.ax.scatter([x], [y], [z], c='red', s=200, marker='s', 
                          alpha=0.8, edgecolors='black', linewidth=2)
            
            # Add feeder label with position name
            position_name = feeder.get_position_name()
            label = f'F{feeder.feeder_id}\n{position_name}'
            self.ax.text(x, y, z + 0.1, label, 
                        fontsize=9, fontweight='bold', ha='center')
            
            # Draw activation zone (sphere)
            activation_radius = feeder.activation_radius
            u = np.linspace(0, 2 * np.pi, 20)
            v = np.linspace(0, np.pi, 20)
            x_sphere = x + activation_radius * np.outer(np.cos(u), np.sin(v))
            y_sphere = y + activation_radius * np.outer(np.sin(u), np.sin(v))
            z_sphere = z + activation_radius * np.outer(np.ones(np.size(u)), np.cos(v))
            
            self.ax.plot_surface(x_sphere, y_sphere, z_sphere, 
                               alpha=0.1, color='red', linewidth=0)

    
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
                update_interval = self.gui_config.get('flight_display_update_interval', 0.5)
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
            trail_length = self.trail_length.get()
            
            # Plot data
            if selected_bat == "All":
                # Plot all bats
                for i, (bat_id, data) in enumerate(self.flight_data.items()):
                    if len(data['x']) > 1:
                        color = self.bat_colors[i % len(self.bat_colors)]
                        self._plot_bat_path_3d(data, bat_id, color, trail_length)
            else:
                # Plot selected bat only
                if selected_bat in self.flight_data:
                    data = self.flight_data[selected_bat]
                    if len(data['x']) > 1:
                        self._plot_bat_path_3d(data, selected_bat, 'blue', trail_length)
            
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
        # Set labels and title
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m)')
        self.ax.set_title('Bat Flight Paths - 3D View')
        
        # Set room bounds
        bounds = self.room_config.get('bounds', {})
        self.ax.set_xlim(bounds.get('x_min', -3), bounds.get('x_max', 3))
        self.ax.set_ylim(bounds.get('y_min', -3), bounds.get('y_max', 3))
        self.ax.set_zlim(bounds.get('z_min', 0), bounds.get('z_max', 3))
        
        # Draw room boundaries
        self._draw_room_boundaries()
        
        # Draw feeders
        self._draw_feeders()
    
    def _clear_dynamic_elements(self):
        """Clear only dynamic elements, preserve static ones and cached collections"""
        artists_to_remove = []
        
        # Remove ALL collections except static ones and current cached collections
        for collection in self.ax.collections:
            # Keep feeder markers (large red squares)
            if (hasattr(collection, '_sizes') and collection._sizes is not None and 
                len(collection._sizes) > 0 and max(collection._sizes) >= 200):
                continue
            # Keep activation zones (transparent spheres)  
            if (hasattr(collection, '_alpha') and collection._alpha is not None and 
                collection._alpha < 0.5):
                continue
            # Keep current cached Line3DCollections
            if collection in self.cached_collections.values():
                continue
            artists_to_remove.append(collection)
        
        # Remove ALL scatter points (current position markers will be redrawn)
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
                          c=color, s=120, alpha=1.0, edgecolors='white', 
                          linewidth=2, marker='o')
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
            
            # Optimized fading calculation - recent = more visible
            fade_samples = min(20, n_segments)
            alphas = np.full(n_segments, 0.4)  # Base visibility throughout
            
            # Apply fade to RECENT samples (end of trail more visible)
            if fade_samples > 1:
                fade_indices = np.arange(fade_samples)
                alphas[-fade_samples:] = 0.4 + 0.6 * (fade_indices / (fade_samples - 1))
            elif fade_samples == 1:
                alphas[-1:] = 1.0  # Single point gets full alpha
            
            # Simple linewidth progression (recent = thicker)
            linewidths = np.linspace(1.0, 2.5, n_segments)
            
            # Convert color efficiently
            if isinstance(color, str) and color in mcolors.CSS4_COLORS:
                color_rgb = mcolors.to_rgb(color)
            else:
                color_rgb = color
            
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
        
        # Only current position marker (SINGLE DOT ONLY)
        self.ax.scatter([x_data[-1]], [y_data[-1]], [z_data[-1]], 
                      c=color, s=120, alpha=1.0, edgecolors='white', 
                      linewidth=2, marker='o')
    
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
            
            # Clean performance display
            perf_text = f'FPS: {fps:.1f} | Points: {total_points:,}'
            
            self.fps_text = self.ax.text2D(0.02, 0.98, perf_text, 
                                          transform=self.ax.transAxes,
                                          fontsize=10, color='black',
                                          bbox=dict(boxstyle='round,pad=0.3', 
                                                   facecolor='white', alpha=0.8))
    
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

    def _clear_paths(self):
        """Clear all flight paths"""
        self.flight_data.clear()
        # Force redraw of static elements
        self.static_elements_drawn = False
        self._update_plot()
    
    def _reset_camera(self):
        """Reset camera to default view"""
        elev = self.gui_config.get('default_camera_elevation', 30)
        azim = self.gui_config.get('default_camera_azimuth', -45)
        self.ax.view_init(elev=elev, azim=azim)
        self.canvas.draw_idle()
    
    def _on_selection_change(self, *args):
        """Handle bat selection change"""
        # Don't redraw static elements when selection changes
        self._update_plot()