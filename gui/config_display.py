"""
Configuration display panel for showing current system settings to user.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any


class ConfigDisplay:
    """Displays current system configuration for user confirmation"""
    
    def __init__(self, parent, settings):
        """
        Initialize configuration display
        
        Args:
            parent: Parent tkinter widget
            settings: Settings object containing configuration
        """
        self.parent = parent
        self.settings = settings
        
        # Create main frame
        self.frame = ttk.LabelFrame(parent, text="System Configuration", padding="5")
        self.config_vars = {}
        
        self._create_widgets()
        self._update_display()
    
    def _create_widgets(self):
        """Create the configuration display widgets"""
        # RTLS System
        rtls_frame = ttk.LabelFrame(self.frame, text="Position Tracking", padding="3")
        rtls_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.config_vars['rtls_backend'] = tk.StringVar()
        ttk.Label(rtls_frame, text="RTLS Backend:").grid(row=0, column=0, sticky="w")
        ttk.Label(rtls_frame, textvariable=self.config_vars['rtls_backend'], 
                 font=("TkDefaultFont", 9, "bold")).grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        # Connection info
        self.config_vars['rtls_connection'] = tk.StringVar()
        ttk.Label(rtls_frame, text="Connection:").grid(row=1, column=0, sticky="w")
        ttk.Label(rtls_frame, textvariable=self.config_vars['rtls_connection']).grid(row=1, column=1, sticky="w", padx=(10, 0))
        
        # Room boundaries
        room_frame = ttk.LabelFrame(self.frame, text="Room Setup", padding="3")
        room_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.config_vars['room_bounds'] = tk.StringVar()
        ttk.Label(room_frame, text="Boundaries:").grid(row=0, column=0, sticky="w")
        ttk.Label(room_frame, textvariable=self.config_vars['room_bounds']).grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        self.config_vars['room_units'] = tk.StringVar()
        ttk.Label(room_frame, text="Units:").grid(row=1, column=0, sticky="w")
        ttk.Label(room_frame, textvariable=self.config_vars['room_units']).grid(row=1, column=1, sticky="w", padx=(10, 0))
        
        # Hardware
        hw_frame = ttk.LabelFrame(self.frame, text="Hardware", padding="3")
        hw_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.config_vars['arduino_port'] = tk.StringVar()
        ttk.Label(hw_frame, text="Arduino Port:").grid(row=0, column=0, sticky="w")
        ttk.Label(hw_frame, textvariable=self.config_vars['arduino_port']).grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        self.config_vars['feeder_count'] = tk.StringVar()
        ttk.Label(hw_frame, text="Feeders:").grid(row=1, column=0, sticky="w")
        ttk.Label(hw_frame, textvariable=self.config_vars['feeder_count']).grid(row=1, column=1, sticky="w", padx=(10, 0))
        
        # Data logging
        data_frame = ttk.LabelFrame(self.frame, text="Data Logging", padding="3")
        data_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.config_vars['data_directory'] = tk.StringVar()
        ttk.Label(data_frame, text="Directory:").grid(row=0, column=0, sticky="w")
        ttk.Label(data_frame, textvariable=self.config_vars['data_directory']).grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        # GUI settings
        gui_frame = ttk.LabelFrame(self.frame, text="GUI Settings", padding="3")
        gui_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=2)
        
        self.config_vars['update_rate'] = tk.StringVar()
        ttk.Label(gui_frame, text="Update Rate:").grid(row=0, column=0, sticky="w")
        ttk.Label(gui_frame, textvariable=self.config_vars['update_rate']).grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        # Refresh button
        ttk.Button(self.frame, text="Refresh Config", 
                  command=self._update_display).grid(row=5, column=0, columnspan=2, pady=5)
        
        # Configure grid weights
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
    
    def _update_display(self):
        """Update the configuration display with current settings"""
        try:
            # RTLS Backend
            backend = self.settings.get_rtls_backend().upper()
            self.config_vars['rtls_backend'].set(backend)
            
            # Connection info
            if backend == "CORTEX":
                cortex_config = self.settings.get_cortex_config()
                conn_info = f"{cortex_config.get('server_ip', 'Unknown')}:{cortex_config.get('server_port', 'Unknown')}"
                frame_rate = cortex_config.get('frame_rate', 120)
                self.config_vars['rtls_connection'].set(f"{conn_info} @ {frame_rate}Hz")
            elif backend == "CIHOLAS":
                ciholas_config = self.settings.get_ciholas_config()
                conn_info = f"{ciholas_config.get('server_ip', 'Unknown')}:{ciholas_config.get('server_port', 'Unknown')}"
                frame_rate = ciholas_config.get('frame_rate', 100)
                self.config_vars['rtls_connection'].set(f"{conn_info} @ {frame_rate}Hz")
            else:
                self.config_vars['rtls_connection'].set("Mock Data")
            
            # Room boundaries
            room_config = self.settings.get_room_config()
            boundaries = room_config.get('boundaries', {})
            x_range = f"X: {boundaries.get('x_min', 0)}-{boundaries.get('x_max', 5)}"
            y_range = f"Y: {boundaries.get('y_min', 0)}-{boundaries.get('y_max', 3)}"
            z_range = f"Z: {boundaries.get('z_min', 0)}-{boundaries.get('z_max', 2.5)}"
            self.config_vars['room_bounds'].set(f"{x_range}, {y_range}, {z_range}")
            self.config_vars['room_units'].set(room_config.get('units', 'meters'))
            
            # Hardware
            arduino_config = self.settings.get_arduino_config()
            self.config_vars['arduino_port'].set(arduino_config.get('port', 'Unknown'))
            
            feeder_configs = self.settings.get_feeder_configs()
            self.config_vars['feeder_count'].set(f"{len(feeder_configs)} configured")
            
            # Data logging
            logging_config = self.settings.get_logging_config()
            self.config_vars['data_directory'].set(logging_config.get('data_directory', 'data'))
            
            # GUI settings
            gui_config = self.settings.get_gui_config()
            update_rate = gui_config.get('update_rate_hz', 30)
            plot_rate = gui_config.get('plot_update_rate_hz', 10)
            self.config_vars['update_rate'].set(f"GUI: {update_rate}Hz, Plot: {plot_rate}Hz")
            
        except Exception as e:
            print(f"Error updating config display: {e}")
    
    def pack(self, **kwargs):
        """Pack the configuration frame"""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Grid the configuration frame"""
        self.frame.grid(**kwargs)
    
    def get_frame(self):
        """Get the main frame widget"""
        return self.frame