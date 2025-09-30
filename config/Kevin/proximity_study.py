"""
Proximity Reward Logic - Reward based on distance thresholds

This task logic rewards bats when they are within a configurable distance
from a feeder when they trigger the beam break sensor.

Scientists can modify this file to customize the reward decision logic.
"""
from task_logic.interface import BatInfo, FeederInfo, TriggerEvent
from task_logic.utils import calculate_distance


def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Proximity-based reward with configurable distance thresholds

    This function is called every time a bat triggers a beam break.
    Return True to deliver a reward, False to withhold it.

    Configuration parameters (from task_logic_config in .json file):
    - activation_radius: Distance threshold for reward in meters (default: feeder.activation_radius)
    - reward_probability: Probability of reward when conditions met (default: 1.0)

    Args:
        bat: Information about the bat (position, active state, reward history)
        feeder: Information about the feeder (position, availability, settings)
        event: The trigger event details (type, timestamp)
        config: Task-specific configuration from task_logic_config section

    Returns:
        bool: True if reward should be delivered, False otherwise
    """
    # Get configuration parameters
    activation_radius = config.get('activation_radius', feeder.activation_radius)
    reward_probability = config.get('reward_probability', 1.0)

    # Check 1: Bat must be in ACTIVE state (eligible for rewards)
    if not bat.is_active:
        return False

    # Check 2: Feeder must be available (not owned by another bat)
    if not feeder.is_available:
        return False

    # Check 3: Calculate 3D distance from bat to feeder
    distance = calculate_distance(bat.position, feeder.position)

    # Check 4: Bat must be within activation radius
    if distance > activation_radius:
        return False

    # Check 5: Apply reward probability (for partial reinforcement schedules)
    import random
    if random.random() >= reward_probability:
        return False

    # All checks passed - deliver reward!
    return True