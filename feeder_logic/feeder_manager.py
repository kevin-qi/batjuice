"""
Main feeder control logic and coordination.
"""
import time
import threading
import math
from typing import Dict, List, Optional, Callable
from utils.data_structures import Position, BatState, FeederConfig, FeederState, RewardEvent
from .position_processor import PositionProcessor
from .reward_system import RewardSystem


class FeederManager:
    """Main coordinator for feeder control logic"""
    
    def __init__(self, feeder_configs: List[FeederConfig], 
                 arduino_controller, 
                 reward_callback: Optional[Callable[[RewardEvent], None]] = None,
                 data_logger=None):
        """
        Initialize feeder manager
        
        Args:
            feeder_configs: List of feeder configurations
            arduino_controller: Arduino controller instance
            reward_callback: Function to call when reward is delivered
        """
        self.feeder_configs = {config.feeder_id: config for config in feeder_configs}
        self.arduino = arduino_controller
        self.reward_callback = reward_callback
        self.data_logger = data_logger
        
        # Tracking state
        self.bat_states: Dict[str, BatState] = {}
        self.position_processor = PositionProcessor()
        self.reward_system = RewardSystem()
        
        # Control
        self.running = False
        self.control_thread: Optional[threading.Thread] = None
        self.dynamic_position_enabled = True  # Can be controlled by GUI
        
    def start(self):
        """Start the feeder control system"""
        if self.running:
            return
            
        self.running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        print("Feeder manager started")
    
    def stop(self):
        """Stop the feeder control system"""
        self.running = False
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=1.0)
        print("Feeder manager stopped")
    
    def update_position(self, position: Position):
        """
        Update bat position and check feeder activation state
        
        Args:
            position: New position data
        """
        bat_id = position.bat_id
        
        # Initialize bat state if new
        if bat_id not in self.bat_states:
            self.bat_states[bat_id] = BatState(
                bat_id=bat_id,
                tag_id=position.tag_id,
                feeder_state=FeederState.INACTIVE,  # This field is now legacy
                last_position=None
            )
        
        bat_state = self.bat_states[bat_id]
        bat_state.last_position = position
        
        # No need to check activation state - new logic handles this in beam break handler
    

    
    def _control_loop(self):
        """Main control loop"""
        while self.running:
            try:
                # Check for beam break events
                beam_breaks = self.arduino.get_beam_breaks()
                
                for feeder_id in beam_breaks:
                    self._handle_beam_break(feeder_id)
                
                time.sleep(0.01)  # 100 Hz control loop
                
            except Exception as e:
                print(f"Error in control loop: {e}")
                time.sleep(0.1)
    
    def _handle_beam_break(self, feeder_id: int):
        """
        Handle beam break event with new logic:
        - Find closest bat to feeder
        - Check time/distance constraints
        - Check for multiple bats near feeder
        - Update feeder position based on trigger location
        
        Args:
            feeder_id: ID of feeder with beam break
        """
        if feeder_id not in self.feeder_configs:
            print(f"Unknown feeder ID: {feeder_id}")
            return
            
        feeder_config = self.feeder_configs[feeder_id]
        feeder_config.beam_break_count += 1
        current_time = time.time()
        
        print(f"Beam break detected on feeder {feeder_id}")
        
        # Log beam break event to events.csv
        if hasattr(self, 'data_logger') and self.data_logger:
            self.data_logger.log_beam_break(feeder_id)
        
        # Find the closest bat to this feeder
        triggering_bat = self._find_closest_bat_to_feeder(feeder_id)
        
        if not triggering_bat:
            print(f"No bats found near feeder {feeder_id} - no reward delivered")
            return
        
        bat_id, bat_distance = triggering_bat
        bat_state = self.bat_states[bat_id]
        
        # Update bat state for beam break
        bat_state.add_flight_to_feeder(feeder_id)
        bat_state.last_beam_break_time = current_time
        bat_state.last_triggered_feeder_id = feeder_id
        
        # Update feeder position with bat's position (if enabled and within 0.2 seconds and not NaN)
        if (self.dynamic_position_enabled and 
            bat_state.last_position and 
            not self._is_position_nan(bat_state.last_position)):
            position_age = current_time - bat_state.last_position.timestamp
            if position_age <= 0.2:  # Within 0.2 seconds
                feeder_config.update_position_from_trigger(bat_state.last_position)
                print(f"Updated feeder {feeder_id} position based on bat trigger: "
                      f"({feeder_config.x_position:.2f}, {feeder_config.y_position:.2f}, {feeder_config.z_position:.2f})")
        
        # Check if bat can receive reward based on new logic
        if not bat_state.can_receive_reward(current_time, 0.5, feeder_config.get_position()):
            print(f"Bat {bat_id} cannot receive reward - too soon since last beam break or too close to previous feeder")
            return
        
        # Check for multiple bats near feeder (collision detection)
        if self._check_multiple_bats_near_feeder(feeder_id, bat_id):
            print(f"Multiple bats near feeder {feeder_id} - no reward delivered")
            return
        
        # Check if reward should be delivered based on probability
        if self.reward_system.should_deliver_reward(feeder_config):
            success = self._deliver_reward(feeder_id, bat_id)
            if success:
                bat_state.add_reward_from_feeder(feeder_id)
                feeder_config.reward_delivery_count += 1
    
    def _find_triggering_bats(self, feeder_id: int) -> List[str]:
        """
        Find bats that could have triggered this feeder
        
        Args:
            feeder_id: ID of the feeder
            
        Returns:
            List[str]: List of bat IDs that are active for this feeder
        """
        active_bats = []
        
        for bat_id, bat_state in self.bat_states.items():
            if bat_state.feeder_state == FeederState.ACTIVE:
                # Check if bat is near this feeder
                if bat_state.last_position:
                    feeder_config = self.feeder_configs[feeder_id]
                    distance = self.position_processor.calculate_distance(
                        bat_state.last_position, feeder_config
                    )
                    # If bat is within reasonable range of feeder
                    if distance <= feeder_config.activation_distance * 2:
                        active_bats.append(bat_id)
        
        return active_bats
    
    def _find_closest_bat_to_feeder(self, feeder_id: int) -> Optional[tuple]:
        """
        Find the closest bat to a specific feeder
        
        Args:
            feeder_id: ID of the feeder
            
        Returns:
            Optional[tuple]: (bat_id, distance) of closest bat, or None if no bats found
        """
        feeder_config = self.feeder_configs[feeder_id]
        closest_bat = None
        min_distance = float('inf')
        
        for bat_id, bat_state in self.bat_states.items():
            if bat_state.last_position:
                distance = self.position_processor.calculate_distance(
                    bat_state.last_position, feeder_config
                )
                # Only consider bats that are reasonably close to the feeder
                if distance <= feeder_config.activation_distance * 3 and distance < min_distance:
                    min_distance = distance
                    closest_bat = (bat_id, distance)
        
        return closest_bat
    
    def _check_multiple_bats_near_feeder(self, feeder_id: int, triggering_bat_id: str) -> bool:
        """
        Check if there are multiple bats within 0.3m of the feeder
        
        Args:
            feeder_id: ID of the feeder
            triggering_bat_id: ID of the bat that triggered the beam break
            
        Returns:
            bool: True if there are other bats within 0.3m of feeder
        """
        feeder_config = self.feeder_configs[feeder_id]
        collision_distance = 0.3  # meters
        
        bats_near_feeder = 0
        
        for bat_id, bat_state in self.bat_states.items():
            if bat_state.last_position:
                distance = self.position_processor.calculate_distance(
                    bat_state.last_position, feeder_config
                )
                if distance <= collision_distance:
                    bats_near_feeder += 1
        
        # If more than 1 bat near feeder, return True (collision detected)
        return bats_near_feeder > 1
    
    def _is_position_nan(self, position: Position) -> bool:
        """
        Check if position contains NaN values
        
        Args:
            position: Position object to check
            
        Returns:
            bool: True if any coordinate is NaN
        """
        import math
        return (math.isnan(position.x) or 
                math.isnan(position.y) or 
                math.isnan(position.z))
    
    def _deliver_reward(self, feeder_id: int, bat_id: str, manual: bool = False) -> bool:
        """
        Deliver reward through specified feeder
        
        Args:
            feeder_id: ID of the feeder
            bat_id: ID of the bat receiving reward
            manual: Whether this is a manual reward
            
        Returns:
            bool: True if reward delivery was successful
        """
        feeder_config = self.feeder_configs[feeder_id]
        
        print(f"Attempting to activate motor {feeder_id} for {feeder_config.duration_ms}ms at speed {feeder_config.speed}...")
        success = self.arduino.activate_motor(feeder_id, feeder_config.duration_ms, feeder_config.speed)
        
        if success:
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
        Manually trigger reward delivery
        
        Args:
            feeder_id: ID of the feeder
            
        Returns:
            bool: True if successful
        """
        if feeder_id not in self.feeder_configs:
            return False
            
        # Use a generic bat ID for manual rewards
        bat_id = "manual"
        return self._deliver_reward(feeder_id, bat_id, manual=True)
    
    def update_feeder_config(self, feeder_id: int, **kwargs):
        """Update feeder configuration"""
        if feeder_id in self.feeder_configs:
            config = self.feeder_configs[feeder_id]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def get_bat_states(self) -> Dict[str, BatState]:
        """Get current bat states"""
        return self.bat_states.copy()
    
    def get_feeder_configs(self) -> Dict[int, FeederConfig]:
        """Get current feeder configurations"""
        return self.feeder_configs.copy()
    
    def set_dynamic_position_enabled(self, enabled: bool):
        """Set whether dynamic feeder position updates are enabled"""
        self.dynamic_position_enabled = enabled