"""
Main GUI window for the bat feeder control system.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Dict, Any, Optional
from .feeder_panel import FeederPanel
from .bat_panel import BatPanel
from .flight_display_3d import FlightDisplay3D
from .session_controls import SessionControls
from .comprehensive_config_display import ComprehensiveConfigDisplay


class MainWindow:
    """Main application window"""
    
    def __init__(self, feeder_controller, settings, data_logger, event_logger):
        """
        Initialize main window
        
        Args:
            feeder_manager: FeederManager instance
            settings: Settings instance
            data_logger: DataLogger instance
            event_logger: EventLogger instance
        """
        self.feeder_controller = feeder_controller
        self.settings = settings
        self.data_logger = data_logger
        self.event_logger = event_logger
        
        # GUI update control
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        self.system_started = False
        self.system = None  # Will be set by main system
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Bat Feeder Control System")
        
        # Configure window size and position
        gui_config = settings.get_gui_config()
        window_size = gui_config.get('window_size', '1200x800')
        self.root.geometry(window_size)
        self.root.minsize(800, 600)
        
        # Setup GUI
        self._setup_gui()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _setup_gui(self):
        """Setup the GUI layout"""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Control tab
        control_frame = ttk.Frame(notebook)
        notebook.add(control_frame, text="Control")
        self._setup_control_tab(control_frame)
        
        # Configuration tab (comprehensive display of all config values)
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Configuration")
        self._setup_comprehensive_config_tab(config_frame)
        
        # Status bar
        self._setup_status_bar(main_frame)
    
    def _setup_control_tab(self, parent):
        """Setup the control tab"""
        # Session controls at top
        self.session_controls = SessionControls(
            parent, 
            self.settings,
            on_start=self._on_session_start,
            on_stop=self._on_session_stop
        )
        
        # Create main paned window for horizontal layout
        main_paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Left section - vertical paned window for feeders and bats
        left_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(left_paned, weight=1)
        
        # Top left - Feeders (compact)
        feeder_frame = ttk.LabelFrame(left_paned, text="Feeders", padding=5)
        left_paned.add(feeder_frame, weight=2)
        
        self.feeder_panel = FeederPanel(
            feeder_frame, 
            self.feeder_controller,
            self.settings,
            self.event_logger
        )
        
        # Bottom left - Bats (compact)
        bat_frame = ttk.LabelFrame(left_paned, text="Bats", padding=5)
        left_paned.add(bat_frame, weight=1)
        
        self.bat_panel = BatPanel(bat_frame, self.feeder_controller, self.settings)
        
        # Right section - Flight Paths Display (larger)
        flight_frame = ttk.LabelFrame(main_paned, text="Flight Paths", padding=3)
        main_paned.add(flight_frame, weight=3)  # Give even more space to flight display
        
        # Create flight display in the control tab
        room_config = self.settings.config.get('room', {})
        feeder_configs = self.settings.get_feeder_configs()
        self.flight_display = FlightDisplay3D(flight_frame, self.settings.get_gui_config(), 
                                            room_config, feeder_configs)
        
        # Set up position change callback to update flight display
        self.feeder_controller.set_position_change_callback(self._on_feeder_position_changed)
    
    def _setup_comprehensive_config_tab(self, parent):
        """Setup the comprehensive configuration display tab"""
        self.comprehensive_config_display = ComprehensiveConfigDisplay(parent, self.settings)
    
    def _setup_status_bar(self, parent):
        """Setup status bar"""
        self.status_frame = ttk.Frame(parent)
        self.status_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Status label
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        # Connection indicators
        self.connection_frame = ttk.Frame(self.status_frame)
        self.connection_frame.pack(side=tk.RIGHT)
        
        # Tracking connection
        ttk.Label(self.connection_frame, text="Tracking:").pack(side=tk.LEFT)
        self.tracking_status = ttk.Label(self.connection_frame, text="●", foreground="red")
        self.tracking_status.pack(side=tk.LEFT, padx=(2, 10))
        
        # Arduino connection
        ttk.Label(self.connection_frame, text="Arduino:").pack(side=tk.LEFT)
        self.arduino_status = ttk.Label(self.connection_frame, text="●", foreground="red")
        self.arduino_status.pack(side=tk.LEFT, padx=(2, 0))
    
    def start_gui_updates(self):
        """Start the GUI update thread"""
        if self.running:
            return
            
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        # Start component updates only if system is started
        if self.system_started:
            self.feeder_panel.start_updates()
            self.bat_panel.start_updates()
            self.flight_display.start_updates()
    
    def stop_gui_updates(self):
        """Stop the GUI update thread"""
        self.running = False
        
        # Stop component updates
        if hasattr(self, 'feeder_panel'):
            self.feeder_panel.stop_updates()
        if hasattr(self, 'bat_panel'):
            self.bat_panel.stop_updates()
        if hasattr(self, 'flight_display'):
            self.flight_display.stop_updates()
        
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)
    
    def _update_loop(self):
        """Main GUI update loop"""
        update_rate = self.settings.get_gui_config().get('update_rate_ms', 50)
        update_interval = update_rate / 1000.0
        
        while self.running:
            try:
                # Schedule GUI updates on main thread
                self.root.after_idle(self._update_gui)
                time.sleep(update_interval)
            except Exception as e:
                self.event_logger.error(f"GUI update error: {e}")
                time.sleep(0.1)
    
    def _update_gui(self):
        """Update GUI components (called on main thread)"""
        try:
            # Update status bar
            self._update_status_bar()
            
        except Exception as e:
            self.event_logger.error(f"GUI component update error: {e}")
    
    def _update_status_bar(self):
        """Update status bar information"""
        if self.system_started:
            # Update status message
            bat_count = len(self.feeder_controller.get_bat_states())
            self.status_label.config(text=f"Running - {bat_count} bats tracked")
            
            # Update connection indicators (simplified - in real app would check actual connections)
            self.tracking_status.config(foreground="green")
            self.arduino_status.config(foreground="green")
        else:
            self.status_label.config(text="Ready - Click Start Session to begin")
            self.tracking_status.config(foreground="red")
            self.arduino_status.config(foreground="red")
    
    
    def update_flight_display(self, bat_states: Dict):
        """Update flight display with new data"""
        if hasattr(self, 'flight_display') and self.system_started:
            self.flight_display.update_positions(bat_states)
    
    def set_connection_status(self, component: str, connected: bool):
        """Update connection status indicators"""
        color = "green" if connected else "red"
        
        if component == "tracking":
            self.tracking_status.config(foreground=color)
        elif component == "arduino":
            self.arduino_status.config(foreground=color)
    
    def show_error(self, title: str, message: str):
        """Show error dialog"""
        messagebox.showerror(title, message)
    
    def show_info(self, title: str, message: str):
        """Show info dialog"""
        messagebox.showinfo(title, message)
    
    def _on_feeder_position_changed(self, updated_feeder_configs):
        """Handle feeder position changes - update flight display and feeder panel"""
        try:
            # Update flight display with new feeder positions
            if hasattr(self, 'flight_display'):
                self.flight_display.update_feeder_positions(updated_feeder_configs)
            
            # Update feeder panel displays
            if hasattr(self, 'feeder_panel'):
                for feeder_config in updated_feeder_configs:
                    self.feeder_panel._update_position_display(feeder_config.feeder_id)
                    
        except Exception as e:
            self.event_logger.error(f"Error handling feeder position change: {e}")

    def _on_closing(self):
        """Handle window close event"""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            self.stop_gui_updates()
            self.root.destroy()
    
    def run(self):
        """Run the GUI main loop"""
        self.start_gui_updates()
        self.root.mainloop()
    
    def _on_session_start(self, session_info: dict):
        """Handle session start"""
        try:
            # Update data logger with session info
            self.data_logger.update_session_info(session_info)
            
            # Log session start
            self.data_logger.log_session_start()
            
            # Start system components
            if self.system:
                self.system.start_components()
            
            self.system_started = True
            self.event_logger.info(f"Session started: {session_info['name']}")
            
            # Start component updates
            self.feeder_panel.start_updates()
            self.bat_panel.start_updates()
            self.flight_display.start_updates()
            
        except Exception as e:
            self.event_logger.error(f"Error starting session: {e}")
    
    def _on_session_stop(self):
        """Handle session stop"""
        try:
            # Stop system components
            if self.system:
                self.system.stop_components()
            
            # Log session end
            self.data_logger.log_session_end()
            
            self.system_started = False
            self.event_logger.info("Session stopped")
            
            # Stop component updates
            self.feeder_panel.stop_updates()
            self.bat_panel.stop_updates()
            self.flight_display.stop_updates()
            
        except Exception as e:
            self.event_logger.error(f"Error stopping session: {e}")