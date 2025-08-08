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