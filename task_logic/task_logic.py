"""
Consolidated Task Logic Implementation

This module consolidates all task logic configuration and computation into a single file.
All task logic parameters are loaded from config/user_config.json through the settings
module - this is the single source of truth for all configuration.

Core logic:
1. Bat gets reward -> becomes INACTIVE
2. Bat must fly D distance away from reward feeder for >T seconds to become ACTIVE again  
3. Only ACTIVE bats can get rewards
4. Multi-bat: first bat "owns" feeder until it moves >D meters away
"""
import json
import math
import os
import time
from typing import Dict, Any, Optional, Tuple
try:
    from .system_state import SystemState, SystemBat, SystemFeeder
except ImportError:
    from system_state import SystemState, SystemBat, SystemFeeder


class TaskLogic:
    """Consolidated task logic with centralized configuration management"""
    
    def __init__(self, settings=None):
        """Initialize task logic with configuration from settings"""
        self.settings = settings
        
        # Load configuration from settings - this is the single source of truth
        self._load_config()
        
        # Apply loaded configuration to instance variables
        self._apply_config()
    
    def _load_config(self):
        """Load configuration from settings object - now using individual feeder parameters"""
        # Only load global timing parameters, distances come from individual feeders
        self.config = {
            "reactivation_time": 0.2,
            "position_timeout": 1.0
        }
        
        if self.settings:
            # Try to get timing parameters from any remaining global config
            global_config = self.settings.config
            if "reactivation_time" in global_config:
                self.config["reactivation_time"] = global_config["reactivation_time"]
            if "position_timeout" in global_config:
                self.config["position_timeout"] = global_config["position_timeout"]
        
        print(f"Loaded global task logic config: {self.config}")
    
    def _apply_config(self):
        """Apply loaded configuration to instance variables"""
        self.reactivation_time = self.config["reactivation_time"]
        self.position_timeout = self.config["position_timeout"]
        
        print(f"Applied task logic config - reactivation_time: {self.reactivation_time}s, "
              f"position_timeout: {self.position_timeout}s"
              f" (distance parameters now come from individual feeders)")
    
    def save_config(self):
        """Save current configuration to user_config.json - distance params now stored per feeder"""
        try:
            # Only save global timing parameters since distance parameters are now per-feeder
            config_file = "config/user_config.json"
            
            # Load the full user config
            with open(config_file, 'r') as f:
                user_config = json.load(f)
            
            # Update global timing parameters
            user_config["reactivation_time"] = self.reactivation_time
            user_config["position_timeout"] = self.position_timeout
            
            # Save back to file
            with open(config_file, 'w') as f:
                json.dump(user_config, f, indent=2)
            
            print(f"Saved global task logic config to {config_file}")
            
            # Update settings object if available
            if self.settings:
                self.settings.config["reactivation_time"] = self.reactivation_time
                self.settings.config["position_timeout"] = self.position_timeout
            
        except Exception as e:
            print(f"Error saving task logic config to user_config.json: {e}")
    
    def update_parameters(self, **kwargs):
        """
        Update task logic parameters and save to user_config.json.
        
        Available parameters:
            reactivation_time: Time bat must be far away to reactivate (seconds)  
            position_timeout: Max age of position data (seconds)
            
        Note: Distance parameters (activation_radius, reactivation_distance) are now 
              configured per feeder and should be updated via feeder configuration.
        """
        updated_params = []
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                setattr(self, key, value)
                self.config[key] = value
                updated_params.append(f"{key}: {old_value} -> {value}")
                print(f"Updated {key} from {old_value} to {value}")
            else:
                print(f"Warning: Unknown parameter '{key}' ignored")
        
        if updated_params:
            self.save_config()
            return f"Updated parameters: {', '.join(updated_params)}"
        return "No valid parameters updated"
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get current task logic parameters - distance parameters now come from feeders"""
        return {
            'reactivation_time': self.reactivation_time, 
            'position_timeout': self.position_timeout,
            'note': 'Distance parameters (activation_radius, reactivation_distance) are now configured per feeder'
        }
    
    def reload_config(self):
        """Reload configuration from user_config.json"""
        self._load_config()
        self._apply_config()
        return "Configuration reloaded from user_config.json"
    
    def should_deliver_reward(self, system_state: SystemState, feeder_id: int, 
                            triggering_bat_id: str) -> Tuple[bool, str]:
        """
        Main reward decision logic.
        
        Args:
            system_state: Complete system state
            feeder_id: ID of feeder with beam break
            triggering_bat_id: ID of triggering bat
            
        Returns:
            tuple: (should_deliver: bool, reason: str)
        """
        current_time = time.time()
        
        # Validate inputs
        if feeder_id not in system_state.feeders:
            return False, f"Unknown feeder ID: {feeder_id}"
        
        if triggering_bat_id not in system_state.bats:
            return False, f"Unknown bat ID: {triggering_bat_id}"
        
        feeder = system_state.feeders[feeder_id]
        bat = system_state.bats[triggering_bat_id]
        
        # Check if feeder and bat are active
        if not feeder.active:
            return False, f"Feeder {feeder_id} is inactive"
        
        if not bat.active:
            return False, f"Bat {triggering_bat_id} is inactive"
        
        # Update bat activation state based on current position
        self._update_bat_activation_state(bat, system_state.feeders, current_time)
        
        # Check if bat is in ACTIVE state (can receive rewards)
        if bat.activation_state != "ACTIVE":
            # Get reactivation distance from the feeder that last gave reward (if any)
            last_feeder_reactivation_dist = "required distance"
            if bat.last_reward_feeder_id is not None and bat.last_reward_feeder_id in system_state.feeders:
                last_feeder_reactivation_dist = f"{system_state.feeders[bat.last_reward_feeder_id].reactivation_distance}m"
            
            return False, (f"Bat {triggering_bat_id} is INACTIVE - must fly "
                         f"{last_feeder_reactivation_dist} away for {self.reactivation_time}s")
        
        # Check feeder ownership (multi-bat scenario)
        if not self._check_feeder_ownership(feeder, bat, system_state, current_time):
            return False, f"Feeder {feeder_id} is owned by bat {feeder.owner_bat_id}"
        
        # All checks passed - reward should be delivered
        return True, f"Reward approved for ACTIVE bat {triggering_bat_id}"
    
    def _update_bat_activation_state(self, bat: SystemBat, feeders: Dict, current_time: float):
        """Update bat activation state based on current position and distance from last reward feeder"""
        if bat.activation_state == "ACTIVE":
            return  # Already active, no update needed
        
        # Bat is INACTIVE - check if it can become ACTIVE again
        if bat.last_reward_feeder_id is None or bat.last_reward_feeder_id not in feeders:
            # No valid last reward feeder, make active
            bat.activation_state = "ACTIVE"
            return
        
        # Check if bat has valid recent position
        if not bat.last_position or len(bat.last_position) < 4:
            return  # No position data, stay INACTIVE
        
        pos_timestamp = bat.last_position[3]
        if current_time - pos_timestamp > self.position_timeout:
            return  # Position too old, stay INACTIVE
        
        # Calculate distance from last reward feeder
        bat_pos = bat.last_position[:3]
        last_reward_feeder = feeders[bat.last_reward_feeder_id]
        distance = self._calculate_3d_distance(bat_pos, last_reward_feeder.position)
        
        # Check if bat is far enough away using feeder's reactivation distance
        if distance >= last_reward_feeder.reactivation_distance:
            # Bat is far enough - check timing requirement
            if bat.distance_threshold_met_time is None:
                # First time being far enough - record timestamp
                bat.distance_threshold_met_time = current_time
            elif current_time - bat.distance_threshold_met_time >= self.reactivation_time:
                # Been far enough for required time - reactivate!
                bat.activation_state = "ACTIVE"
                bat.distance_threshold_met_time = None
                print(f"Bat {bat.bat_id} reactivated after flying {distance:.2f}m away "
                      f"(threshold: {last_reward_feeder.reactivation_distance}m)")
        else:
            # Bat moved closer - reset timing
            bat.distance_threshold_met_time = None
    
    def _check_feeder_ownership(self, feeder: SystemFeeder, triggering_bat: SystemBat, 
                               system_state: SystemState, current_time: float) -> bool:
        """Check if feeder is available for triggering bat (handles multi-bat scenarios)"""
        if feeder.owner_bat_id is None:
            # Feeder has no owner - triggering bat can claim it
            feeder.owner_bat_id = triggering_bat.bat_id
            feeder.owner_since = current_time
            return True
        
        if feeder.owner_bat_id == triggering_bat.bat_id:
            # Triggering bat already owns this feeder
            return True
        
        # Feeder is owned by another bat - check if owner has moved away
        if feeder.owner_bat_id not in system_state.bats:
            # Owner bat doesn't exist anymore - clear ownership
            feeder.owner_bat_id = triggering_bat.bat_id
            feeder.owner_since = current_time
            return True
        
        owner_bat = system_state.bats[feeder.owner_bat_id]
        
        # Check if owner has valid recent position
        if not owner_bat.last_position or len(owner_bat.last_position) < 4:
            # No position data for owner - release ownership to triggering bat
            feeder.owner_bat_id = triggering_bat.bat_id
            feeder.owner_since = current_time
            return True
        
        pos_timestamp = owner_bat.last_position[3]
        if current_time - pos_timestamp > self.position_timeout:
            # Owner position too old - keep current ownership
            return False
        
        # Calculate distance from owner to feeder using feeder's activation_radius
        owner_pos = owner_bat.last_position[:3]
        distance = self._calculate_3d_distance(owner_pos, feeder.position)
        
        if distance >= feeder.activation_radius:
            # Owner has moved far enough away - transfer ownership
            feeder.owner_bat_id = triggering_bat.bat_id
            feeder.owner_since = current_time
            return True
        
        # Owner is still too close - feeder remains owned
        return False
    
    def update_bat_state_after_reward(self, system_state: SystemState, feeder_id: int, bat_id: str):
        """Update bat and feeder states after successful reward delivery"""
        if feeder_id not in system_state.feeders or bat_id not in system_state.bats:
            return
        
        bat = system_state.bats[bat_id]
        current_time = time.time()
        
        # Set bat to INACTIVE state
        bat.activation_state = "INACTIVE"
        bat.last_reward_feeder_id = feeder_id
        bat.last_reward_time = current_time
        bat.distance_threshold_met_time = None  # Reset distance timing
        
        feeder = system_state.feeders[feeder_id]
        print(f"Bat {bat_id} set to INACTIVE after reward, must fly "
              f"{feeder.reactivation_distance}m away for {self.reactivation_time}s to reactivate")
    
    def _calculate_3d_distance(self, pos1: Tuple, pos2: Tuple) -> float:
        """Calculate 3D Euclidean distance between two positions"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1] 
        dz = pos1[2] - pos2[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)


