"""
Standard Task Logic - Basic proximity-based reward delivery

This is the current task logic converted to the new simplified interface.
Scientists can use this as a template for creating their own logic.
"""
from task_logic.interface import BatInfo, FeederInfo, TriggerEvent
from task_logic.utils import calculate_distance


def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Standard reward logic: deliver reward if bat is active and close to feeder
    
    Args:
        bat: Information about the bat
        feeder: Information about the feeder  
        event: The trigger event
        config: Configuration parameters (can include custom thresholds)
        
    Returns:
        bool: True if reward should be delivered
    """
    # Get configuration parameters (with defaults)
    max_distance = config.get('max_distance', feeder.activation_radius)
    min_reward_interval = config.get('min_reward_interval', 0.2)  # seconds
    
    # Basic checks - bat must be active
    if not bat.is_active:
        return False
    
    # Check if bat is within activation radius
    distance = calculate_distance(bat.position, feeder.position)
    if distance > max_distance:
        return False
    
    # Check minimum time between rewards
    if bat.time_since_last_reward is not None and bat.time_since_last_reward < min_reward_interval:
        return False
    
    # Check feeder availability  
    if not feeder.is_available:
        return False
    
    # All checks passed - deliver reward
    return True