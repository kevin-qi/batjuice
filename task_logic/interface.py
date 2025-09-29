"""
Task Logic Interface - Simple data structures for scientists to use
"""
from typing import NamedTuple, Optional


class BatInfo(NamedTuple):
    """Information about a bat - provided by system"""
    id: str
    position: tuple[float, float, float]  # (x, y, z) in meters
    position_age: float  # seconds since position update
    is_active: bool  # can receive rewards
    time_since_last_reward: Optional[float]  # seconds, None if never
    last_reward_feeder_id: Optional[int]


class FeederInfo(NamedTuple):
    """Information about a feeder - provided by system"""
    id: int
    position: tuple[float, float, float]  # (x, y, z) in meters
    is_available: bool  # not owned by another bat
    activation_radius: float  # meters
    duration_ms: int
    probability: float


class TriggerEvent(NamedTuple):
    """The event that triggered evaluation"""
    type: str  # "beam_break", "proximity", "timer"
    feeder_id: int
    bat_id: str
    timestamp: float


# This is the ONLY function scientists need to implement
def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Scientists implement this single function to control reward delivery.
    
    Args:
        bat: Information about the bat requesting reward
        feeder: Information about the feeder that was triggered
        event: The trigger event details
        config: Task-specific configuration from config file
        
    Returns:
        bool: True if reward should be delivered, False otherwise
    """
    raise NotImplementedError("Scientists must implement this function")