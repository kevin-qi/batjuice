"""
Feeder control panel for the GUI.
"""
import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Optional


class FeederPanel:
    """Panel for controlling and monitoring feeders"""
    
    def __init__(self, parent, feeder_controller, settings, event_logger):
        """
        Initialize feeder panel
        
        Args:
            parent: Parent tkinter widget
            feeder_manager: FeederManager instance
            settings: Settings instance
            event_logger: EventLogger instance
        """
        self.parent = parent
        self.feeder_controller = feeder_controller
        self.settings = settings
        self.event_logger = event_logger
        
        # Update control
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        
        # Feeder widgets
        self.feeder_frames = {}
        self.feeder_vars = {}
        
        # Setup panel
        self._setup_panel()
    
    def _setup_panel(self):
        """Setup the feeder panel layout"""
        # Main scrollable frame
        canvas = tk.Canvas(self.parent)
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Get feeder configurations
        feeder_configs = self.settings.get_feeder_configs()
        
        # Create compact feeder table instead of individual widgets
        self._create_feeder_table(scrollable_frame, feeder_configs)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_feeder_table(self, parent, feeder_configs):
        """Create compact tabular display for feeders"""
        # Main feeder table frame
        table_frame = ttk.LabelFrame(parent, text="Feeders", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for compact display
        columns = ('ID', 'Status', 'Beam Breaks', 'Rewards', 'Duration', 'Speed', 'Probability', 'Distance', 'Actions')
        self.feeder_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=len(feeder_configs) + 1)
        
        # Configure column headers and widths
        col_widths = {'ID': 30, 'Status': 60, 'Beam Breaks': 80, 'Rewards': 60, 
                     'Duration': 60, 'Speed': 50, 'Probability': 70, 'Distance': 60, 'Actions': 100}
        
        for col in columns:
            self.feeder_tree.heading(col, text=col)
            self.feeder_tree.column(col, width=col_widths.get(col, 80), minwidth=50)
        
        # Add feeder data
        for feeder_config in feeder_configs:
            feeder_id = feeder_config.feeder_id
            self.feeder_tree.insert('', 'end', iid=f'feeder_{feeder_id}', values=(
                feeder_id,
                'Ready',
                0,  # beam breaks
                0,  # rewards
                feeder_config.duration_ms,
                feeder_config.speed,
                f"{feeder_config.probability:.1f}",
                f"{feeder_config.activation_radius:.1f}",
                ''  # actions placeholder
            ))
            
            # Store feeder vars for updates
            self.feeder_vars[feeder_id] = {
                'duration_ms': feeder_config.duration_ms,
                'speed': feeder_config.speed,
                'probability': feeder_config.probability,
                'activation_radius': feeder_config.activation_radius
            }
        
        self.feeder_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Compact controls frame
        controls_frame = ttk.Frame(table_frame)
        controls_frame.pack(fill=tk.X)
        
        # Configuration controls
        config_frame = ttk.LabelFrame(controls_frame, text="Quick Config", padding=5)
        config_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Duration control
        ttk.Label(config_frame, text="Duration (ms):").grid(row=0, column=0, sticky='w', padx=(0, 5))
        self.duration_var = tk.IntVar(value=100)
        duration_spin = ttk.Spinbox(config_frame, from_=50, to=2000, width=8, textvariable=self.duration_var)
        duration_spin.grid(row=0, column=1, padx=(0, 10))
        
        # Speed control  
        ttk.Label(config_frame, text="Speed:").grid(row=0, column=2, sticky='w', padx=(0, 5))
        self.speed_var = tk.IntVar(value=255)
        speed_spin = ttk.Spinbox(config_frame, from_=0, to=255, width=8, textvariable=self.speed_var)
        speed_spin.grid(row=0, column=3, padx=(0, 10))
        
        # Apply button
        apply_btn = ttk.Button(config_frame, text="Apply to Selected", command=self._apply_quick_config)
        apply_btn.grid(row=0, column=4, padx=(10, 0))
        
        # Manual controls
        manual_frame = ttk.LabelFrame(controls_frame, text="Manual Control", padding=5)
        manual_frame.pack(side=tk.RIGHT)
        
        # Manual reward buttons (top row)
        reward_frame = ttk.Frame(manual_frame)
        reward_frame.pack()
        ttk.Label(reward_frame, text="Reward:").pack(side=tk.LEFT, padx=(0, 5))
        for feeder_config in feeder_configs:
            feeder_id = feeder_config.feeder_id
            reward_btn = ttk.Button(
                reward_frame,
                text=f"F{feeder_id}",
                width=4,
                command=lambda fid=feeder_id: self._manual_reward(fid)
            )
            reward_btn.pack(side=tk.LEFT, padx=2)
        
    
    def _apply_quick_config(self):
        """Apply quick configuration to selected feeders"""
        selection = self.feeder_tree.selection()
        if not selection:
            # If nothing selected, apply to all
            selection = [f'feeder_{i}' for i in self.feeder_vars.keys()]
        
        duration = self.duration_var.get()
        speed = self.speed_var.get()
        
        for item_id in selection:
            if item_id.startswith('feeder_'):
                feeder_id = int(item_id.split('_')[1])
                if feeder_id in self.feeder_vars:
                    # Update feeder manager
                    self.feeder_controller.update_feeder_config(feeder_id, duration_ms=duration, speed=speed)
                    
                    # Update tree display
                    current_values = list(self.feeder_tree.item(item_id)['values'])
                    current_values[4] = duration  # Duration column
                    current_values[5] = speed     # Speed column
                    self.feeder_tree.item(item_id, values=current_values)
                    
                    print(f"Updated feeder {feeder_id}: duration={duration}ms, speed={speed}")
    
    def _create_feeder_widget(self, parent, feeder_config, row):
        """Create widget for a single feeder"""
        feeder_id = feeder_config.feeder_id
        
        # Main frame for this feeder
        feeder_frame = ttk.LabelFrame(parent, text=f"Feeder {feeder_id}", padding=10)
        feeder_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.feeder_frames[feeder_id] = feeder_frame
        self.feeder_vars[feeder_id] = {}
        
        # Status row
        status_frame = ttk.Frame(feeder_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        status_label = ttk.Label(status_frame, text="Ready", foreground="green")
        status_label.pack(side=tk.LEFT, padx=(5, 0))
        self.feeder_vars[feeder_id]['status_label'] = status_label
        
        # Statistics row
        stats_frame = ttk.Frame(feeder_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Beam breaks
        beam_frame = ttk.Frame(stats_frame)
        beam_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(beam_frame, text="Beam Breaks:").pack(side=tk.LEFT)
        beam_label = ttk.Label(beam_frame, text="0", font=('TkDefaultFont', 9, 'bold'))
        beam_label.pack(side=tk.LEFT, padx=(5, 0))
        self.feeder_vars[feeder_id]['beam_label'] = beam_label
        
        # Rewards
        reward_frame = ttk.Frame(stats_frame)
        reward_frame.pack(side=tk.LEFT)
        ttk.Label(reward_frame, text="Rewards:").pack(side=tk.LEFT)
        reward_label = ttk.Label(reward_frame, text="0", font=('TkDefaultFont', 9, 'bold'))
        reward_label.pack(side=tk.LEFT, padx=(5, 0))
        self.feeder_vars[feeder_id]['reward_label'] = reward_label
        
        # Position selection frame (NEW)
        position_frame = ttk.LabelFrame(feeder_frame, text="Position Control", padding=5)
        position_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Current position display
        current_pos_frame = ttk.Frame(position_frame)
        current_pos_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(current_pos_frame, text="Current:").pack(side=tk.LEFT)
        current_pos_label = ttk.Label(current_pos_frame, text=feeder_config.get_position_name(), 
                                     font=('TkDefaultFont', 9, 'bold'), foreground="blue")
        current_pos_label.pack(side=tk.LEFT, padx=(5, 10))
        self.feeder_vars[feeder_id]['current_pos_label'] = current_pos_label
        
        # Coordinates display
        coords = feeder_config.get_current_position()
        coords_text = f"({coords[0]:.2f}, {coords[1]:.2f}, {coords[2]:.2f})"
        coords_label = ttk.Label(current_pos_frame, text=coords_text, foreground="gray")
        coords_label.pack(side=tk.LEFT)
        self.feeder_vars[feeder_id]['coords_label'] = coords_label
        
        # Position selection
        selection_frame = ttk.Frame(position_frame)
        selection_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(selection_frame, text="Change to:").pack(side=tk.LEFT)
        
        # Get available positions
        position_options = feeder_config.available_positions or []
        position_names = [pos['name'] for pos in position_options]
        
        if position_names:
            position_var = tk.StringVar(value=position_names[feeder_config.current_position_index])
            position_combo = ttk.Combobox(selection_frame, textvariable=position_var, 
                                        values=position_names, state="readonly", width=20)
            position_combo.pack(side=tk.LEFT, padx=(5, 10))
            self.feeder_vars[feeder_id]['position_var'] = position_var
            self.feeder_vars[feeder_id]['position_combo'] = position_combo
            
            # Move button
            move_btn = ttk.Button(selection_frame, text="Move Feeder", 
                                command=lambda: self._move_feeder_position(feeder_id))
            move_btn.pack(side=tk.LEFT)
            self.feeder_vars[feeder_id]['move_btn'] = move_btn
        else:
            # Single position - show message
            ttk.Label(selection_frame, text="Single position configured", 
                     foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        
        # Configuration frame with current vs pending values
        config_frame = ttk.LabelFrame(feeder_frame, text="Configuration", padding=5)
        config_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Header row
        header_frame = ttk.Frame(config_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(header_frame, text="Parameter", width=15).pack(side=tk.LEFT)
        ttk.Label(header_frame, text="Current", width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(header_frame, text="New Value", width=10).pack(side=tk.LEFT, padx=(0, 5))
        
        # Duration setting
        duration_frame = ttk.Frame(config_frame)
        duration_frame.pack(fill=tk.X, pady=2)
        ttk.Label(duration_frame, text="Duration (ms):", width=15).pack(side=tk.LEFT)
        
        # Current value display (bold)
        current_duration_label = ttk.Label(duration_frame, text=str(feeder_config.duration_ms), 
                                         width=10, font=('TkDefaultFont', 9, 'bold'))
        current_duration_label.pack(side=tk.LEFT, padx=(0, 5))
        self.feeder_vars[feeder_id]['current_duration_label'] = current_duration_label
        
        # Editable new value
        duration_var = tk.IntVar(value=feeder_config.duration_ms)
        duration_spinbox = ttk.Spinbox(duration_frame, from_=100, to=5000, width=10, textvariable=duration_var)
        duration_spinbox.pack(side=tk.LEFT, padx=(0, 5))
        duration_spinbox.bind('<Key>', lambda e: self._highlight_changes(feeder_id))
        duration_spinbox.bind('<Button-1>', lambda e: self._highlight_changes(feeder_id))
        self.feeder_vars[feeder_id]['duration_var'] = duration_var
        self.feeder_vars[feeder_id]['duration_spinbox'] = duration_spinbox
        
        # Probability setting
        prob_frame = ttk.Frame(config_frame)
        prob_frame.pack(fill=tk.X, pady=2)
        ttk.Label(prob_frame, text="Probability:", width=15).pack(side=tk.LEFT)
        
        # Current value display
        current_prob_label = ttk.Label(prob_frame, text=f"{feeder_config.probability:.1f}", 
                                     width=10, font=('TkDefaultFont', 9, 'bold'))
        current_prob_label.pack(side=tk.LEFT, padx=(0, 5))
        self.feeder_vars[feeder_id]['current_prob_label'] = current_prob_label
        
        # Editable new value
        prob_var = tk.DoubleVar(value=feeder_config.probability)
        prob_spinbox = ttk.Spinbox(prob_frame, from_=0.0, to=1.0, increment=0.1, width=10, textvariable=prob_var)
        prob_spinbox.pack(side=tk.LEFT, padx=(0, 5))
        prob_spinbox.bind('<Key>', lambda e: self._highlight_changes(feeder_id))
        prob_spinbox.bind('<Button-1>', lambda e: self._highlight_changes(feeder_id))
        self.feeder_vars[feeder_id]['prob_var'] = prob_var
        self.feeder_vars[feeder_id]['prob_spinbox'] = prob_spinbox
        
        # Speed setting
        speed_frame = ttk.Frame(config_frame)
        speed_frame.pack(fill=tk.X, pady=2)
        ttk.Label(speed_frame, text="Speed (0-255):", width=15).pack(side=tk.LEFT)
        
        # Current value display
        current_speed_label = ttk.Label(speed_frame, text=str(feeder_config.speed), 
                                      width=10, font=('TkDefaultFont', 9, 'bold'))
        current_speed_label.pack(side=tk.LEFT, padx=(0, 5))
        self.feeder_vars[feeder_id]['current_speed_label'] = current_speed_label
        
        # Editable new value
        speed_var = tk.IntVar(value=feeder_config.speed)
        speed_spinbox = ttk.Spinbox(speed_frame, from_=0, to=255, width=10, textvariable=speed_var)
        speed_spinbox.pack(side=tk.LEFT, padx=(0, 5))
        speed_spinbox.bind('<Key>', lambda e: self._highlight_changes(feeder_id))
        speed_spinbox.bind('<Button-1>', lambda e: self._highlight_changes(feeder_id))
        self.feeder_vars[feeder_id]['speed_var'] = speed_var
        self.feeder_vars[feeder_id]['speed_spinbox'] = speed_spinbox
        
        # Activation distance setting
        dist_frame = ttk.Frame(config_frame)
        dist_frame.pack(fill=tk.X, pady=2)
        ttk.Label(dist_frame, text="Min Distance (m):", width=15).pack(side=tk.LEFT)
        
        # Current value display
        current_dist_label = ttk.Label(dist_frame, text=f"{feeder_config.activation_radius:.2f}", 
                                     width=10, font=('TkDefaultFont', 9, 'bold'))
        current_dist_label.pack(side=tk.LEFT, padx=(0, 5))
        self.feeder_vars[feeder_id]['current_dist_label'] = current_dist_label
        
        # Editable new value
        dist_var = tk.DoubleVar(value=feeder_config.activation_radius)
        # Get max activation distance from GUI config
        gui_config = self.settings.get_gui_config()
        max_distance = gui_config.get('max_activation_radius', 5.0)
        dist_spinbox = ttk.Spinbox(dist_frame, from_=0.1, to=max_distance, increment=0.05, width=10, textvariable=dist_var)
        dist_spinbox.pack(side=tk.LEFT, padx=(0, 5))
        dist_spinbox.bind('<Key>', lambda e: self._highlight_changes(feeder_id))
        dist_spinbox.bind('<Button-1>', lambda e: self._highlight_changes(feeder_id))
        self.feeder_vars[feeder_id]['dist_var'] = dist_var
        self.feeder_vars[feeder_id]['dist_spinbox'] = dist_spinbox
        
        # Apply button frame
        apply_frame = ttk.Frame(config_frame)
        apply_frame.pack(fill=tk.X, pady=(5, 0))
        
        apply_btn = ttk.Button(apply_frame, text="Apply Changes", 
                              command=lambda: self._apply_config_changes(feeder_id))
        apply_btn.pack(side=tk.LEFT)
        self.feeder_vars[feeder_id]['apply_btn'] = apply_btn
        
        # Status indicator for unsaved changes
        changes_label = ttk.Label(apply_frame, text="", foreground="orange")
        changes_label.pack(side=tk.LEFT, padx=(10, 0))
        self.feeder_vars[feeder_id]['changes_label'] = changes_label
        
        # Manual control frame
        control_frame = ttk.LabelFrame(feeder_frame, text="Manual Control", padding=5)
        control_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Manual reward button
        reward_btn = ttk.Button(
            control_frame, 
            text="Manual Reward",
            command=lambda: self._manual_reward(feeder_id)
        )
        reward_btn.pack(side=tk.LEFT)
        
        # Test motor button
        test_btn = ttk.Button(
            control_frame, 
            text="Test Motor",
            command=lambda: self._test_motor(feeder_id)
        )
        test_btn.pack(side=tk.LEFT, padx=(10, 0))
    
    def _highlight_changes(self, feeder_id):
        """Highlight that there are unsaved changes"""
        def check_changes():
            try:
                # Get current values from feeder manager
                configs = self.feeder_controller.get_feeder_configs()
                current_config = configs[feeder_id]
                
                # Get pending values from GUI
                pending_duration = self.feeder_vars[feeder_id]['duration_var'].get()
                pending_prob = self.feeder_vars[feeder_id]['prob_var'].get()
                pending_speed = self.feeder_vars[feeder_id]['speed_var'].get()
                pending_dist = self.feeder_vars[feeder_id]['dist_var'].get()
                
                # Check if any values changed
                changes = []
                if pending_duration != current_config.duration_ms:
                    changes.append("Duration")
                if abs(pending_prob - current_config.probability) > 0.01:
                    changes.append("Probability")
                if pending_speed != current_config.speed:
                    changes.append("Speed")
                if abs(pending_dist - current_config.activation_radius) > 0.01:
                    changes.append("Distance")
                
                # Update changes indicator
                changes_label = self.feeder_vars[feeder_id]['changes_label']
                apply_btn = self.feeder_vars[feeder_id]['apply_btn']
                
                if changes:
                    changes_label.config(text=f"Unsaved: {', '.join(changes)}", foreground="orange")
                    apply_btn.config(style="Accent.TButton")
                else:
                    changes_label.config(text="")
                    apply_btn.config(style="TButton")
                    
            except Exception as e:
                self.event_logger.error(f"Error checking changes: {e}")
        
        # Delay check to allow spinbox value to update
        self.parent.after(100, check_changes)
    
    def _apply_config_changes(self, feeder_id):
        """Apply configuration changes and log them"""
        try:
            # Get new values
            new_duration = self.feeder_vars[feeder_id]['duration_var'].get()
            new_prob = self.feeder_vars[feeder_id]['prob_var'].get()
            new_speed = self.feeder_vars[feeder_id]['speed_var'].get()
            new_dist = self.feeder_vars[feeder_id]['dist_var'].get()
            
            # Get current config for comparison
            configs = self.feeder_controller.get_feeder_configs()
            current_config = configs[feeder_id]
            
            changes_made = []
            
            # Apply duration change
            if new_duration != current_config.duration_ms:
                self.feeder_controller.update_feeder_config(feeder_id, duration_ms=new_duration)
                changes_made.append(f"Duration: {current_config.duration_ms} -> {new_duration}")
                
            # Apply probability change
            if abs(new_prob - current_config.probability) > 0.01:
                # Note: Probability is now handled in task logic configuration
                changes_made.append(f"Probability: {current_config.probability:.2f} -> {new_prob:.2f}")
                
            # Apply speed change
            if new_speed != current_config.speed:
                self.feeder_controller.update_feeder_config(feeder_id, speed=new_speed)
                changes_made.append(f"Speed: {current_config.speed} -> {new_speed}")
                
            # Apply distance change
            if abs(new_dist - current_config.activation_radius) > 0.01:
                self.feeder_controller.update_feeder_config(feeder_id, activation_radius=new_dist)
                changes_made.append(f"Distance: {current_config.activation_radius:.2f} -> {new_dist:.2f}")
            
            if changes_made:
                # Update current value displays
                updated_configs = self.feeder_controller.get_feeder_configs()
                updated_config = updated_configs[feeder_id]
                self.feeder_vars[feeder_id]['current_duration_label'].config(text=str(updated_config.duration_ms))
                self.feeder_vars[feeder_id]['current_prob_label'].config(text=f"{updated_config.probability:.1f}")
                self.feeder_vars[feeder_id]['current_speed_label'].config(text=str(updated_config.speed))
                self.feeder_vars[feeder_id]['current_dist_label'].config(text=f"{updated_config.activation_radius:.2f}")
                
                # Log the complete feeder state
                self.event_logger.info(f"Feeder {feeder_id} config updated: {'; '.join(changes_made)}")
                self.event_logger.info(f"Feeder {feeder_id} current state: Duration={updated_config.duration_ms}ms, "
                                     f"Speed={updated_config.speed}, Probability={updated_config.probability:.2f}, Distance={updated_config.activation_radius:.2f}m")
                
                # Clear change indicators
                self.feeder_vars[feeder_id]['changes_label'].config(text="")
                self.feeder_vars[feeder_id]['apply_btn'].config(style="TButton")
                
        except Exception as e:
            self.event_logger.error(f"Error applying config changes: {e}")
    
    def _manual_reward(self, feeder_id: int):
        """Trigger manual reward"""
        try:
            success = self.feeder_controller.manual_reward(feeder_id)
            if success:
                self.event_logger.info(f"Manual reward triggered for feeder {feeder_id}")
            else:
                self.event_logger.warning(f"Failed to trigger manual reward for feeder {feeder_id}")
        except Exception as e:
            self.event_logger.error(f"Error triggering manual reward: {e}")
    
    def _test_motor(self, feeder_id: int):
        """Test motor operation"""
        try:
            configs = self.feeder_controller.get_feeder_configs()
            if feeder_id in configs:
                duration = configs[feeder_id].duration_ms
                speed = configs[feeder_id].speed
                success = self.feeder_controller.arduino.activate_motor(feeder_id, duration, speed)
                if success:
                    self.event_logger.info(f"Motor test successful for feeder {feeder_id}")
                else:
                    self.event_logger.warning(f"Motor test failed for feeder {feeder_id}")
        except Exception as e:
            self.event_logger.error(f"Error testing motor: {e}")

    
    def _move_feeder_position(self, feeder_id):
        """Move feeder to selected position"""
        try:
            position_var = self.feeder_vars[feeder_id]['position_var']
            selected_name = position_var.get()
            
            # Find the index of the selected position
            feeder_config = self.feeder_controller.feeder_configs[feeder_id]
            position_options = feeder_config.available_positions or []
            
            selected_index = None
            for i, pos_config in enumerate(position_options):
                if pos_config['name'] == selected_name:
                    selected_index = i
                    break
            
            if selected_index is None:
                print(f"Error: Could not find position '{selected_name}' for feeder {feeder_id}")
                return
            
            # Check if already at this position
            if selected_index == feeder_config.current_position_index:
                print(f"Feeder {feeder_id} is already at position '{selected_name}'")
                return
            
            # Move the feeder
            if self.feeder_controller.change_feeder_position(feeder_id, selected_index):
                # Update GUI display
                self._update_position_display(feeder_id)
                print(f"Successfully moved feeder {feeder_id} to '{selected_name}'")
            else:
                print(f"Failed to move feeder {feeder_id} to '{selected_name}'")
                
        except Exception as e:
            print(f"Error moving feeder {feeder_id}: {e}")
    
    def _update_position_display(self, feeder_id):
        """Update the position display for a feeder"""
        try:
            feeder_config = self.feeder_controller.feeder_configs[feeder_id]
            feeder_vars = self.feeder_vars[feeder_id]
            
            # Update current position label
            if 'current_pos_label' in feeder_vars:
                feeder_vars['current_pos_label'].config(text=feeder_config.get_position_name())
            
            # Update coordinates display
            if 'coords_label' in feeder_vars:
                coords = feeder_config.get_current_position()
                coords_text = f"({coords[0]:.2f}, {coords[1]:.2f}, {coords[2]:.2f})"
                feeder_vars['coords_label'].config(text=coords_text)
            
            # Update dropdown selection
            if 'position_var' in feeder_vars:
                feeder_vars['position_var'].set(feeder_config.get_position_name())
                
        except Exception as e:
            print(f"Error updating position display for feeder {feeder_id}: {e}")
    
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
        """Update loop for feeder panel"""
        while self.running:
            try:
                # Schedule update on main thread
                if self.parent.winfo_exists():
                    self.parent.after_idle(self._update_display)
                time.sleep(1.0)  # Update every 1000ms
            except Exception as e:
                print(f"Feeder panel update error: {e}")
                time.sleep(1.0)
    
    def _update_display(self):
        """Update feeder table display (called on main thread)"""
        try:
            feeder_configs = self.feeder_controller.get_feeder_configs()
            
            for feeder_id, config in feeder_configs.items():
                item_id = f'feeder_{feeder_id}'
                if self.feeder_tree.exists(item_id):
                    # Get current values and update
                    current_values = list(self.feeder_tree.item(item_id)['values'])
                    current_values[2] = config.beam_break_count  # Beam breaks
                    current_values[3] = config.reward_delivery_count  # Rewards
                    current_values[4] = config.duration_ms  # Duration
                    current_values[5] = config.speed  # Speed
                    current_values[6] = f"{config.probability:.1f}"  # Probability
                    current_values[7] = f"{config.activation_radius:.1f}"  # Distance
                    
                    self.feeder_tree.item(item_id, values=current_values)
                    
        except Exception as e:
            print(f"Error updating feeder display: {e}")