"""
Simple Task Logic - Clean, minimal implementation

This replaces the overly complex task logic with a simple, intuitive system:

1. Bat gets reward -> becomes INACTIVE 
2. Bat must fly D meters away from reward feeder for >0.2s to become ACTIVE again
3. Only ACTIVE bats can get rewards
4. Multi-bat: first bat "owns" feeder until it moves >0.5m away

This file can be imported instead of the full task_logic_endpoint if you want
the minimal implementation without all the complex state tracking.
"""
import time
import math
from typing import Optional, Dict, Tuple


class SimpleBat:
    """Minimal bat state for task logic"""
    def __init__(self, bat_id: str):
        self.bat_id = bat_id
        self.activation_state = "ACTIVE"  # "ACTIVE" or "INACTIVE"
        self.last_reward_feeder_id: Optional[int] = None
        self.last_reward_time: Optional[float] = None
        self.distance_threshold_met_time: Optional[float] = None
        self.last_position: Optional[Tuple[float, float, float, float]] = None  # x,y,z,timestamp


class SimpleFeeder:
    """Minimal feeder state for task logic"""
    def __init__(self, feeder_id: int, position: Tuple[float, float, float]):
        self.feeder_id = feeder_id
        self.position = position
        self.owner_bat_id: Optional[str] = None
        self.owner_since: Optional[float] = None


