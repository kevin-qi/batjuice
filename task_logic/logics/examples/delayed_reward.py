"""
Delayed Reward Logic - Reward after a time delay

Example of time-based reward delivery where bats must remain near feeder
for a specified duration before receiving reward.
"""
from task_logic.interface import BatInfo, FeederInfo, TriggerEvent
from task_logic.utils import calculate_distance
import time


# Global state to track bat presence at feeders
_bat_arrival_times = {}


def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Delayed reward logic - bat must stay near feeder for specified time
    
    Configuration parameters:
    - delay_seconds: How long bat must remain near feeder (default: 2.0)
    - max_distance: Distance threshold (default: feeder.activation_radius)
    - reset_on_leave: Reset timer if bat leaves area (default: True)
    """
    # Get configuration
    delay_seconds = config.get('delay_seconds', 2.0)
    max_distance = config.get('max_distance', feeder.activation_radius)
    reset_on_leave = config.get('reset_on_leave', True)
    
    current_time = event.timestamp
    bat_feeder_key = f"{bat.id}_{feeder.id}"
    
    # Must be active bat
    if not bat.is_active:
        # Reset timer if bat becomes inactive
        _bat_arrival_times.pop(bat_feeder_key, None)
        return False
    
    # Check if bat is within range
    distance = calculate_distance(bat.position, feeder.position)
    within_range = distance <= max_distance
    
    if within_range:
        # Bat is in range
        if bat_feeder_key not in _bat_arrival_times:
            # First time in range - record arrival
            _bat_arrival_times[bat_feeder_key] = current_time
            return False  # Not enough time yet
        
        # Check if enough time has passed
        time_in_area = current_time - _bat_arrival_times[bat_feeder_key]
        if time_in_area >= delay_seconds:
            # Enough time has passed - deliver reward and reset timer
            _bat_arrival_times.pop(bat_feeder_key, None)
            return feeder.is_available
        else:
            # Still waiting
            return False
    else:
        # Bat is out of range
        if reset_on_leave and bat_feeder_key in _bat_arrival_times:
            # Reset timer if configured to do so
            _bat_arrival_times.pop(bat_feeder_key, None)
        return False