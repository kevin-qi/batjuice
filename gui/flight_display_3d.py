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
    
    def __init__(self, parent, gui_config: Dict[str, Any], room_config: Dict[str, Any], feeder_configs: list, data_manager):
        """
        Initialize 3D flight display (manual refresh mode)
        
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
        self.data_manager = data_manager  # Shared data manager
        
        # Display control
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

        # Incremental plotting for O(1) performance
        self.bat_trail_collections = defaultdict(list)  # bat_id -> List[Line3DCollection]
        self.last_plotted_index = {}  # bat_id -> last plotted point index
        
        # Background caching for true incremental rendering
        self.background = None  # Cached clean background
        self.needs_full_redraw = True  # Flag for when to redraw everything
        
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

        # NEW: Refresh button for manual 3D update
        refresh_btn = ttk.Button(control_frame, text="Refresh 3D", command=self._on_refresh_clicked)
        refresh_btn.pack(side=tk.LEFT, padx=(5, 10))

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
    
    def update_feeder_positions(self, updated_feeder_configs):
        """Update feeder positions in the display"""
        self.feeder_configs = updated_feeder_configs
        self.static_elements_drawn = False

    def _on_refresh_clicked(self):
        """Refresh 3D plot with latest data (on separate thread - non-blocking)"""
        def refresh_worker():
            try:
                # Get snapshot from data manager (thread-safe)
                snapshot = self.data_manager.get_snapshot()

                # Schedule plot update on main thread
                self.parent.after_idle(lambda: self._refresh_plot(snapshot))
            except Exception as e:
                import traceback
                print(f"3D refresh error: {e}")
                traceback.print_exc()

        # Run on separate thread (never blocks main thread)
        refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
        refresh_thread.start()

    def _refresh_plot(self, snapshot):
        """Update 3D plot with snapshot data (called on main thread)"""
        try:
            # Clear existing trajectories
            for bat_id, collections in self.bat_trail_collections.items():
                for collection in collections:
                    try:
                        collection.remove()
                    except:
                        pass
            self.bat_trail_collections.clear()
            self.last_plotted_index.clear()

            # Update bat combobox
            current_bats = list(snapshot.keys())
            current_bats.insert(0, "All")
            self.bat_combobox['values'] = current_bats

            # Trigger full replot with snapshot
            self.needs_full_redraw = True
            self._update_plot_with_snapshot(snapshot)

        except Exception as e:
            import traceback
            print(f"3D plot refresh error: {e}")
            traceback.print_exc()

    def _update_plot_with_snapshot(self, snapshot):
        """Update plot using snapshot data"""
        try:
            # Only draw static elements once or when needed
            if not self.static_elements_drawn:
                self._draw_static_elements()
                self.static_elements_drawn = True

            # Clear dynamic elements
            self._clear_dynamic_elements()

            selected_bat = self.selected_bat.get()
            trail_length = 100000  # No limit for snapshot

            # Plot data
            if selected_bat == "All":
                # Plot all bats with their distinct colors
                for i, (bat_id, data) in enumerate(snapshot.items()):
                    if len(data['x']) > 1:
                        color = self.bat_colors[i % len(self.bat_colors)]
                        new_collections = self._plot_bat_path_3d(data, bat_id, color, trail_length)
                        for lc in new_collections:
                            self.ax.add_collection3d(lc)
            else:
                # Plot all bats: selected in bright highlight color, others in grey
                highlight_color = '#FF00FF'
                grey_color = '#606060'

                for bat_id, data in snapshot.items():
                    if len(data['x']) > 1:
                        if bat_id == selected_bat:
                            new_collections = self._plot_bat_path_3d(data, bat_id, highlight_color, trail_length)
                        else:
                            new_collections = self._plot_bat_path_3d(data, bat_id, grey_color, trail_length)
                        for lc in new_collections:
                            self.ax.add_collection3d(lc)

            # Add legend
            if selected_bat == "All" and len(snapshot) > 1:
                if self.ax.get_legend():
                    self.ax.get_legend().remove()

                legend_elements = []
                for i, bat_id in enumerate(snapshot.keys()):
                    color = self.bat_colors[i % len(self.bat_colors)]
                    from matplotlib.lines import Line2D
                    legend_elements.append(Line2D([0], [0], color=color, lw=2, label=bat_id))

                if legend_elements:
                    self.ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')

            # Add FPS counter
            self._draw_fps_counter()

            # Full redraw
            self.canvas.draw()
            self.needs_full_redraw = False

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
        """Clear only dynamic elements (scatter points), preserve static ones and bat trail collections"""
        from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

        artists_to_remove = []

        # Remove ALL collections except static ones and bat trail collections
        for collection in self.ax.collections:
            # Keep feeder elements (squares and spheres tracked in lists)
            if (collection in self.feeder_square_collections or
                collection in self.feeder_trigger_sphere_collections or
                collection in self.feeder_reactivation_sphere_collections):
                continue

            # Keep all bat trail Line3DCollections (now stored in lists per bat)
            is_bat_trail = False
            for bat_collections in self.bat_trail_collections.values():
                if collection in bat_collections:
                    is_bat_trail = True
                    break
            if is_bat_trail:
                continue

            # Remove scatter points and other temporary collections
            artists_to_remove.append(collection)

        # Remove temporary elements (scatter points will be redrawn each frame)
        for artist in artists_to_remove:
            try:
                artist.remove()
            except:
                pass
    
    def _plot_bat_path_3d(self, data: Dict, bat_id: str, color: str, trail_length: int):
        """Plot bat flight path in 3D with O(1) incremental plotting
        
        Returns:
            list: New Line3DCollection objects created (for incremental rendering)
        """
        import numpy as np
        import matplotlib.colors as mcolors
        from mpl_toolkits.mplot3d.art3d import Line3DCollection

        x_data = list(data['x'])
        y_data = list(data['y'])
        z_data = list(data['z'])

        if len(x_data) < 1:
            return []

        current_length = len(x_data)
        new_collections = []  # Track new collections created this call

        # Convert color to RGB tuple (handles hex colors and named colors)
        if isinstance(color, str):
            color_rgb = mcolors.to_rgb(color)
        else:
            color_rgb = color

        # Check if this is a grey/unhighlighted trajectory (for lower opacity)
        is_grey = (color_rgb[0] == color_rgb[1] == color_rgb[2])  # Grey has equal RGB values

        # Determine alpha and linewidth based on color
        if is_grey:
            base_alpha = 0.3
            fade_alpha = 0.6
            linewidth = 1.5  # Thinner for performance
        else:
            base_alpha = 0.75
            fade_alpha = 1.0
            linewidth = 2.0  # Thinner for performance

        # INCREMENTAL PLOTTING: Only plot NEW segments since last call
        last_idx = self.last_plotted_index.get(bat_id, 0)
        is_full_replot = (last_idx == 0 and current_length > 1)

        # Check if we need to replot everything (data was cleaned up or bat just appeared)
        if last_idx > current_length:
            # Data was cleaned up - clear and restart
            for collection in self.bat_trail_collections[bat_id]:
                try:
                    collection.remove()
                except:
                    pass
            self.bat_trail_collections[bat_id].clear()
            last_idx = 0
            self.last_plotted_index[bat_id] = 0
            is_full_replot = True

        # Calculate new segments to plot
        if current_length > last_idx and current_length > 1:
            # Determine which points are new
            if last_idx == 0:
                # First time plotting - plot all segments
                new_start = 0
            else:
                # Plot only new segments (start from previous point to create continuity)
                new_start = max(0, last_idx - 1)

            # Extract new points
            new_x = x_data[new_start:]
            new_y = y_data[new_start:]
            new_z = z_data[new_start:]

            if len(new_x) >= 2:
                # Convert to numpy arrays
                x_array = np.array(new_x)
                y_array = np.array(new_y)
                z_array = np.array(new_z)

                # Check for NaN values and skip if any are present
                if not (np.isnan(x_array).any() or np.isnan(y_array).any() or np.isnan(z_array).any()):
                    # Create line segments with distance filtering
                    points = np.array([x_array, y_array, z_array]).T

                    # Build CONTINUOUS chains of segments (no gaps from distance filtering)
                    # This prevents matplotlib from showing endpoint markers
                    current_chain = []
                    chains = []
                    
                    for i in range(len(points) - 1):
                        p1 = points[i]
                        p2 = points[i + 1]
                        # Calculate Euclidean distance
                        distance = np.sqrt(np.sum((p2 - p1) ** 2))

                        # Only add segment if distance <= 1.0 meter
                        if distance <= 1.0:
                            current_chain.append([p1, p2])
                        else:
                            # Gap detected - save current chain and start new one
                            if len(current_chain) > 0:
                                chains.append((current_chain, i - len(current_chain), i))
                                current_chain = []
                    
                    # Don't forget the last chain
                    if len(current_chain) > 0:
                        chains.append((current_chain, len(points) - len(current_chain) - 1, len(points) - 1))

                    # BATCHING STRATEGY: Combine ALL chains into ONE large collection per bat
                    # This minimizes the number of collections matplotlib must handle
                    if len(chains) > 0:
                        all_segments = []
                        all_alphas = []
                        
                        # Collect all segments and their alphas
                        for chain_segments, start_idx, end_idx in chains:
                            for seg_idx, segment in enumerate(chain_segments):
                                all_segments.append(segment)
                                
                                # Calculate alpha for this segment
                                global_seg_idx = new_start + start_idx + seg_idx
                                segments_from_end = current_length - 1 - global_seg_idx
                                
                                if segments_from_end < 20:  # Fade last 20 segments
                                    fade_progress = (20 - segments_from_end) / 20
                                    alpha = base_alpha + (fade_alpha - base_alpha) * fade_progress
                                else:
                                    alpha = base_alpha
                                
                                all_alphas.append(alpha)
                        
                        # Create ONE large collection for the entire bat trajectory
                        # This dramatically reduces the number of objects matplotlib must render
                        if len(all_segments) > 0:
                            segments = np.array(all_segments)
                            n_segments = len(segments)
                            linewidths = np.full(n_segments, linewidth)
                            colors = [(color_rgb[0], color_rgb[1], color_rgb[2], alpha) for alpha in all_alphas]
                            
                            # Create single large collection (PERFORMANCE OPTIMIZATION)
                            # Disable antialiasing for better rotation performance
                            lc = Line3DCollection(segments, colors=colors, linewidths=linewidths,
                                                linestyles='solid', antialiased=False)  # Antialiasing off for speed
                            self.bat_trail_collections[bat_id].append(lc)
                            new_collections.append(lc)

            # Update last plotted index
            self.last_plotted_index[bat_id] = current_length

        # Only current position marker (SINGLE DOT ONLY) - dark theme edge
        if len(x_data) > 0:
            self.ax.scatter([x_data[-1]], [y_data[-1]], [z_data[-1]],
                          c=color, s=100, alpha=1.0, edgecolors='#2B2D31',
                          linewidth=2.0, marker='o')
        
        return new_collections
    
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

    def _clear_paths_with_confirmation(self):
        """Clear all flight paths with confirmation dialog"""
        from tkinter import messagebox
        if messagebox.askyesno("Clear Paths", "Are you sure you want to clear all flight paths?"):
            self._clear_paths()

    def _clear_paths(self):
        """Clear all flight paths"""
        # Clear data manager (shared data)
        self.data_manager.clear()

        # Clear all bat trail collections
        for bat_id, collections in self.bat_trail_collections.items():
            for collection in collections:
                try:
                    collection.remove()
                except:
                    pass
        self.bat_trail_collections.clear()
        self.last_plotted_index.clear()

        # Force redraw
        self.static_elements_drawn = False
        self.canvas.draw()

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
        # Note: User must click Refresh to see updated display

    def _on_selection_change(self, *args):
        """Handle bat selection change"""
        # Clear all bat trail collections to force replot with new colors
        for bat_id, collections in self.bat_trail_collections.items():
            for collection in collections:
                try:
                    collection.remove()
                except:
                    pass
        self.bat_trail_collections.clear()
        
        # Reset plotting indices
        self.last_plotted_index.clear()
        
        # Note: User must click Refresh to see updated colors
        print("Bat selection changed. Click 'Refresh 3D' to update.")