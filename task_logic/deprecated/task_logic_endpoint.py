"""
Modular task logic endpoint for feeder reward decisions.

This module provides a clean interface for determining whether to deliver
rewards based on the complete system state. Users can customize the logic
in this file without touching the broader codebase.
"""
import time
import math
from typing import Optional
from .system_state import SystemState, SystemBat, SystemFeeder


class TaskLogicEndpoint:
    """
    Simple, robust task logic endpoint.
    
    Core logic:
    1. Bat gets reward -> becomes INACTIVE
    2. Bat must fly D distance away from reward feeder for >0.2s to become ACTIVE again
    3. Only ACTIVE bats can get rewards
    4. Multi-bat: first bat "owns" feeder until it moves >0.5m away
    """
    
    def __init__(self):
        """Initialize task logic endpoint"""
        # Core task parameters
        self.reactivation_distance = 0.5  # meters - how far bat must fly to reactivate
        self.reactivation_time = 0.2  # seconds - how long bat must be far away
        self.feeder_ownership_distance = 0.5  # meters - how far owner must move to release feeder
        
        # System parameters
        self.position_timeout = 1.0  # seconds - max age of position data
    
    def should_deliver_reward(self, system_state: SystemState, feeder_id: int, 
                            triggering_bat_id: str) -> tuple:
        """
        Simple reward decision logic.
        
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
            return False, f"Bat {triggering_bat_id} is INACTIVE - must fly {self.reactivation_distance}m away for {self.reactivation_time}s"
        
        # Check feeder ownership (multi-bat scenario)
        if not self._check_feeder_ownership(feeder, bat, system_state, current_time):
            return False, f"Feeder {feeder_id} is owned by bat {feeder.owner_bat_id}"
        
        # All checks passed - reward should be delivered
        return True, f"Reward approved for ACTIVE bat {triggering_bat_id}"
    
    def _update_bat_activation_state(self, bat: SystemBat, feeders: dict, current_time: float):
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
        
        # Check if bat is far enough away
        if distance >= self.reactivation_distance:
            # Bat is far enough - check timing requirement
            if bat.distance_threshold_met_time is None:
                # First time being far enough - record timestamp
                bat.distance_threshold_met_time = current_time
            elif current_time - bat.distance_threshold_met_time >= self.reactivation_time:
                # Been far enough for required time - reactivate!
                bat.activation_state = "ACTIVE"
                bat.distance_threshold_met_time = None
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
        
        # Calculate distance from owner to feeder
        owner_pos = owner_bat.last_position[:3]
        distance = self._calculate_3d_distance(owner_pos, feeder.position)
        
        if distance >= self.feeder_ownership_distance:
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
        feeder = system_state.feeders[feeder_id]
        current_time = time.time()
        
        # Set bat to INACTIVE state
        bat.activation_state = "INACTIVE"
        bat.last_reward_feeder_id = feeder_id
        bat.last_reward_time = current_time
        bat.distance_threshold_met_time = None  # Reset distance timing
    
    def _calculate_3d_distance(self, pos1: tuple, pos2: tuple) -> float:
        """
        Calculate 3D Euclidean distance between two positions.
        
        Args:
            pos1: (x, y, z) coordinates
            pos2: (x, y, z) coordinates
            
        Returns:
            float: Distance in meters
        """
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        dz = pos1[2] - pos2[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def update_parameters(self, **kwargs):
        """
        Update task logic parameters.
        
        Available parameters:
            reactivation_distance: Distance bat must fly to reactivate (meters)
            reactivation_time: Time bat must be far away to reactivate (seconds)  
            feeder_ownership_distance: Distance owner must move to release feeder (meters)
            position_timeout: Max age of position data (seconds)
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                print(f"Updated {key} to {value}")
            else:
                print(f"Warning: Unknown parameter {key}")
    
    def get_parameters(self) -> dict:
        """Get current task logic parameters"""
        return {
            'reactivation_distance': self.reactivation_distance,
            'reactivation_time': self.reactivation_time,
            'feeder_ownership_distance': self.feeder_ownership_distance,
            'position_timeout': self.position_timeout
        }


# Global instance for easy access
task_logic = TaskLogicEndpoint()


def should_deliver_reward(system_state: SystemState, feeder_id: int, 
                         triggering_bat_id: str) -> tuple:
    """
    Convenience function for reward decision.
    
    This is the main entry point that the feeder manager will call.
    
    Args:
        system_state: Complete system state
        feeder_id: ID of feeder with beam break
        triggering_bat_id: ID of triggering bat
        
    Returns:
        tuple: (should_deliver: bool, reason: str)
    """
    return task_logic.should_deliver_reward(system_state, feeder_id, triggering_bat_id)


def update_task_parameters(**kwargs):
    """Update task logic parameters"""
    task_logic.update_parameters(**kwargs)


def get_task_parameters() -> dict:
    """Get current task logic parameters"""
    return task_logic.get_parameters()


def update_bat_state_after_reward(system_state: SystemState, feeder_id: int, bat_id: str):
    """Update bat state after successful reward delivery"""
    task_logic.update_bat_state_after_reward(system_state, feeder_id, bat_id)
