"""
Feeder controller that manages hardware and delegates decisions to task logic.

This controller:
1. Maintains system state
2. Handles hardware communication
3. Delegates reward decisions to task logic
4. Provides clean interface for GUI and logging
"""
import time
import threading
import math
from typing import Dict, Optional, Callable
from utils.data_structures import Position, RewardEvent
# Removed utils.decorators import - inlined single usage
from task_logic.system_state import SystemState
from task_logic.task_logic import should_deliver_reward, update_bat_state_after_reward


class FeederController:
    """
    Feeder controller using modular task logic system.
    
    This controller handles hardware communication and delegates
    all reward logic decisions to the task logic endpoint.
    """
    
    def __init__(self, feeder_configs: list, arduino_controller, 
                 reward_callback: Optional[Callable[[RewardEvent], None]] = None,
                 data_logger=None):
        """
        Initialize feeder controller.

        Args:
            feeder_configs: List of feeder configurations
            arduino_controller: Arduino controller instance
            reward_callback: Function to call when reward is delivered
            data_logger: Data logging instance
        """
        self.arduino = arduino_controller
        self.reward_callback = reward_callback
        self.data_logger = data_logger
        
        # Position change callback for GUI updates
        self.position_change_callback = None
        
        # Initialize system state
        self.system_state = SystemState()
        self._initialize_feeders(feeder_configs)
        
        # Control
        self.running = False
        self.control_thread: Optional[threading.Thread] = None
        
        # Performance tracking
        self.stats = {
            'beam_breaks_processed': 0,
            'rewards_delivered': 0,
            'rewards_denied': 0,
            'start_time': time.time()
        }
    
    def set_position_change_callback(self, callback):
        """Set callback to notify when feeder positions change"""
        self.position_change_callback = callback
    
    def _initialize_feeders(self, feeder_configs: list):
        """Initialize feeders from configuration"""
        # Store feeder configs for position management
        self.feeder_configs = {config.feeder_id: config for config in feeder_configs}
        
        for config in feeder_configs:
            self.system_state.add_feeder(
                feeder_id=config.feeder_id,
                name=f"Feeder_{config.feeder_id}",
                position=(config.x_position, config.y_position, config.z_position),
                activation_radius=config.activation_radius,
                reactivation_distance=config.reactivation_distance,
                duration_ms=config.duration_ms,
                motor_speed=config.speed
            )
    
    def change_feeder_position(self, feeder_id: int, position_index: int) -> bool:
        """
        Change a feeder's position and update system state
        
        Args:
            feeder_id: ID of the feeder to move
            position_index: Index of the new position
            
        Returns:
            bool: True if position change was successful
        """
        if feeder_id not in self.feeder_configs:
            print(f"Error: Unknown feeder ID {feeder_id}")
            return False
        
        feeder_config = self.feeder_configs[feeder_id]
        old_position_index = feeder_config.current_position_index
        
        if not feeder_config.set_position(position_index):
            print(f"Error: Invalid position index {position_index} for feeder {feeder_id}")
            return False
        
        # Update system state feeder position
        if feeder_id in self.system_state.feeders:
            feeder_state = self.system_state.feeders[feeder_id]
            new_coords = feeder_config.get_current_position()
            feeder_state.x_position, feeder_state.y_position, feeder_state.z_position = new_coords
            feeder_state.position = new_coords
            
            print(f"Feeder {feeder_id} moved to position '{feeder_config.get_position_name()}' at {new_coords}")
            
            # Log the position change
            if self.data_logger:
                import time
                self.data_logger.log_feeder_position_change(
                    feeder_id=feeder_id,
                    old_position_index=old_position_index,
                    new_position_index=position_index,
                    position_name=feeder_config.get_position_name(),
                    coordinates=new_coords,
                    timestamp=time.time()
                )
            
            # Notify GUI of position change
            if self.position_change_callback:
                try:
                    self.position_change_callback(list(self.feeder_configs.values()))
                except Exception as e:
                    print(f"Error in position change callback: {e}")
            
            return True
        
        return False
    
    def get_feeder_position_options(self, feeder_id: int) -> list:
        """
        Get available position options for a feeder
        
        Args:
            feeder_id: ID of the feeder
            
        Returns:
            list: List of position configurations with name, coordinates, description
        """
        if feeder_id not in self.feeder_configs:
            return []
        
        feeder_config = self.feeder_configs[feeder_id]
        return feeder_config.available_positions or []
    
    def get_current_feeder_position_index(self, feeder_id: int) -> int:
        """Get current position index for a feeder"""
        if feeder_id not in self.feeder_configs:
            return 0
        return self.feeder_configs[feeder_id].current_position_index

    def start(self):
        """Start the feeder control system"""
        if self.running:
            return
            
        self.running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        self.system_state.session_start_time = time.time()
        print("Feeder controller started")
    
    def stop(self):
        """Stop the feeder control system"""
        self.running = False
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=1.0)
        print("Feeder controller stopped")
    
    def update_position(self, position: Position):
        """
        Update bat position in system state.
        
        Args:
            position: New position data
        """
        bat_id = position.bat_id
        
        # Add bat to system state if new
        if bat_id not in self.system_state.bats:
            self.system_state.add_bat(bat_id, position.tag_id)
        
        # Update position
        self.system_state.update_bat_position(
            bat_id, 
            (position.x, position.y, position.z), 
            position.timestamp
        )
    
    def _control_loop(self):
        """Main control loop - monitors for beam breaks"""
        while self.running:
            try:
                # Check for beam break events
                beam_breaks = self.arduino.get_beam_breaks()
                
                for feeder_id in beam_breaks:
                    self._handle_beam_break(feeder_id)
                
                time.sleep(0.01)  # 100 Hz control loop
                
            except Exception as e:
                import traceback
                print(f"Error in feeder control loop: {e}")
                traceback.print_exc()
                time.sleep(0.1)
    
    def _handle_beam_break(self, feeder_id: int):
        """
        Handle beam break event using task logic.
        
        Args:
            feeder_id: ID of feeder with beam break
        """
        current_time = time.time()
        self.stats['beam_breaks_processed'] += 1
        
        print(f"Beam break detected on feeder {feeder_id}")
        
        # Log beam break event
        if self.data_logger:
            self.data_logger.log_beam_break(feeder_id)
        
        # Find triggering bat using feeder's activation radius
        triggering_bat_id = self._find_closest_bat_to_feeder(feeder_id)
        
        if not triggering_bat_id:
            feeder = self.system_state.feeders[feeder_id]
            print(f"⚠️  BEAM BREAK IGNORED: No bats within {feeder.activation_radius}m of feeder {feeder_id}")
            return
        
        # Calculate distance and position for history
        bat = self.system_state.bats[triggering_bat_id]
        feeder = self.system_state.feeders[feeder_id]
        
        distance = 0.0
        bat_position = None
        
        if bat.last_position:
            bat_pos = bat.last_position[:3]
            bat_position = bat_pos
            distance = self._calculate_distance(bat_pos, feeder.position)

        # Update system state timestamp
        self.system_state.timestamp = current_time

        # Call task logic to determine if reward should be delivered
        should_deliver, reason = should_deliver_reward(
            self.system_state, feeder_id, triggering_bat_id
        )

        # Debug output - show current bat state
        bat_activation_state = bat.activation_state
        bat_last_reward_feeder = bat.last_reward_feeder_id
        print(f"🦇 Bat {triggering_bat_id} state: {bat_activation_state} (last reward feeder: {bat_last_reward_feeder})")
        print(f"🤖 Task logic decision: {should_deliver} - {reason}")

        if should_deliver:
            # ONLY record beam break when task logic approves reward delivery
            # This ensures beam break count = reward request count (not including INACTIVE triggers)
            self.system_state.record_beam_break(feeder_id, triggering_bat_id, distance, bat_position)
            success = self._deliver_reward(feeder_id, triggering_bat_id)
            if success:
                self.stats['rewards_delivered'] += 1
                
                # Update bat state AFTER successful reward delivery
                update_bat_state_after_reward(self.system_state, feeder_id, triggering_bat_id)
                
                # Record reward in system state
                self.system_state.record_reward_delivery(feeder_id, triggering_bat_id)
                
                print(f"🎯 Bat {triggering_bat_id} set to INACTIVE after reward from feeder {feeder_id}")
            else:
                self.stats['rewards_denied'] += 1
                print(f"Hardware failed to deliver reward")
        else:
            self.stats['rewards_denied'] += 1
    
    def _find_closest_bat_to_feeder(self, feeder_id: int) -> Optional[str]:
        """
        Find the closest bat to a feeder that's within triggering distance.
        Uses feeder's activation_radius to determine if a bat could have triggered the beam break.
        
        Args:
            feeder_id: ID of the feeder
            
        Returns:
            Optional[str]: bat_id of closest bat within activation_radius, or None
        """
        if feeder_id not in self.system_state.feeders:
            return None
        
        feeder = self.system_state.feeders[feeder_id]
        feeder_pos = feeder.position
        current_time = time.time()
        
        # Use feeder's activation radius for beam break validation
        beam_break_threshold = feeder.activation_radius
        
        closest_bat_id = None
        min_distance = float('inf')
        
        for bat_id, bat in self.system_state.bats.items():
            # Skip inactive bats or bats without recent position data
            if not bat.active or not bat.last_position:
                continue
            
            # Check if position is recent enough (within 1 second for position timeout)
            pos_timestamp = bat.last_position[3] if len(bat.last_position) > 3 else current_time
            if current_time - pos_timestamp > 1.0:
                continue
            
            bat_pos = bat.last_position[:3]
            distance = self._calculate_distance(bat_pos, feeder_pos)
            
            # CRITICAL: Only consider bats within beam break triggering distance
            if distance <= beam_break_threshold and distance < min_distance:
                min_distance = distance
                closest_bat_id = bat_id
        
        if closest_bat_id:
            print(f"Identified triggering bat: {closest_bat_id} at {min_distance:.2f}m from feeder {feeder_id}")
        else:
            print(f"No bats within {beam_break_threshold}m of feeder {feeder_id} - beam break ignored")
        
        return closest_bat_id
    
    def _calculate_distance(self, pos1: tuple, pos2: tuple) -> float:
        """Calculate 3D distance between two positions"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1] 
        dz = pos1[2] - pos2[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def _deliver_reward(self, feeder_id: int, bat_id: str, manual: bool = False) -> bool:
        """
        Deliver reward through hardware.
        
        Args:
            feeder_id: ID of the feeder
            bat_id: ID of the bat receiving reward
            manual: Whether this is a manual reward
            
        Returns:
            bool: True if successful
        """
        if feeder_id not in self.system_state.feeders:
            return False
        
        feeder = self.system_state.feeders[feeder_id]
        
        print(f"Activating motor {feeder_id} for {feeder.duration_ms}ms at speed {feeder.motor_speed}...")
        success = self.arduino.activate_motor(feeder_id, feeder.duration_ms, feeder.motor_speed)
        
        if success:
            # Create reward event for callback
            reward_event = RewardEvent.create_now(feeder_id, bat_id, manual)
            if self.reward_callback:
                self.reward_callback(reward_event)
            
            print(f"✓ Reward delivered: Feeder {feeder_id}, Bat {bat_id}, Manual: {manual}")
            return True
        else:
            print(f"✗ Failed to deliver reward: Feeder {feeder_id} - Motor activation failed")
            return False
    
    def manual_reward(self, feeder_id: int) -> bool:
        """
        Manually trigger reward delivery.
        
        Args:
            feeder_id: ID of the feeder
            
        Returns:
            bool: True if successful
        """
        if feeder_id not in self.system_state.feeders:
            return False
        
        # Use generic bat ID for manual rewards
        bat_id = "manual"
        success = self._deliver_reward(feeder_id, bat_id, manual=True)
        
        if success:
            # Record in system state
            self.system_state.record_reward_delivery(feeder_id, bat_id, manual=True)
            self.stats['rewards_delivered'] += 1
        
        return success
    
    def update_feeder_config(self, feeder_id: int, **kwargs):
        """Update feeder configuration"""
        if feeder_id in self.system_state.feeders:
            feeder = self.system_state.feeders[feeder_id]
            
            if 'duration_ms' in kwargs:
                feeder.duration_ms = kwargs['duration_ms']
            if 'speed' in kwargs:
                feeder.motor_speed = kwargs['speed']
            if 'x_position' in kwargs or 'y_position' in kwargs or 'z_position' in kwargs:
                x = kwargs.get('x_position', feeder.position[0])
                y = kwargs.get('y_position', feeder.position[1])
                z = kwargs.get('z_position', feeder.position[2])
                feeder.position = (x, y, z)
            if 'activation_radius' in kwargs:
                feeder.activation_radius = kwargs['activation_radius']
            if 'reactivation_distance' in kwargs:
                feeder.reactivation_distance = kwargs['reactivation_distance']
            if 'active' in kwargs:
                feeder.active = kwargs['active']
    
    def get_bat_states(self) -> Dict:
        """Get current bat states for GUI"""
        states = {}
        
        for bat_id, bat in self.system_state.bats.items():
            # Create simple state object for GUI
            state = type('BatState', (), {})()
            state.bat_id = bat.bat_id
            state.tag_id = bat.tag_id
            state.active = bat.active
            
            # Add new task logic state fields
            state.activation_state = bat.activation_state
            state.last_reward_feeder_id = bat.last_reward_feeder_id
            state.last_reward_time = bat.last_reward_time
            
            # Convert position format
            if bat.last_position:
                state.last_position = Position(
                    bat_id=bat.bat_id,
                    tag_id=bat.tag_id,
                    x=bat.last_position[0],
                    y=bat.last_position[1],
                    z=bat.last_position[2],
                    timestamp=bat.last_position[3] if len(bat.last_position) > 3 else time.time()
                )
            else:
                state.last_position = None
            
            # Statistics
            state.flight_count = len(bat.beam_break_history)
            state.reward_count = len(bat.reward_history)
            
            # Per-feeder statistics
            state.flights_per_feeder = {}
            state.rewards_per_feeder = {}
            
            for event in bat.beam_break_history:
                state.flights_per_feeder[event.feeder_id] = state.flights_per_feeder.get(event.feeder_id, 0) + 1
            
            for event in bat.reward_history:
                state.rewards_per_feeder[event.feeder_id] = state.rewards_per_feeder.get(event.feeder_id, 0) + 1
            
            # Timing info
            if bat.beam_break_history:
                state.last_beam_break_time = bat.beam_break_history[-1].timestamp
                state.last_triggered_feeder_id = bat.beam_break_history[-1].feeder_id
            else:
                state.last_beam_break_time = 0.0
                state.last_triggered_feeder_id = None
            
            # Add helper method for GUI compatibility
            def get_feeder_stats_string(max_feeders=4):
                flight_parts = []
                reward_parts = []
                for i in range(max_feeders):
                    flights = state.flights_per_feeder.get(i, 0)
                    rewards = state.rewards_per_feeder.get(i, 0)
                    flight_parts.append(str(flights))
                    reward_parts.append(str(rewards))
                return (" | ".join(flight_parts), " | ".join(reward_parts))
            
            state.get_feeder_stats_string = get_feeder_stats_string
            states[bat_id] = state
        
        return states
    
    def get_feeder_configs(self) -> Dict:
        """Get feeder configurations for GUI"""
        configs = {}
        
        for feeder_id, feeder in self.system_state.feeders.items():
            # Create simple config object for GUI
            config = type('FeederConfig', (), {})()
            config.feeder_id = feeder.feeder_id
            config.duration_ms = feeder.duration_ms
            config.speed = feeder.motor_speed
            config.x_position = feeder.position[0]
            config.y_position = feeder.position[1]
            config.z_position = feeder.position[2]
            config.activation_radius = feeder.activation_radius
            config.beam_break_count = len(feeder.beam_break_history)
            config.reward_delivery_count = len(feeder.reward_delivery_history)
            config.probability = 1.0  # Default probability for GUI compatibility
            config.active = feeder.active  # Whether feeder is active
            config.state = 'Ready' if feeder.active else 'Inactive'

            configs[feeder_id] = config
        
        return configs
    
    def get_system_state(self) -> SystemState:
        """Get the complete system state"""
        return self.system_state
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        runtime = time.time() - self.stats['start_time']
        return {
            **self.stats,
            'runtime_seconds': runtime,
            'beam_breaks_per_minute': (self.stats['beam_breaks_processed'] / runtime) * 60 if runtime > 0 else 0,
            'rewards_per_minute': (self.stats['rewards_delivered'] / runtime) * 60 if runtime > 0 else 0,
            'reward_success_rate': (self.stats['rewards_delivered'] / self.stats['beam_breaks_processed']) if self.stats['beam_breaks_processed'] > 0 else 0
        }