class SimpleTaskLogic:
    """Ultra-simple task logic implementation"""
    
    def __init__(self):
        self.reactivation_distance = 0.5  # meters - how far bat must fly to reactivate
        self.reactivation_time = 0.2  # seconds - how long bat must be far away
        self.feeder_ownership_distance = 0.5  # meters - how far owner must move to release feeder
        self.position_timeout = 1.0  # seconds - max age of position data
        
        # Simple state storage
        self.bats: Dict[str, SimpleBat] = {}
        self.feeders: Dict[int, SimpleFeeder] = {}
    
    def add_bat(self, bat_id: str):
        """Add a bat to the system"""
        if bat_id not in self.bats:
            self.bats[bat_id] = SimpleBat(bat_id)
    
    def add_feeder(self, feeder_id: int, position: Tuple[float, float, float]):
        """Add a feeder to the system"""
        self.feeders[feeder_id] = SimpleFeeder(feeder_id, position)
    
    def update_bat_position(self, bat_id: str, x: float, y: float, z: float):
        """Update bat position"""
        if bat_id not in self.bats:
            self.add_bat(bat_id)
        
        self.bats[bat_id].last_position = (x, y, z, time.time())
        
        # Update activation state based on new position
        self._update_bat_activation_state(self.bats[bat_id])
    
    def should_deliver_reward(self, feeder_id: int, triggering_bat_id: str) -> Tuple[bool, str]:
        """
        Main decision point: should we deliver reward?
        
        Returns:
            (should_deliver, reason)
        """
        current_time = time.time()
        
        # Validate inputs
        if feeder_id not in self.feeders:
            return False, f"Unknown feeder {feeder_id}"
        
        if triggering_bat_id not in self.bats:
            self.add_bat(triggering_bat_id)
        
        bat = self.bats[triggering_bat_id]
        feeder = self.feeders[feeder_id]
        
        # Update bat activation state
        self._update_bat_activation_state(bat)
        
        # Check if bat is ACTIVE (can receive rewards)
        if bat.activation_state != "ACTIVE":
            return False, f"Bat {triggering_bat_id} is INACTIVE - must fly {self.reactivation_distance}m away for {self.reactivation_time}s"
        
        # Check feeder ownership
        if not self._check_feeder_ownership(feeder, bat, current_time):
            return False, f"Feeder {feeder_id} is owned by bat {feeder.owner_bat_id}"
        
        # All checks passed - deliver reward
        self._deliver_reward(bat, feeder, current_time)
        return True, f"Reward delivered to ACTIVE bat {triggering_bat_id}"
    
    def _update_bat_activation_state(self, bat: SimpleBat):
        """Update bat activation state based on current position"""
        if bat.activation_state == "ACTIVE":
            return  # Already active
        
        current_time = time.time()
        
        # Check if we have valid position and reward feeder data
        if (bat.last_reward_feeder_id is None or 
            bat.last_reward_feeder_id not in self.feeders or
            bat.last_position is None):
            bat.activation_state = "ACTIVE"
            return
        
        # Check if position is recent enough
        pos_timestamp = bat.last_position[3]
        if current_time - pos_timestamp > self.position_timeout:
            return  # Position too old, stay INACTIVE
        
        # Calculate distance from last reward feeder
        bat_pos = bat.last_position[:3]
        feeder_pos = self.feeders[bat.last_reward_feeder_id].position
        distance = self._calculate_distance(bat_pos, feeder_pos)
        
        # Check if bat is far enough away
        if distance >= self.reactivation_distance:
            # First time being far enough?
            if bat.distance_threshold_met_time is None:
                bat.distance_threshold_met_time = current_time
            # Been far enough for required time?
            elif current_time - bat.distance_threshold_met_time >= self.reactivation_time:
                bat.activation_state = "ACTIVE"
                bat.distance_threshold_met_time = None
        else:
            # Bat moved closer - reset timing
            bat.distance_threshold_met_time = None
    
    def _check_feeder_ownership(self, feeder: SimpleFeeder, triggering_bat: SimpleBat, current_time: float) -> bool:
        """Check if feeder is available for triggering bat"""
        if feeder.owner_bat_id is None:
            # No owner - claim it
            feeder.owner_bat_id = triggering_bat.bat_id
            feeder.owner_since = current_time
            return True
        
        if feeder.owner_bat_id == triggering_bat.bat_id:
            # Already owned by this bat
            return True
        
        # Owned by another bat - check if owner moved away
        if feeder.owner_bat_id not in self.bats:
            # Owner doesn't exist - claim it
            feeder.owner_bat_id = triggering_bat.bat_id
            feeder.owner_since = current_time
            return True
        
        owner_bat = self.bats[feeder.owner_bat_id]
        
        # Check if owner has recent position
        if owner_bat.last_position is None:
            return False  # No position data, keep current owner
        
        pos_timestamp = owner_bat.last_position[3]
        if current_time - pos_timestamp > self.position_timeout:
            return False  # Position too old, keep current owner
        
        # Check distance from owner to feeder
        owner_pos = owner_bat.last_position[:3]
        distance = self._calculate_distance(owner_pos, feeder.position)
        
        if distance >= self.feeder_ownership_distance:
            # Owner moved far enough - transfer ownership
            feeder.owner_bat_id = triggering_bat.bat_id
            feeder.owner_since = current_time
            return True
        
        return False  # Owner still too close
    
    def _deliver_reward(self, bat: SimpleBat, feeder: SimpleFeeder, current_time: float):
        """Update states after reward delivery"""
        bat.activation_state = "INACTIVE"
        bat.last_reward_feeder_id = feeder.feeder_id
        bat.last_reward_time = current_time
        bat.distance_threshold_met_time = None
    
    def _calculate_distance(self, pos1: Tuple[float, float, float], pos2: Tuple[float, float, float]) -> float:
        """Calculate 3D distance"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        dz = pos1[2] - pos2[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def get_bat_state(self, bat_id: str) -> Optional[str]:
        """Get bat activation state"""
        if bat_id in self.bats:
            return self.bats[bat_id].activation_state
        return None
    
    def get_feeder_owner(self, feeder_id: int) -> Optional[str]:
        """Get feeder owner"""
        if feeder_id in self.feeders:
            return self.feeders[feeder_id].owner_bat_id
        return None


# Example usage
if __name__ == "__main__":
    # Create simple task logic
    logic = SimpleTaskLogic()
    
    # Add feeder at position (0, 0, 0)
    logic.add_feeder(1, (0.0, 0.0, 0.0))
    
    # Add bat
    logic.add_bat("bat1")
    
    # Bat approaches feeder (close position)
    logic.update_bat_position("bat1", 0.1, 0.1, 0.1)
    
    # First beam break - should get reward
    should_reward, reason = logic.should_deliver_reward(1, "bat1")
    print(f"First trigger: {should_reward} - {reason}")
    print(f"Bat state: {logic.get_bat_state('bat1')}")
    
    # Second beam break immediately - should NOT get reward (INACTIVE)
    should_reward, reason = logic.should_deliver_reward(1, "bat1")
    print(f"Second trigger: {should_reward} - {reason}")
    
    # Bat moves far away
    logic.update_bat_position("bat1", 1.0, 1.0, 1.0)  # >0.5m away
    
    # Wait a bit
    time.sleep(0.3)  # >0.2s
    
    # Update position again to trigger state check
    logic.update_bat_position("bat1", 1.0, 1.0, 1.0)
    print(f"After flying away: {logic.get_bat_state('bat1')}")
    
    # Now should get reward again
    logic.update_bat_position("bat1", 0.1, 0.1, 0.1)  # Back at feeder
    should_reward, reason = logic.should_deliver_reward(1, "bat1")
    print(f"After reactivation: {should_reward} - {reason}")