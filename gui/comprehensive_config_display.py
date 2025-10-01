"""
Configuration Display

Displays configuration values as loaded by the actual code, using the same
getter methods to verify configuration is being read correctly.
"""
import tkinter as tk
from tkinter import ttk


class ComprehensiveConfigDisplay:
    """Displays configuration values using actual code getter methods"""

    def __init__(self, parent, settings, mock_mode=False):
        """
        Initialize configuration display

        Args:
            parent: Parent tkinter widget
            settings: Settings object containing configuration
            mock_mode: Whether system is running in mock mode
        """
        self.parent = parent
        self.settings = settings
        self.mock_mode = mock_mode

        # Create main scrollable frame with dark theme background
        canvas = tk.Canvas(parent, bg='#2B2D31', highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Display configuration
        self._display_configuration()

    def _display_configuration(self):
        """Display all configuration values using actual getter methods"""
        row = 0

        # Title
        title = ttk.Label(self.scrollable_frame, text="Configuration",
                         font=("TkDefaultFont", 16, "bold"))
        title.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 5))
        row += 1

        # Config file path (absolute)
        import os
        abs_path = os.path.abspath(self.settings.config_file)
        file_path = ttk.Label(self.scrollable_frame,
                             text=f"File: {abs_path}",
                             font=("TkDefaultFont", 9), foreground="#B9BBBE")
        file_path.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 20))
        row += 1

        # Experiment section
        row = self._section_header(row, "Experiment")
        experiment = self.settings.config.get("experiment", {})
        row = self._add_item(row, "Name", experiment.get("name", "Not set"))
        row = self._add_item(row, "Description", experiment.get("description", "Not set"))
        row = self._add_item(row, "Data Directory", self.settings.get_data_directory())

        task_logic = self.settings.get_task_logic_path()
        row = self._add_item(row, "Task Logic File", task_logic if task_logic else "None")
        row += 1

        # Feeders section
        row = self._section_header(row, "Feeders")
        feeders = self.settings.get_feeder_configs()
        row = self._add_item(row, "Count", str(len(feeders)))

        for feeder in feeders:
            row = self._subsection_header(row, f"Feeder {feeder.feeder_id}")
            row = self._add_item(row, "Position (x, y, z)",
                               f"({feeder.x_position:.2f}, {feeder.y_position:.2f}, {feeder.z_position:.2f})")
            row = self._add_item(row, "Activation Radius", f"{feeder.activation_radius} m")
            row = self._add_item(row, "Reactivation Distance", f"{feeder.reactivation_distance} m")
            row = self._add_item(row, "Duration", f"{feeder.duration_ms} ms")
            row = self._add_item(row, "Speed", str(feeder.speed))
            row = self._add_item(row, "Probability", str(feeder.probability))
        row += 1

        # RTLS System section
        row = self._section_header(row, "RTLS System")
        rtls_backend = self.settings.get_rtls_backend()
        row = self._add_item(row, "Backend", rtls_backend.upper())

        if rtls_backend == "cortex":
            cortex = self.settings.get_cortex_config()
            row = self._add_item(row, "Server IP", cortex.get("server_ip", "Not set"))
            row = self._add_item(row, "Server Port", str(cortex.get("server_port", "Not set")))
            row = self._add_item(row, "Timeout", f"{cortex.get('timeout', 'Not set')} s")
            row = self._add_item(row, "Frame Rate", f"{cortex.get('frame_rate', 'Not set')} Hz")
        elif rtls_backend == "ciholas":
            ciholas = self.settings.get_ciholas_config()
            row = self._add_item(row, "Multicast Group", ciholas.get("multicast_group", "Not set"))
            row = self._add_item(row, "Local Port", str(ciholas.get("local_port", "Not set")))
            row = self._add_item(row, "Timeout", f"{ciholas.get('timeout', 'Not set')} s")
            row = self._add_item(row, "Frame Rate", f"{ciholas.get('frame_rate', 'Not set')} Hz")
            row = self._add_item(row, "Serial Numbers", str(ciholas.get("serial_numbers", "Not set")))
            row = self._add_item(row, "Sync Serial Number", str(ciholas.get("sync_serial_number", "Not set")))
            row = self._add_item(row, "Coordinate Units", ciholas.get("coordinate_units", "Not set"))
            row = self._add_item(row, "Coordinate Scale", str(ciholas.get("coordinate_scale", "Not set")))
        row += 1

        # Room section
        row = self._section_header(row, "Room")
        room = self.settings.get_room_config()
        boundaries = room.get("boundaries", {})
        row = self._add_item(row, "X Range",
                           f"{boundaries.get('x_min', 0)} to {boundaries.get('x_max', 0)}")
        row = self._add_item(row, "Y Range",
                           f"{boundaries.get('y_min', 0)} to {boundaries.get('y_max', 0)}")
        row = self._add_item(row, "Z Range",
                           f"{boundaries.get('z_min', 0)} to {boundaries.get('z_max', 0)}")
        row = self._add_item(row, "Units", room.get("units", "Not set"))
        row += 1

        # GUI section
        row = self._section_header(row, "GUI")
        gui = self.settings.get_gui_config()
        row = self._add_item(row, "Refresh Rate", f"{gui.get('refresh_rate_hz', 10)} Hz")
        row = self._add_item(row, "Stationary Threshold", f"{gui.get('stationary_threshold', 0.5)} m/s")
        row = self._add_item(row, "Position Timeout", f"{gui.get('position_timeout_gui', 1.0)} s")
        row += 1

        # Arduino section
        row = self._section_header(row, "Arduino")
        arduino = self.settings.get_arduino_config()
        row = self._add_item(row, "Port", arduino.get("port", "Not set"))
        row = self._add_item(row, "Baudrate", str(arduino.get("baudrate", "Not set")))
        row = self._add_item(row, "Timeout", f"{arduino.get('timeout', 'Not set')} s")
        row += 1

        # Logging section
        row = self._section_header(row, "Logging")
        logging = self.settings.get_logging_config()
        row = self._add_item(row, "Log Level", logging.get("log_level", "Not set"))
        row += 1

        # Mock section (only if in mock mode)
        if self.mock_mode:
            row = self._section_header(row, "Mock Configuration")
            mock_rtls = self.settings.get_mock_rtls_config()
            mock_arduino = self.settings.get_mock_arduino_config()
            row = self._add_item(row, "RTLS Data File", mock_rtls.get("data_file", "Not set"))
            row = self._add_item(row, "Bat IDs", str(mock_rtls.get("bat_ids", "Not set")))
            row = self._add_item(row, "Arduino Log File", mock_arduino.get("log_file", "Not set"))

    def _section_header(self, row, title):
        """Add a section header"""
        ttk.Separator(self.scrollable_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(10, 5))
        row += 1

        label = ttk.Label(self.scrollable_frame, text=title,
                         font=("TkDefaultFont", 12, "bold"))
        label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 5))
        row += 1

        return row

    def _subsection_header(self, row, title):
        """Add a subsection header"""
        label = ttk.Label(self.scrollable_frame, text=title,
                         font=("TkDefaultFont", 10, "bold"), foreground="#5865F2")
        label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(5, 3), padx=(20, 0))
        row += 1

        return row

    def _add_item(self, row, label, value):
        """Add a configuration item"""
        label_widget = ttk.Label(self.scrollable_frame, text=f"{label}:")
        label_widget.grid(row=row, column=0, sticky="w", padx=(40, 10), pady=1)

        value_widget = ttk.Label(self.scrollable_frame, text=str(value),
                                font=("TkDefaultFont", 9, "bold"))
        value_widget.grid(row=row, column=1, sticky="w", pady=1)

        return row + 1