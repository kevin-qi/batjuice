"""
Session control panel with start/stop and data management.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from datetime import datetime
from typing import Callable, Optional


class SessionControls:
    """Session control panel for managing experiment sessions"""
    
    def __init__(self, parent, settings, on_start: Optional[Callable] = None, on_stop: Optional[Callable] = None):
        """
        Initialize session controls
        
        Args:
            parent: Parent tkinter widget
            settings: Settings instance
            on_start: Callback function when starting session
            on_stop: Callback function when stopping session
        """
        self.parent = parent
        self.settings = settings
        self.on_start = on_start
        self.on_stop = on_stop
        
        # Session state
        self.session_running = False
        self.session_start_time = None
        
        # Variables
        self.session_name = tk.StringVar()
        self.session_date = tk.StringVar()
        self.data_path = tk.StringVar()
        
        # Initialize values - use experiment name as default session name
        experiment_config = settings.config.get('experiment', {})
        experiment_name = experiment_config.get('name', 'BatFeeder_Session')
        self.session_name.set(experiment_name)
        self.session_date.set(datetime.now().strftime('%y%m%d'))

        # Convert data directory to absolute path
        import os
        data_dir = settings.get_data_directory()
        abs_data_dir = os.path.abspath(data_dir)
        self.data_path.set(abs_data_dir)
        
        # Setup controls
        self._setup_controls()
        
        # Start timer update loop
        self._update_timer()
    
    def _setup_controls(self):
        """Setup the session control layout"""
        # Main frame
        control_frame = ttk.LabelFrame(self.parent, text="Session", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Top row - Session info
        info_frame = ttk.Frame(control_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Session name
        name_frame = ttk.Frame(info_frame)
        name_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(name_frame, text="Session Name:").pack(side=tk.LEFT)
        name_entry = ttk.Entry(name_frame, textvariable=self.session_name, width=20)
        name_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Session date
        date_frame = ttk.Frame(info_frame)
        date_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(date_frame, text="Date (YYMMDD):").pack(side=tk.LEFT)
        date_entry = ttk.Entry(date_frame, textvariable=self.session_date, width=10)
        date_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Auto-update date button
        date_btn = ttk.Button(date_frame, text="Today", width=8,
                             command=lambda: self.session_date.set(datetime.now().strftime('%y%m%d')))
        date_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Middle row - Data path
        path_frame = ttk.Frame(control_frame)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(path_frame, text="Data Path:").pack(side=tk.LEFT)
        path_entry = ttk.Entry(path_frame, textvariable=self.data_path, width=40)
        path_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        browse_btn = ttk.Button(path_frame, text="Browse", command=self._browse_data_path)
        browse_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Bottom row - Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        # Start/Stop buttons
        self.start_btn = ttk.Button(button_frame, text="Start Session", 
                                   command=self._start_session, style="Accent.TButton")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Session", 
                                  command=self._stop_session, state="disabled")
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # Status indicator (dark theme) - green when ready
        self.status_label = ttk.Label(button_frame, text="Ready to start", foreground="#3BA55D")
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Timer label
        self.timer_label = ttk.Label(button_frame, text="00:00:00", foreground="#DCDDDE", 
                                     font=('TkDefaultFont', 10, 'bold'))
        self.timer_label.pack(side=tk.LEFT)
    
    def _browse_data_path(self):
        """Browse for data directory"""
        current_path = self.data_path.get()
        if not os.path.exists(current_path):
            current_path = os.path.expanduser("~")
            
        new_path = filedialog.askdirectory(
            title="Select Data Directory",
            initialdir=current_path
        )
        
        if new_path:
            self.data_path.set(new_path)
    
    def _start_session(self):
        """Start the session"""
        try:
            # Validate inputs
            if not self.session_name.get().strip():
                messagebox.showerror("Error", "Please enter a session name")
                return
                
            if not self.session_date.get().strip():
                messagebox.showerror("Error", "Please enter a date")
                return
            
            # Create data directory if it doesn't exist
            data_path = self.data_path.get()
            os.makedirs(data_path, exist_ok=True)
            
            # Update session state
            self.session_running = True
            self.session_start_time = datetime.now()
            
            # Update UI - yellow when running
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.status_label.config(text="Session Running", foreground="#FAA61A")
            
            # Update settings with current session info
            session_info = {
                'name': self.session_name.get(),
                'date': self.session_date.get(),
                'data_path': data_path,
                'start_time': self.session_start_time.isoformat()
            }
            
            # Call start callback
            if self.on_start:
                self.on_start(session_info)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start session: {e}")
    
    def _stop_session(self):
        """Stop the session"""
        try:
            # Update session state
            self.session_running = False
            self.session_start_time = None

            # Update UI
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.status_label.config(text="Session Stopped", foreground="red")
            self.timer_label.config(text="00:00:00")

            # Call stop callback
            if self.on_stop:
                self.on_stop()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop session: {e}")

    
    def _update_timer(self):
        """Update the session timer display"""
        if self.session_running and self.session_start_time:
            elapsed = datetime.now() - self.session_start_time
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            seconds = int(elapsed.total_seconds() % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.timer_label.config(text=time_str)
        
        # Schedule next update (every 1000ms)
        self.parent.after(1000, self._update_timer)
    
    def get_session_info(self) -> dict:
        """Get current session information"""
        return {
            'name': self.session_name.get(),
            'date': self.session_date.get(),
            'data_path': self.data_path.get(),
            'running': self.session_running
        }
    
    def is_running(self) -> bool:
        """Check if session is running"""
        return self.session_running