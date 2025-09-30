"""
Proximity Reward Logic - Reward based on distance thresholds

This task logic rewards bats when they are within a configurable distance
from a feeder when they trigger the beam break sensor.

All parameters come from the feeder configuration in the JSON file.
Scientists can modify this file to customize the reward decision logic.
"""
from task_logic.interface import BatInfo, FeederInfo, TriggerEvent
from task_logic.utils import calculate_distance


def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Proximity-based reward using feeder-specific parameters

    This function is called every time a bat triggers a beam break.
    Return True to deliver a reward, False to withhold it.

    All configuration comes from the feeder properties set in the JSON config:
    - feeder.activation_radius: Distance threshold for reward (meters)
    - feeder.probability: Probability of reward when conditions met (0.0-1.0)

    These values can be modified in real-time through the GUI.

    Args:
        bat: Information about the bat (position, active state, reward history)
        feeder: Information about the feeder (position, availability, settings)
        event: The trigger event details (type, timestamp)
        config: Empty dict (all config now in feeder properties)

    Returns:
        bool: True if reward should be delivered, False otherwise
    """
    # Check 1: Bat must be in ACTIVE state (eligible for rewards)
    if not bat.is_active:
        return False

    # Check 2: Feeder must be available (not owned by another bat)
    if not feeder.is_available:
        return False

    # Check 3: Calculate 3D distance from bat to feeder
    distance = calculate_distance(bat.position, feeder.position)

    # Check 4: Bat must be within activation radius (from feeder config)
    if distance > feeder.activation_radius:
        return False

    # Check 5: Apply reward probability (from feeder config, for partial reinforcement)
    import random
    if random.random() >= feeder.probability:
        return False

    # All checks passed - deliver reward!
    return True