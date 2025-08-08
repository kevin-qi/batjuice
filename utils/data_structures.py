"""
Core data structures for the bat feeder system.
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import time


class FeederState(Enum):
    """Feeder activation states"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class TrackingSystem(Enum):
    """Available tracking systems"""
    CORTEX = "cortex"
    CIHOLAS = "ciholas"
    MOCK = "mock"


@dataclass
class Position:
    """Position data from tracking systems"""
    bat_id: str
    tag_id: str
    x: float
    y: float
    z: float
    timestamp: float
    
    @classmethod
    def create_now(cls, bat_id: str, tag_id: str, x: float, y: float, z: float):
        """Create position with current timestamp"""
        return cls(bat_id, tag_id, x, y, z, time.time())


@dataclass
class BatState:
    """State information for a bat"""
    bat_id: str
    tag_id: str
    feeder_state: FeederState
    last_position: Optional[Position]
    flight_count: int = 0  # Number of feeder activations (beam breaks)
    reward_count: int = 0  # Number of actual rewards delivered
    last_feeder_activation: float = 0.0
    last_feeder_deactivation: float = 0.0
    last_triggered_feeder_id: Optional[int] = None  # ID of feeder that was last triggered by this bat
    last_beam_break_time: float = 0.0  # Time of last beam break event
    feeder_flights: dict = None  # Number of beam breaks per feeder {feeder_id: count}
    feeder_rewards: dict = None  # Number of rewards per feeder {feeder_id: count}
    
    def __post_init__(self):
        if self.last_feeder_activation == 0.0:
            self.last_feeder_activation = time.time()
        if self.feeder_flights is None:
            self.feeder_flights = {}
        if self.feeder_rewards is None:
            self.feeder_rewards = {}
    
    def add_flight_to_feeder(self, feeder_id: int):
        """Increment flight count for specific feeder"""
        if self.feeder_flights is None:
            self.feeder_flights = {}
        self.feeder_flights[feeder_id] = self.feeder_flights.get(feeder_id, 0) + 1
        self.flight_count += 1
    
    def add_reward_from_feeder(self, feeder_id: int):
        """Increment reward count for specific feeder"""
        if self.feeder_rewards is None:
            self.feeder_rewards = {}
        self.feeder_rewards[feeder_id] = self.feeder_rewards.get(feeder_id, 0) + 1
        self.reward_count += 1
    
    def get_feeder_stats_string(self, max_feeders: int = 4) -> tuple:
        """Get formatted strings for per-feeder flights and rewards"""
        flight_parts = []
        reward_parts = []
        
        for i in range(max_feeders):
            flights = self.feeder_flights.get(i, 0) if self.feeder_flights else 0
            rewards = self.feeder_rewards.get(i, 0) if self.feeder_rewards else 0
            flight_parts.append(str(flights))
            reward_parts.append(str(rewards))
        
        return ("|".join(flight_parts), "|".join(reward_parts))
    
    def can_receive_reward(self, current_time: float, min_distance: float, feeder_position: tuple) -> bool:
        """
        Check if bat can receive reward based on time and distance constraints
        
        Args:
            current_time: Current timestamp
            min_distance: Minimum distance required from last triggered feeder
            feeder_position: (x, y, z) position of the feeder being checked
            
        Returns:
            bool: True if bat can receive reward
        """
        # If no previous beam break, can always receive reward
        if self.last_beam_break_time == 0.0:
            return True
            
        # Must wait at least 0.5 seconds since last beam break
        time_since_last_break = current_time - self.last_beam_break_time
        if time_since_last_break < 0.5:
            return False
            
        # If we have a last position, check distance constraint
        if self.last_position and self.last_triggered_feeder_id is not None:
            current_distance = ((self.last_position.x - feeder_position[0]) ** 2 + 
                              (self.last_position.y - feeder_position[1]) ** 2 + 
                              (self.last_position.z - feeder_position[2]) ** 2) ** 0.5
            return current_distance >= min_distance
            
        return True


@dataclass
class FeederConfig:
    """Configuration for a single feeder"""
    feeder_id: int
    duration_ms: int = 500  # Motor activation duration
    speed: int = 255  # Motor speed (0-255)
    probability: float = 1.0  # Probability of reward delivery (0.0-1.0)
    x_position: float = 0.0  # Physical position of feeder
    y_position: float = 0.0
    z_position: float = 0.0
    activation_distance: float = 50.0  # Minimum distance for activation (cm)
    beam_break_count: int = 0
    reward_delivery_count: int = 0
    recent_trigger_positions: list = None  # Recent positions where beam breaks occurred
    
    def __post_init__(self):
        if self.recent_trigger_positions is None:
            self.recent_trigger_positions = []
    
    def update_position_from_trigger(self, position: Position):
        """Update feeder position based on last trigger position"""
        self.x_position = position.x
        self.y_position = position.y
        self.z_position = position.z
    
    def get_position(self) -> tuple:
        """Get current feeder position as tuple"""
        return (self.x_position, self.y_position, self.z_position)


@dataclass
class RewardEvent:
    """Record of a reward delivery event"""
    feeder_id: int
    bat_id: str
    timestamp: float
    manual: bool = False  # True if manually triggered
    
    @classmethod
    def create_now(cls, feeder_id: int, bat_id: str, manual: bool = False):
        """Create reward event with current timestamp"""
        return cls(feeder_id, bat_id, time.time(), manual)


@dataclass
class TTLEvent:
    """TTL pulse event for synchronization"""
    timestamp: float
    
    @classmethod
    def create_now(cls):
        """Create TTL event with current timestamp"""
        return cls(time.time())