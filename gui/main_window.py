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
from .flight_display_2d import FlightDisplay2D
from .flight_data_manager import FlightDataManager
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

        # Create shared flight data manager (thread-safe)
        self.flight_data_manager = FlightDataManager(max_points=10000)

        # Create main window
        self.root = tk.Tk()
        self.root.title("Bat Feeder Control System")

        # Configure window size and position (21% larger than original)
        gui_config = settings.get_gui_config()
        window_size = gui_config.get('window_size', '1742x968')  # 1440*1.21 x 800*1.21

        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 1742) // 2
        y = (screen_height - 968) // 2

        # Ensure window starts fully visible (not cut off)
        if y < 0:
            y = 0
        if x < 0:
            x = 0

        self.root.geometry(f'{window_size}+{x}+{y}')
        self.root.minsize(1162, 726)  # 960*1.21 x 600*1.21

        # Apply modern theme and styling
        self._apply_modern_theme()

        # Setup GUI
        self._setup_gui()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _apply_modern_theme(self):
        """Apply modern dark theme to the GUI"""
        style = ttk.Style()

        # Use clam theme as base (more modern than default)
        try:
            style.theme_use('clam')
        except:
            pass  # Fall back to default if clam not available

        # Cohesive Dark Color Palette
        BG_COLOR = '#2B2D31'        # Dark background
        SURFACE_COLOR = '#36393F'   # Surface/card color
        ELEVATED_COLOR = '#40444B'  # Elevated elements (tables, inputs)
        ACCENT_COLOR = '#5865F2'    # Purple-blue accent
        TEXT_PRIMARY = '#DCDDDE'    # Primary text
        TEXT_SECONDARY = '#B9BBBE'  # Secondary text
        BORDER_COLOR = '#1E1F22'    # Dark borders
        SUCCESS_COLOR = '#3BA55D'   # Green
        ERROR_COLOR = '#ED4245'     # Red
        HOVER_COLOR = '#4752C4'     # Darker accent for hover

        # Configure root window
        self.root.configure(bg=BG_COLOR)

        # Frame styles - all dark, uniform background
        style.configure('TFrame', background=BG_COLOR)
        style.configure('Card.TFrame', background=BG_COLOR, relief='flat')

        # Label styles - light text on dark background, uniform
        style.configure('TLabel', background=BG_COLOR, foreground=TEXT_PRIMARY,
                       font=('Segoe UI', 9))
        style.configure('Header.TLabel', background=BG_COLOR, foreground=TEXT_SECONDARY,
                       font=('Segoe UI', 10, 'bold'), padding=(0, 5, 0, 5))
        style.configure('CardLabel.TLabel', background=BG_COLOR, foreground=TEXT_PRIMARY)

        # Button styles - elevated with accent
        style.configure('TButton',
                       background=ELEVATED_COLOR,
                       foreground=TEXT_PRIMARY,
                       borderwidth=0,
                       padding=8,
                       relief='flat',
                       font=('Segoe UI', 9))
        style.map('TButton',
                 background=[('active', ACCENT_COLOR), ('!active', ELEVATED_COLOR)],
                 foreground=[('active', '#FFFFFF'), ('!active', TEXT_PRIMARY)])

        # Notebook (tabs) style - dark theme, minimalistic, no focus rectangle
        style.configure('TNotebook', background=BG_COLOR, borderwidth=0)
        style.configure('TNotebook.Tab',
                       background=SURFACE_COLOR,
                       foreground=TEXT_SECONDARY,
                       padding=[16, 10],
                       font=('Segoe UI', 9),
                       borderwidth=0,
                       focuscolor='')
        style.map('TNotebook.Tab',
                 background=[('selected', SURFACE_COLOR), ('!selected', SURFACE_COLOR)],
                 foreground=[('selected', ACCENT_COLOR), ('!selected', TEXT_SECONDARY)],
                 padding=[('selected', [16, 10]), ('!selected', [16, 10])],
                 focuscolor=[('selected', ''), ('!selected', '')])

        # Treeview (table) styles - cohesive dark
        style.configure('Treeview',
                       background=ELEVATED_COLOR,
                       foreground=TEXT_PRIMARY,
                       fieldbackground=ELEVATED_COLOR,
                       borderwidth=0,
                       rowheight=28,
                       font=('Segoe UI', 9))
        style.configure('Treeview.Heading',
                       background=SURFACE_COLOR,
                       foreground=TEXT_SECONDARY,
                       relief='flat',
                       borderwidth=0,
                       font=('Segoe UI', 9, 'bold'))
        style.map('Treeview',
                 background=[('selected', ACCENT_COLOR)],
                 foreground=[('selected', '#FFFFFF')])
        style.map('Treeview.Heading',
                 background=[('active', SURFACE_COLOR)],
                 foreground=[('active', TEXT_PRIMARY)])

        # Entry and Spinbox styles - elevated dark
        style.configure('TEntry',
                       fieldbackground=ELEVATED_COLOR,
                       foreground=TEXT_PRIMARY,
                       bordercolor=BORDER_COLOR,
                       lightcolor=BORDER_COLOR,
                       darkcolor=BORDER_COLOR,
                       borderwidth=1,
                       insertcolor=TEXT_PRIMARY)
        style.configure('TSpinbox',
                       fieldbackground=ELEVATED_COLOR,
                       foreground=TEXT_PRIMARY,
                       bordercolor=BORDER_COLOR,
                       arrowcolor=TEXT_PRIMARY,
                       borderwidth=1)
        style.map('TSpinbox',
                 fieldbackground=[('readonly', ELEVATED_COLOR)],
                 foreground=[('readonly', TEXT_PRIMARY)])

        # LabelFrame style - dark, uniform background
        style.configure('TLabelframe',
                       background=BG_COLOR,
                       borderwidth=1,
                       relief='flat',
                       bordercolor=BORDER_COLOR)
        style.configure('TLabelframe.Label',
                       background=BG_COLOR,
                       foreground=TEXT_SECONDARY,
                       font=('Segoe UI', 10, 'bold'))

        # Checkbutton style - minimalistic with checkmark indicator, no focus rectangle
        style.configure('TCheckbutton',
                       background=BG_COLOR,
                       foreground=TEXT_PRIMARY,
                       focuscolor='',
                       borderwidth=0,
                       indicatorcolor=ELEVATED_COLOR,
                       indicatorbackground=ELEVATED_COLOR,
                       indicatordiameter=12)
        style.map('TCheckbutton',
                 background=[('active', BG_COLOR)],
                 foreground=[('active', ACCENT_COLOR)],
                 indicatorcolor=[('selected', ACCENT_COLOR), ('!selected', ELEVATED_COLOR)],
                 focuscolor=[('selected', ''), ('!selected', '')])

        # Combobox style - dark
        style.configure('TCombobox',
                       fieldbackground=ELEVATED_COLOR,
                       background=ELEVATED_COLOR,
                       foreground=TEXT_PRIMARY,
                       bordercolor=BORDER_COLOR,
                       arrowcolor=TEXT_PRIMARY,
                       borderwidth=1)
        style.map('TCombobox',
                 fieldbackground=[('readonly', ELEVATED_COLOR)],
                 foreground=[('readonly', TEXT_PRIMARY)])

        # Scrollbar style - dark
        style.configure('Vertical.TScrollbar',
                       background=SURFACE_COLOR,
                       troughcolor=BG_COLOR,
                       borderwidth=0,
                       arrowcolor=TEXT_SECONDARY)
        style.map('Vertical.TScrollbar',
                 background=[('active', ACCENT_COLOR)])

        # PanedWindow style - dark
        style.configure('TPanedwindow', background=BG_COLOR)
        style.configure('Sash', sashthickness=3, background=BORDER_COLOR)
        
    def _setup_gui(self):
        """Setup the GUI layout"""
        # Create main frame with better padding
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Control tab
        control_frame = ttk.Frame(self.notebook)
        self.notebook.add(control_frame, text="Control")
        self._setup_control_tab(control_frame)

        # Configuration tab (comprehensive display of all config values)
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Configuration")
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
        main_paned.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

        # Left section - vertical paned window for feeders and bats (wider)
        left_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(left_paned, weight=3)

        # Top left - Feeders card (increased height)
        feeder_container, feeder_content = self._create_card_panel(left_paned, "Feeders")
        left_paned.add(feeder_container, weight=3)

        self.feeder_panel = FeederPanel(
            feeder_content,
            self.feeder_controller,
            self.settings,
            self.event_logger
        )

        # Bottom left - Bats card (reduced height)
        bat_container, bat_content = self._create_card_panel(left_paned, "Bats")
        left_paned.add(bat_container, weight=2)

        self.bat_panel = BatPanel(bat_content, self.feeder_controller, self.settings)

        # Right section - Flight Paths card (narrower) - 2D real-time view
        flight_container, flight_content = self._create_card_panel(main_paned, "Flight Paths (2D)")
        main_paned.add(flight_container, weight=7)

        # Create 2D flight display in the control tab (real-time)
        room_config = self.settings.config.get('room', {})
        feeder_configs = self.settings.get_feeder_configs()
        self.flight_display_2d = FlightDisplay2D(
            flight_content,
            self.settings.get_gui_config(),
            room_config,
            feeder_configs,
            self.flight_data_manager
        )

        # Set up position change callback to update flight display
        self.feeder_controller.set_position_change_callback(self._on_feeder_position_changed)

    def _create_card_panel(self, parent, title):
        """Create a modern card-style panel with header - returns (container, content)"""
        # Main container frame (this gets added to parent/PanedWindow)
        container = ttk.Frame(parent, style='Card.TFrame')

        # Header label
        if title:
            header = ttk.Label(container, text=title.upper(), style='Header.TLabel')
            header.pack(fill=tk.X, padx=12, pady=(8, 0))

        # Content frame where child widgets will be placed
        content = ttk.Frame(container, style='Card.TFrame')
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        return container, content
    
    def _setup_comprehensive_config_tab(self, parent):
        """Setup the comprehensive configuration display tab"""
        self.comprehensive_config_display = ComprehensiveConfigDisplay(parent, self.settings)
    
    def _setup_status_bar(self, parent):
        """Setup modern dark status bar"""
        self.status_frame = ttk.Frame(parent)
        self.status_frame.pack(fill=tk.X, pady=(10, 0))

        # Status label with dark theme
        self.status_label = ttk.Label(self.status_frame, text="Ready",
                                     font=('Segoe UI', 9), foreground='#B9BBBE')
        self.status_label.pack(side=tk.LEFT)

        # Connection indicators with dark theme
        self.connection_frame = ttk.Frame(self.status_frame)
        self.connection_frame.pack(side=tk.RIGHT)

        # Tracking connection
        ttk.Label(self.connection_frame, text="Tracking",
                 font=('Segoe UI', 9), foreground='#B9BBBE').pack(side=tk.LEFT, padx=(0, 4))
        self.tracking_status = ttk.Label(self.connection_frame, text="●",
                                        foreground="#ED4245", font=('Segoe UI', 12))
        self.tracking_status.pack(side=tk.LEFT, padx=(0, 15))

        # Arduino connection
        ttk.Label(self.connection_frame, text="Arduino",
                 font=('Segoe UI', 9), foreground='#B9BBBE').pack(side=tk.LEFT, padx=(0, 4))
        self.arduino_status = ttk.Label(self.connection_frame, text="●",
                                       foreground="#ED4245", font=('Segoe UI', 12))
        self.arduino_status.pack(side=tk.LEFT)
    
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
            self.flight_display_2d.start_updates()  # Only 2D is real-time
    
    def stop_gui_updates(self):
        """Stop the GUI update thread"""
        self.running = False
        
        # Stop component updates
        if hasattr(self, 'feeder_panel'):
            self.feeder_panel.stop_updates()
        if hasattr(self, 'bat_panel'):
            self.bat_panel.stop_updates()
        if hasattr(self, 'flight_display_2d'):
            self.flight_display_2d.stop_updates()
        # Note: flight_display_3d has no updates to stop (manual refresh)
        
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)
    
    def _update_loop(self):
        """Main GUI update loop"""
        refresh_rate_hz = self.settings.get_gui_config().get('refresh_rate_hz', 10)
        update_interval = 1.0 / refresh_rate_hz
        
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

            # Update flight display with current bat states
            # Note: This runs at GUI update rate (typically 20 Hz)
            # FlightDataManager will further downsample to 10 Hz for display
            if self.system_started and hasattr(self, 'system'):
                bat_states = self.system.feeder_controller.get_bat_states()
                self.update_flight_display(bat_states)

        except Exception as e:
            self.event_logger.error(f"GUI component update error: {e}")
    
    def _update_status_bar(self):
        """Update status bar information"""
        if self.system_started:
            # Update status message
            bat_count = len(self.feeder_controller.get_bat_states())
            self.status_label.config(text=f"Running - {bat_count} bats tracked")

            # Update connection indicators with dark theme colors
            self.tracking_status.config(foreground="#3BA55D")  # Green
            self.arduino_status.config(foreground="#3BA55D")  # Green
        else:
            self.status_label.config(text="Ready - Click Start Session to begin")
            self.tracking_status.config(foreground="#ED4245")  # Red
            self.arduino_status.config(foreground="#ED4245")  # Red
    
    
    def update_flight_display(self, bat_states: Dict):
        """Update flight display with new data (thread-safe)"""
        if self.system_started:
            # Add to shared data manager (thread-safe with 10x downsampling)
            for bat_id, bat_state in bat_states.items():
                if bat_state.last_position:
                    self.flight_data_manager.add_position(bat_id, bat_state.last_position)
            # Note: 2D display auto-updates via its thread
            # Note: 3D display updates on manual refresh
    
    def set_connection_status(self, component: str, connected: bool):
        """Update connection status indicators with dark theme colors"""
        color = "#3BA55D" if connected else "#ED4245"  # Green or Red

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
            if hasattr(self, 'flight_display_2d'):
                self.flight_display_2d.update_feeder_positions(updated_feeder_configs)

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
            self.flight_display_2d.start_updates()  # Only 2D is real-time
            
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
            self.flight_display_2d.stop_updates()  # Only 2D has updates to stop
            
        except Exception as e:
            self.event_logger.error(f"Error stopping session: {e}")