"""
Proximity Reward Logic - Reward based on distance thresholds

Example of configurable proximity-based rewards with different activation zones.
"""
from task_logic.interface import BatInfo, FeederInfo, TriggerEvent
from task_logic.utils import calculate_distance


def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Proximity-based reward with configurable distance thresholds
    
    Configuration parameters:
    - activation_radius: Distance threshold for reward (default: feeder.activation_radius)
    - reward_probability: Probability of reward when conditions met (default: 1.0)
    - use_2d_distance: Use only x,y coordinates (default: False)
    """
    # Get configuration
    activation_radius = config.get('activation_radius', feeder.activation_radius)
    reward_probability = config.get('reward_probability', 1.0)
    use_2d = config.get('use_2d_distance', False)
    
    # Must be active bat
    if not bat.is_active:
        return False
    
    # Calculate distance
    if use_2d:
        # Only use x,y coordinates (ignore height)
        bat_pos_2d = (bat.position[0], bat.position[1], 0)
        feeder_pos_2d = (feeder.position[0], feeder.position[1], 0)
        distance = calculate_distance(bat_pos_2d, feeder_pos_2d)
    else:
        distance = calculate_distance(bat.position, feeder.position)
    
    # Check distance threshold
    if distance > activation_radius:
        return False
    
    # Check feeder availability
    if not feeder.is_available:
        return False
    
    # Apply probability (could be used for partial reinforcement schedules)
    import random
    return random.random() < reward_probability