# Global instance - single source of truth for task logic
# Will be initialized with settings object when available
task_logic_adapter = None

def initialize_task_logic(settings=None):
    """Initialize the global task logic adapter"""
    global task_logic_adapter

    # Get task logic path and configuration from settings
    logic_path = None
    logic_config = {}

    if settings:
        logic_path = settings.get_task_logic_path()
        logic_config = settings.get_task_logic_config()

    # Create task logic adapter
    from .adapter import TaskLogicAdapter
    task_logic_adapter = TaskLogicAdapter(logic_path, logic_config)
    return task_logic_adapter


# Public API functions
def should_deliver_reward(system_state: SystemState, feeder_id: int,
                         triggering_bat_id: str) -> Tuple[bool, str]:
    """Main entry point for reward decisions"""
    if task_logic_adapter is None:
        initialize_task_logic()
    return task_logic_adapter.should_deliver_reward(system_state, feeder_id, triggering_bat_id)


def update_bat_state_after_reward(system_state: SystemState, feeder_id: int, bat_id: str):
    """Update bat state after successful reward delivery"""
    # This is now handled inside the TaskLogic class automatically
    # Kept for backward compatibility but delegates to core logic
    from .task_logic import TaskLogic
    task_logic = TaskLogic()
    task_logic.update_bat_state_after_reward(system_state, feeder_id, bat_id)