"""
Random Reward Logic - Control baseline with random reward delivery

Example of control condition where rewards are delivered randomly,
independent of bat position or behavior.
"""
import random
from task_logic.interface import BatInfo, FeederInfo, TriggerEvent


def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Random reward logic for control experiments
    
    Configuration parameters:
    - probability: Base probability of reward (default: 0.3)
    - ignore_position: Ignore bat position completely (default: True)
    - min_reward_interval: Minimum time between rewards (default: None)
    """
    # Get configuration
    probability = config.get('probability', 0.3)
    ignore_position = config.get('ignore_position', True)
    min_reward_interval = config.get('min_reward_interval', None)
    
    # Must be active bat
    if not bat.is_active:
        return False
    
    # Check minimum reward interval if specified
    if (min_reward_interval is not None and 
        bat.time_since_last_reward is not None and 
        bat.time_since_last_reward < min_reward_interval):
        return False
    
    # Check feeder availability
    if not feeder.is_available:
        return False
    
    # Apply random probability
    if not ignore_position:
        # Still require bat to be somewhat close to feeder
        from task_logic.utils import calculate_distance
        distance = calculate_distance(bat.position, feeder.position)
        if distance > feeder.activation_radius * 2:  # Double the normal radius
            return False
    
    return random.random() < probability