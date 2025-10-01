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
    
    def __init__(self, parent, feeder_controller, settings=None):
        """
        Initialize bat panel
        
        Args:
            parent: Parent tkinter widget
            feeder_manager: FeederManager instance
            settings: Settings instance for configuration
        """
        self.parent = parent
        self.feeder_controller = feeder_controller
        self.settings = settings
        
        # Load configuration
        gui_config = settings.get_gui_config() if settings else {}
        refresh_rate_hz = gui_config.get('refresh_rate_hz', 10)
        self.update_interval = 1.0 / refresh_rate_hz  # Convert Hz to seconds
        self.position_timeout = gui_config.get('position_timeout_gui', 5.0)
        
        # Update control
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        
        # Setup panel
        self._setup_panel()
    
    def _setup_panel(self):
        """Setup the bat panel layout"""
        # Create treeview for bat data with per-feeder stats
        columns = ('Bat ID', 'Tag ID', 'Status', 'Position', 'Total Flights', 'Total Rewards', 'Flights/Feeder', 'Rewards/Feeder')
        self.bat_tree = ttk.Treeview(self.parent, columns=columns, show='headings', height=8)

        # Configure columns
        column_widths = {
            'Bat ID': 60,
            'Tag ID': 100,  # Doubled from 50 to accommodate 8-10 digit numbers
            'Status': 80,
            'Position': 90,
            'Total Flights': 90,
            'Total Rewards': 100,
            'Flights/Feeder': 100,
            'Rewards/Feeder': 110
        }

        for col in columns:
            self.bat_tree.heading(col, text=col)
            self.bat_tree.column(col, width=column_widths.get(col, 100))

        # Configure zebra striping for alternating rows (dark theme)
        self.bat_tree.tag_configure('oddrow', background='#40444B')
        self.bat_tree.tag_configure('evenrow', background='#36393F')

        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(self.parent, orient=tk.VERTICAL, command=self.bat_tree.yview)
        self.bat_tree.configure(yscrollcommand=scrollbar.set)

        # Pack widgets
        self.bat_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
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
                time.sleep(self.update_interval)
            except Exception as e:
                import traceback
                print(f"Bat panel update error in {__file__}:")
                print(f"Error: {e}")
                traceback.print_exc()
                time.sleep(1.0)
    
    def _update_display(self):
        """Update bat display (called on main thread)"""
        try:
            bat_states = self.feeder_controller.get_bat_states()
            
            # Clear existing items
            for item in self.bat_tree.get_children():
                self.bat_tree.delete(item)
            
            # Add current bat states
            total_flights = 0
            total_rewards = 0
            active_bats = 0

            row_index = 0
            for bat_id, bat_state in bat_states.items():
                # Format position
                if bat_state.last_position:
                    position_str = f"({bat_state.last_position.x:.1f}, {bat_state.last_position.y:.1f}, {bat_state.last_position.z:.1f})"
                else:
                    position_str = "Unknown"
                
                # Determine if bat is active (recent position update)
                is_active = (bat_state.last_position and 
                           time.time() - bat_state.last_position.timestamp < self.position_timeout)
                
                if is_active:
                    active_bats += 1
                
                # Format activation status
                activation_status = getattr(bat_state, 'activation_state', 'UNKNOWN')
                if activation_status == 'INACTIVE':
                    last_reward_feeder = getattr(bat_state, 'last_reward_feeder_id', None)
                    status_str = f"INACTIVE (F{last_reward_feeder})" if last_reward_feeder else "INACTIVE"
                else:
                    status_str = activation_status
                
                # Get per-feeder statistics
                flights_per_feeder, rewards_per_feeder = bat_state.get_feeder_stats_string()

                # Determine row tags for zebra striping
                row_tag = 'evenrow' if row_index % 2 == 0 else 'oddrow'
                tags = [row_tag]

                # Add INACTIVE tag if needed
                if activation_status == 'INACTIVE':
                    tags.append('inactive')

                # Add to tree with zebra striping
                item = self.bat_tree.insert('', 'end', values=(
                    bat_state.bat_id,
                    bat_state.tag_id,
                    status_str,
                    position_str,
                    bat_state.flight_count,
                    bat_state.reward_count,
                    flights_per_feeder,
                    rewards_per_feeder
                ), tags=tuple(tags))

                # Configure INACTIVE style (muted gray on dark background)
                if activation_status == 'INACTIVE':
                    try:
                        self.bat_tree.tag_configure('inactive', foreground='#72767D')
                    except:
                        pass  # Ignore styling errors

                total_flights += bat_state.flight_count
                total_rewards += bat_state.reward_count
                row_index += 1


        except Exception as e:
            import traceback
            print(f"Error updating bat display in {__file__}:")
            print(f"Error: {e}")
            traceback.print_exc()