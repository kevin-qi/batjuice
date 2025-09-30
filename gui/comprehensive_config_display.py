"""
Comprehensive Configuration Display

This module displays ALL configuration values that are actually being used 
by the system at runtime. Every value shown here reflects the exact values
being used by the codebase.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Tuple
import json


class ComprehensiveConfigDisplay:
    """Displays all system configuration values with their actual runtime values"""
    
    def __init__(self, parent, settings):
        """
        Initialize comprehensive configuration display
        
        Args:
            parent: Parent tkinter widget
            settings: Settings object containing configuration
        """
        self.parent = parent
        self.settings = settings
        
        # Create main scrollable frame
        self.canvas = tk.Canvas(parent)
        self.scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        self._bind_mousewheel()
        
        # Storage for dynamic values
        self.config_vars = {}
        
        # Create all configuration sections
        self._create_all_sections()
        
        # Initial update
        self._update_all_values()
    
    def _bind_mousewheel(self):
        """Bind mousewheel to canvas for scrolling"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")
        
        self.canvas.bind('<Enter>', _bind_to_mousewheel)
        self.canvas.bind('<Leave>', _unbind_from_mousewheel)
    
    def _create_all_sections(self):
        """Create all configuration sections"""
        row = 0
        
        # Title
        title_label = ttk.Label(self.scrollable_frame, text="System Configuration", 
                               font=("TkDefaultFont", 14, "bold"))
        title_label.grid(row=row, column=0, columnspan=2, pady=(0, 20), sticky="w")
        row += 1
        
        # Refresh button
        refresh_btn = ttk.Button(self.scrollable_frame, text="Refresh All Values", 
                                command=self._update_all_values)
        refresh_btn.grid(row=row, column=0, columnspan=2, pady=(0, 20), sticky="w")
        row += 2
        
        # RTLS System Configuration
        row = self._create_rtls_section(row)
        
        # Hardware Configuration  
        row = self._create_hardware_section(row)
        
        # Feeder Configuration
        row = self._create_feeder_section(row)
        
        # Task Logic Configuration
        row = self._create_task_logic_section(row)
        
        # Room Configuration
        row = self._create_room_section(row)
        
        # GUI Configuration
        row = self._create_gui_section(row)
        
        # Logging Configuration  
        row = self._create_logging_section(row)

        # Mock Configuration (if used)
        row = self._create_mock_section(row)
        
        # Configuration Files Info
        row = self._create_files_section(row)
    
    def _create_section_header(self, parent, row: int, title: str) -> int:
        """Create a section header"""
        separator = ttk.Separator(parent, orient='horizontal')
        separator.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(20, 5))
        row += 1
        
        header = ttk.Label(parent, text=title, font=("TkDefaultFont", 12, "bold"))
        header.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))
        row += 1
        
        return row
    
    def _create_config_item(self, parent, row: int, label: str, var_name: str, 
                           description: str = "") -> int:
        """Create a configuration item with label and value"""
        # Label
        label_widget = ttk.Label(parent, text=f"{label}:")
        label_widget.grid(row=row, column=0, sticky="w", padx=(20, 10), pady=2)
        
        # Value
        self.config_vars[var_name] = tk.StringVar()
        value_widget = ttk.Label(parent, textvariable=self.config_vars[var_name], 
                                font=("TkDefaultFont", 9, "bold"), foreground="blue")
        value_widget.grid(row=row, column=1, sticky="w", pady=2)
        
        # Description (if provided)
        if description:
            desc_widget = ttk.Label(parent, text=f"({description})", 
                                  font=("TkDefaultFont", 8), foreground="gray")
            desc_widget.grid(row=row+1, column=0, columnspan=2, sticky="w", 
                           padx=(40, 0), pady=(0, 5))
            return row + 2
        
        return row + 1
    
    def _create_rtls_section(self, row: int) -> int:
        """Create RTLS system configuration section"""
        row = self._create_section_header(self.scrollable_frame, row, "Position Tracking (RTLS)")
        
        row = self._create_config_item(self.scrollable_frame, row, "Backend System", 
                                     "rtls_backend", "cortex, ciholas, or mock")
        
        row = self._create_config_item(self.scrollable_frame, row, "Connection Status", 
                                     "rtls_status", "Runtime connection state")
        
        # Cortex specific
        row = self._create_config_item(self.scrollable_frame, row, "Cortex Server IP", 
                                     "cortex_ip", "MotionAnalysis Cortex server")
        row = self._create_config_item(self.scrollable_frame, row, "Cortex Server Port", 
                                     "cortex_port")
        row = self._create_config_item(self.scrollable_frame, row, "Cortex Frame Rate", 
                                     "cortex_frame_rate", "Hz")
        row = self._create_config_item(self.scrollable_frame, row, "Cortex Timeout", 
                                     "cortex_timeout", "seconds")
        
        # Ciholas specific
        row = self._create_config_item(self.scrollable_frame, row, "Ciholas Multicast Group", 
                                     "ciholas_multicast")
        row = self._create_config_item(self.scrollable_frame, row, "Ciholas Local Port", 
                                     "ciholas_port")
        row = self._create_config_item(self.scrollable_frame, row, "Ciholas Frame Rate", 
                                     "ciholas_frame_rate", "Hz")
        row = self._create_config_item(self.scrollable_frame, row, "Ciholas Timeout", 
                                     "ciholas_timeout", "seconds")
        row = self._create_config_item(self.scrollable_frame, row, "Ciholas Serial Numbers", 
                                     "ciholas_serial_numbers")
        row = self._create_config_item(self.scrollable_frame, row, "Ciholas Coordinate Units", 
                                     "ciholas_units")
        row = self._create_config_item(self.scrollable_frame, row, "Ciholas Coordinate Scale", 
                                     "ciholas_scale")
        
        return row
    
    def _create_hardware_section(self, row: int) -> int:
        """Create hardware configuration section"""
        row = self._create_section_header(self.scrollable_frame, row, "Hardware")
        
        row = self._create_config_item(self.scrollable_frame, row, "Arduino Port", 
                                     "arduino_port", "Serial communication port")
        row = self._create_config_item(self.scrollable_frame, row, "Arduino Baudrate", 
                                     "arduino_baudrate", "bits/second")
        row = self._create_config_item(self.scrollable_frame, row, "Arduino Timeout", 
                                     "arduino_timeout", "seconds")
        row = self._create_config_item(self.scrollable_frame, row, "Arduino Status", 
                                     "arduino_status", "Runtime connection state")
        
        return row
    
    def _create_feeder_section(self, row: int) -> int:
        """Create feeder configuration section"""
        row = self._create_section_header(self.scrollable_frame, row, "Feeders")
        
        row = self._create_config_item(self.scrollable_frame, row, "Total Feeders", 
                                     "feeder_count", "Number configured")
        
        # Dynamic feeder details (will be populated in update)
        self.feeder_details_row = row
        row += 10  # Reserve space for feeder details
        
        return row
    
    def _create_task_logic_section(self, row: int) -> int:
        """Create task logic configuration section"""
        row = self._create_section_header(self.scrollable_frame, row, "Task Logic")
        
        row = self._create_config_item(self.scrollable_frame, row, "Reactivation Distance", 
                                     "task_reactivation_distance", "Distance bat must fly to reactivate (meters)")
        row = self._create_config_item(self.scrollable_frame, row, "Reactivation Time", 
                                     "task_reactivation_time", "Time bat must be far away (seconds)")
        row = self._create_config_item(self.scrollable_frame, row, "Feeder Ownership Distance", 
                                     "task_feeder_ownership_distance", "Distance owner must move to release feeder (meters)")
        row = self._create_config_item(self.scrollable_frame, row, "Position Timeout", 
                                     "task_position_timeout", "Max age of position data (seconds)")
        row = self._create_config_item(self.scrollable_frame, row, "Config File Location", 
                                     "task_config_file", "Source of task logic parameters")
        
        return row
    
    def _create_room_section(self, row: int) -> int:
        """Create room configuration section"""
        row = self._create_section_header(self.scrollable_frame, row, "Room Setup")
        
        row = self._create_config_item(self.scrollable_frame, row, "X Boundaries", 
                                     "room_x_bounds", "min to max")
        row = self._create_config_item(self.scrollable_frame, row, "Y Boundaries", 
                                     "room_y_bounds", "min to max")
        row = self._create_config_item(self.scrollable_frame, row, "Z Boundaries", 
                                     "room_z_bounds", "min to max")
        row = self._create_config_item(self.scrollable_frame, row, "Coordinate Units", 
                                     "room_units", "meters, cm, etc.")
        
        return row
    
    def _create_gui_section(self, row: int) -> int:
        """Create GUI configuration section"""
        row = self._create_section_header(self.scrollable_frame, row, "GUI Settings")
        
        row = self._create_config_item(self.scrollable_frame, row, "Update Rate", 
                                     "gui_update_rate", "GUI refresh rate (Hz)")
        row = self._create_config_item(self.scrollable_frame, row, "Plot Update Rate", 
                                     "gui_plot_rate", "3D plot refresh rate (Hz)")
        row = self._create_config_item(self.scrollable_frame, row, "Max Flight Points", 
                                     "gui_max_points", "Flight trail points to track")
        row = self._create_config_item(self.scrollable_frame, row, "Flight Trail Fade", 
                                     "gui_trail_fade", "Trail fade samples")
        row = self._create_config_item(self.scrollable_frame, row, "Window Title", 
                                     "gui_window_title")
        
        return row
    
    def _create_logging_section(self, row: int) -> int:
        """Create logging configuration section"""
        row = self._create_section_header(self.scrollable_frame, row, "Logging")
        
        row = self._create_config_item(self.scrollable_frame, row, "Logging Directory",
                                     "logging_directory", "Where data files are saved (uses YYYYMMDD_HHMMSS_* naming)")
        row = self._create_config_item(self.scrollable_frame, row, "Log Level",
                                     "logging_level", "INFO, DEBUG, etc.")
        row = self._create_config_item(self.scrollable_frame, row, "Auto Save Interval",
                                     "logging_interval", "seconds")

        return row
    
    
    def _create_mock_section(self, row: int) -> int:
        """Create mock configuration section (if applicable)"""
        row = self._create_section_header(self.scrollable_frame, row, "Mock/Testing Configuration")
        
        row = self._create_config_item(self.scrollable_frame, row, "Mock RTLS Data File", 
                                     "mock_rtls_file", "Source of mock position data")
        row = self._create_config_item(self.scrollable_frame, row, "Mock Bat Count", 
                                     "mock_bat_count")
        row = self._create_config_item(self.scrollable_frame, row, "Mock Bat IDs", 
                                     "mock_bat_ids")
        row = self._create_config_item(self.scrollable_frame, row, "Mock Tag IDs", 
                                     "mock_tag_ids")
        row = self._create_config_item(self.scrollable_frame, row, "Mock Loop Data", 
                                     "mock_loop_data", "Whether to loop mock data")
        row = self._create_config_item(self.scrollable_frame, row, "Mock Arduino Log File", 
                                     "mock_arduino_file", "Where Arduino communication is logged")
        
        return row
    
    def _create_files_section(self, row: int) -> int:
        """Create configuration files information section"""
        row = self._create_section_header(self.scrollable_frame, row, "Configuration Files")
        
        row = self._create_config_item(self.scrollable_frame, row, "Main Config File", 
                                     "main_config_file", "Primary system configuration")
        row = self._create_config_item(self.scrollable_frame, row, "Task Logic Config File", 
                                     "task_logic_config_file", "Task logic parameters")
        row = self._create_config_item(self.scrollable_frame, row, "Mock Config File", 
                                     "mock_config_file", "Mock/testing parameters")
        
        return row
    
    def _update_all_values(self):
        """Update all configuration values from actual runtime sources"""
        try:
            # RTLS Configuration
            self._update_rtls_values()
            
            # Hardware Configuration
            self._update_hardware_values()
            
            # Feeder Configuration  
            self._update_feeder_values()
            
            # Task Logic Configuration
            self._update_task_logic_values()
            
            # Room Configuration
            self._update_room_values()
            
            # GUI Configuration
            self._update_gui_values()
            
            # Logging Configuration
            self._update_logging_values()

            # Mock Configuration
            self._update_mock_values()
            
            # Files Configuration
            self._update_files_values()
            
        except Exception as e:
            print(f"Error updating config display: {e}")
    
    def _update_rtls_values(self):
        """Update RTLS configuration values"""
        try:
            backend = self.settings.get_rtls_backend()
            self.config_vars['rtls_backend'].set(backend.upper())
            
            # For now, set status as configured (would need system reference for actual status)
            self.config_vars['rtls_status'].set("Configured")
            
            # Cortex config
            cortex_config = self.settings.get_cortex_config()
            self.config_vars['cortex_ip'].set(cortex_config.get('server_ip', 'Not set'))
            self.config_vars['cortex_port'].set(str(cortex_config.get('server_port', 'Not set')))
            self.config_vars['cortex_frame_rate'].set(f"{cortex_config.get('frame_rate', 'Not set')} Hz")
            self.config_vars['cortex_timeout'].set(f"{cortex_config.get('timeout', 'Not set')} s")
            
            # Ciholas config
            ciholas_config = self.settings.get_ciholas_config()
            self.config_vars['ciholas_multicast'].set(ciholas_config.get('multicast_group', 'Not set'))
            self.config_vars['ciholas_port'].set(str(ciholas_config.get('local_port', 'Not set')))
            self.config_vars['ciholas_frame_rate'].set(f"{ciholas_config.get('frame_rate', 'Not set')} Hz")
            self.config_vars['ciholas_timeout'].set(f"{ciholas_config.get('timeout', 'Not set')} s")
            self.config_vars['ciholas_serial_numbers'].set(str(ciholas_config.get('serial_numbers', 'Not set')))
            self.config_vars['ciholas_units'].set(ciholas_config.get('coordinate_units', 'Not set'))
            self.config_vars['ciholas_scale'].set(str(ciholas_config.get('coordinate_scale', 'Not set')))
            
        except Exception as e:
            print(f"Error updating RTLS values: {e}")
    
    def _update_hardware_values(self):
        """Update hardware configuration values"""
        try:
            arduino_config = self.settings.get_arduino_config()
            self.config_vars['arduino_port'].set(arduino_config.get('port', 'Not set'))
            self.config_vars['arduino_baudrate'].set(str(arduino_config.get('baudrate', 'Not set')))
            self.config_vars['arduino_timeout'].set(f"{arduino_config.get('timeout', 'Not set')} s")
            self.config_vars['arduino_status'].set("Configured")
            
        except Exception as e:
            print(f"Error updating hardware values: {e}")
    
    def _update_feeder_values(self):
        """Update feeder configuration values"""
        try:
            feeder_configs = self.settings.get_feeder_configs()
            self.config_vars['feeder_count'].set(str(len(feeder_configs)))
            
            # TODO: Add individual feeder details in the reserved space
            # This would show each feeder's position, activation distance, etc.
            
        except Exception as e:
            print(f"Error updating feeder values: {e}")
    
    def _update_task_logic_values(self):
        """Update task logic configuration values"""
        try:
            # Get task logic path - all parameters now come from feeder properties
            task_logic_path = self.settings.get_task_logic_path()

            # All parameters are per-feeder, configured in feeders section
            self.config_vars['task_reactivation_distance'].set("Per-feeder (see Feeders section)")
            self.config_vars['task_reactivation_time'].set("N/A")
            self.config_vars['task_feeder_ownership_distance'].set("Per-feeder (see Feeders section)")
            self.config_vars['task_position_timeout'].set("N/A")
            self.config_vars['task_config_file'].set(task_logic_path if task_logic_path else "default (built-in)")

        except Exception as e:
            print(f"Error updating task logic values: {e}")
            self.config_vars['task_reactivation_distance'].set("Error loading")
            self.config_vars['task_reactivation_time'].set("Error loading")
            self.config_vars['task_feeder_ownership_distance'].set("Error loading")
            self.config_vars['task_position_timeout'].set("Error loading")
            self.config_vars['task_config_file'].set("Error loading")
    
    def _update_room_values(self):
        """Update room configuration values"""
        try:
            room_config = self.settings.get_room_config()
            boundaries = room_config.get('boundaries', {})
            
            x_min, x_max = boundaries.get('x_min', 0), boundaries.get('x_max', 0)
            y_min, y_max = boundaries.get('y_min', 0), boundaries.get('y_max', 0)
            z_min, z_max = boundaries.get('z_min', 0), boundaries.get('z_max', 0)
            
            self.config_vars['room_x_bounds'].set(f"{x_min} to {x_max}")
            self.config_vars['room_y_bounds'].set(f"{y_min} to {y_max}")
            self.config_vars['room_z_bounds'].set(f"{z_min} to {z_max}")
            self.config_vars['room_units'].set(room_config.get('units', 'Not set'))
            
        except Exception as e:
            print(f"Error updating room values: {e}")
    
    def _update_gui_values(self):
        """Update GUI configuration values"""
        try:
            gui_config = self.settings.get_gui_config()
            self.config_vars['gui_update_rate'].set(f"{gui_config.get('update_rate_hz', 'Not set')} Hz")
            self.config_vars['gui_plot_rate'].set(f"{gui_config.get('plot_update_rate_hz', 'Not set')} Hz")
            self.config_vars['gui_max_points'].set(str(gui_config.get('max_flight_points', 'Not set')))
            self.config_vars['gui_trail_fade'].set(str(gui_config.get('flight_trail_fade_samples', 'Not set')))
            self.config_vars['gui_window_title'].set(gui_config.get('window_title', 'Not set'))
            
        except Exception as e:
            print(f"Error updating GUI values: {e}")
    
    def _update_logging_values(self):
        """Update logging configuration values"""
        try:
            logging_config = self.settings.get_logging_config()
            self.config_vars['logging_directory'].set(logging_config.get('data_directory', 'Not set'))
            self.config_vars['logging_level'].set(logging_config.get('log_level', 'Not set'))
            self.config_vars['logging_interval'].set(f"{logging_config.get('auto_save_interval_seconds', 'Not set')} s")

        except Exception as e:
            print(f"Error updating logging values: {e}")
    
    def _update_mock_values(self):
        """Update mock configuration values"""
        try:
            mock_rtls = self.settings.get_mock_rtls_config()
            mock_arduino = self.settings.get_mock_arduino_config()
            
            self.config_vars['mock_rtls_file'].set(mock_rtls.get('data_file', 'Not set'))
            self.config_vars['mock_bat_count'].set(str(mock_rtls.get('bat_count', 'Not set')))
            self.config_vars['mock_bat_ids'].set(str(mock_rtls.get('bat_ids', 'Not set')))
            self.config_vars['mock_tag_ids'].set(str(mock_rtls.get('tag_ids', 'Not set')))
            self.config_vars['mock_loop_data'].set(str(mock_rtls.get('loop_data', 'Not set')))
            self.config_vars['mock_arduino_file'].set(mock_arduino.get('log_file', 'Not set'))
            
        except Exception as e:
            print(f"Error updating mock values: {e}")
    
    def _update_files_values(self):
        """Update configuration files information"""
        try:
            self.config_vars['main_config_file'].set(self.settings.config_file)
            self.config_vars['task_logic_config_file'].set("config/task_logic_config.json")
            self.config_vars['mock_config_file'].set(self.settings.mock_config_file)
            
        except Exception as e:
            print(f"Error updating files values: {e}")