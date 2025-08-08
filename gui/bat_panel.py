"""
Bat monitoring panel for the GUI.
"""
import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Optional


class BatPanel:
    """Panel for monitoring bat states"""
    
    def __init__(self, parent, feeder_manager):
        """
        Initialize bat panel
        
        Args:
            parent: Parent tkinter widget
            feeder_manager: FeederManager instance
        """
        self.parent = parent
        self.feeder_manager = feeder_manager
        
        # Update control
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        
        # Setup panel
        self._setup_panel()
    
    def _setup_panel(self):
        """Setup the bat panel layout"""
        # Create treeview for bat data with per-feeder stats
        columns = ('Bat ID', 'Tag ID', 'Position', 'Total Flights', 'Total Rewards', 'Flights/Feeder', 'Rewards/Feeder', 'Last Update')
        self.bat_tree = ttk.Treeview(self.parent, columns=columns, show='headings', height=8)
        
        # Configure columns
        column_widths = {
            'Bat ID': 60,
            'Tag ID': 50,
            'Position': 120,
            'Total Flights': 70,
            'Total Rewards': 70,
            'Flights/Feeder': 80,
            'Rewards/Feeder': 80,
            'Last Update': 80
        }
        
        for col in columns:
            self.bat_tree.heading(col, text=col)
            self.bat_tree.column(col, width=column_widths.get(col, 100))
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(self.parent, orient=tk.VERTICAL, command=self.bat_tree.yview)
        self.bat_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.bat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary frame at bottom
        summary_frame = ttk.Frame(self.parent)
        summary_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Summary labels
        self.total_bats_label = ttk.Label(summary_frame, text="Total Bats: 0")
        self.total_bats_label.pack(side=tk.LEFT)
        
        self.active_bats_label = ttk.Label(summary_frame, text="Active Bats: 0")
        self.active_bats_label.pack(side=tk.LEFT, padx=(20, 0))
        
        self.total_flights_label = ttk.Label(summary_frame, text="Total Flights: 0")
        self.total_flights_label.pack(side=tk.LEFT, padx=(20, 0))
        
        self.total_rewards_label = ttk.Label(summary_frame, text="Total Rewards: 0")
        self.total_rewards_label.pack(side=tk.LEFT, padx=(20, 0))
    
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
        """Update loop for bat panel"""
        while self.running:
            try:
                # Schedule update on main thread
                if self.parent.winfo_exists():
                    self.parent.after_idle(self._update_display)
                time.sleep(2.0)  # Update every 2 seconds
            except Exception as e:
                print(f"Bat panel update error: {e}")
                time.sleep(1.0)
    
    def _update_display(self):
        """Update bat display (called on main thread)"""
        try:
            bat_states = self.feeder_manager.get_bat_states()
            
            # Clear existing items
            for item in self.bat_tree.get_children():
                self.bat_tree.delete(item)
            
            # Add current bat states
            total_flights = 0
            total_rewards = 0
            active_bats = 0
            
            for bat_id, bat_state in bat_states.items():
                # Format position
                if bat_state.last_position:
                    position_str = f"({bat_state.last_position.x:.1f}, {bat_state.last_position.y:.1f}, {bat_state.last_position.z:.1f})"
                    # Format last update time
                    time_diff = time.time() - bat_state.last_position.timestamp
                    if time_diff < 60:
                        last_update = f"{time_diff:.1f}s ago"
                    else:
                        last_update = f"{time_diff/60:.1f}m ago"
                else:
                    position_str = "Unknown"
                    last_update = "Never"
                
                # Determine if bat is active (recent position update)
                is_active = (bat_state.last_position and 
                           time.time() - bat_state.last_position.timestamp < 5.0)
                
                if is_active:
                    active_bats += 1
                
                # Get per-feeder statistics
                flights_per_feeder, rewards_per_feeder = bat_state.get_feeder_stats_string()
                
                # Add to tree
                self.bat_tree.insert('', 'end', values=(
                    bat_state.bat_id,
                    bat_state.tag_id,
                    position_str,
                    bat_state.flight_count,
                    bat_state.reward_count,
                    flights_per_feeder,
                    rewards_per_feeder,
                    last_update
                ))
                
                total_flights += bat_state.flight_count
                total_rewards += bat_state.reward_count
            
            # Update summary
            self.total_bats_label.config(text=f"Total Bats: {len(bat_states)}")
            self.active_bats_label.config(text=f"Active Bats: {active_bats}")
            self.total_flights_label.config(text=f"Total Flights: {total_flights}")
            self.total_rewards_label.config(text=f"Total Rewards: {total_rewards}")
            
        except Exception as e:
            print(f"Error updating bat display: {e}")