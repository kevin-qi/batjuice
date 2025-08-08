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
        
        # Variables
        self.session_name = tk.StringVar()
        self.session_date = tk.StringVar()
        self.data_path = tk.StringVar()
        
        # Initialize values
        session_config = settings.config.get('session', {})
        self.session_name.set(session_config.get('default_name', 'BatFeeder_Session'))
        self.session_date.set(datetime.now().strftime('%y%m%d'))
        self.data_path.set(session_config.get('default_data_path', './data'))
        
        # Setup controls
        self._setup_controls()
    
    def _setup_controls(self):
        """Setup the session control layout"""
        # Main frame
        control_frame = ttk.LabelFrame(self.parent, text="Session Control", padding=10)
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
        
        # Status indicator
        self.status_label = ttk.Label(button_frame, text="Ready to start", foreground="blue")
        self.status_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # Export button
        export_btn = ttk.Button(button_frame, text="Export Data", command=self._export_data)
        export_btn.pack(side=tk.RIGHT)
    
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
            
            # Update UI
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.status_label.config(text="Session Running", foreground="green")
            
            # Update settings with current session info
            session_info = {
                'name': self.session_name.get(),
                'date': self.session_date.get(),
                'data_path': data_path,
                'start_time': datetime.now().isoformat()
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
            
            # Update UI
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.status_label.config(text="Session Stopped", foreground="red")
            
            # Call stop callback
            if self.on_stop:
                self.on_stop()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop session: {e}")
    
    def _export_data(self):
        """Export session data to consolidated format"""
        try:
            if not self.session_running:
                messagebox.showwarning("Warning", "No active session to export")
                return
                
            # Generate filename
            name = self.session_name.get().replace(' ', '_')
            date = self.session_date.get()
            filename = f"{name}_{date}.txt"
            
            # Ask for save location
            filepath = filedialog.asksaveasfilename(
                title="Export Session Data",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfilename=filename
            )
            
            if filepath:
                self._create_consolidated_export(filepath)
                messagebox.showinfo("Success", f"Data exported to: {filepath}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {e}")
    
    def _create_consolidated_export(self, filepath: str):
        """Create consolidated data export for pandas"""
        # This will be implemented to combine all log files into a single
        # pandas-friendly format
        with open(filepath, 'w') as f:
            f.write("# Bat Feeder Session Data Export\n")
            f.write(f"# Session: {self.session_name.get()}\n")
            f.write(f"# Date: {self.session_date.get()}\n")
            f.write(f"# Export Time: {datetime.now().isoformat()}\n")
            f.write("\n")
            f.write("timestamp,event_type,bat_id,feeder_id,x_pos,y_pos,z_pos,reward_delivered,manual,notes\n")
            
            # TODO: Implement actual data consolidation from log files
            # This would read from the CSV files and combine them
            f.write("# Data consolidation not yet implemented\n")
    
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