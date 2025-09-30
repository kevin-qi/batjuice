"""
Core data structures for the bat feeder system.
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import time


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
class FeederConfig:
    """Feeder configuration for system compatibility"""
    feeder_id: int
    duration_ms: int = 500
    speed: int = 255
    probability: float = 1.0
    x_position: float = 0.0
    y_position: float = 0.0
    z_position: float = 0.0
    activation_radius: float = 3.0
    reactivation_distance: float = 2.0
    beam_break_count: int = 0
    reward_delivery_count: int = 0
    
    # New fields for multiple positions
    available_positions: list = None  # List of position configurations
    current_position_index: int = 0   # Index of currently selected position
    
    def __post_init__(self):
        """Initialize available_positions if None"""
        if self.available_positions is None:
            # Create single position from current x,y,z for backwards compatibility
            self.available_positions = [{
                'name': f'Position {self.feeder_id}',
                'coordinates': [self.x_position, self.y_position, self.z_position],
                'description': 'Default position'
            }]
    
    def get_current_position(self) -> tuple[float, float, float]:
        """Get current position coordinates"""
        if (self.available_positions and 
            0 <= self.current_position_index < len(self.available_positions)):
            coords = self.available_positions[self.current_position_index]['coordinates']
            return tuple(coords)
        return (self.x_position, self.y_position, self.z_position)
    
    def set_position(self, position_index: int) -> bool:
        """Set current position by index. Returns True if successful."""
        if (self.available_positions and 
            0 <= position_index < len(self.available_positions)):
            self.current_position_index = position_index
            # Update x,y,z for backwards compatibility
            coords = self.available_positions[position_index]['coordinates']
            self.x_position, self.y_position, self.z_position = coords
            return True
        return False
    
    def get_position_name(self) -> str:
        """Get name of current position"""
        if (self.available_positions and 
            0 <= self.current_position_index < len(self.available_positions)):
            return self.available_positions[self.current_position_index]['name']
        return f'Position {self.feeder_id}'


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