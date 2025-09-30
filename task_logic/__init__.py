"""Task logic module for customizable feeder reward decisions."""

# User-facing interface for writing task logic
from .interface import BatInfo, FeederInfo, TriggerEvent, decide_reward
from .utils import calculate_distance, calculate_2d_distance, is_within_radius

# Core adapter and functions
from .adapter import TaskLogicAdapter
from .task_logic import (
    TaskLogic,
    initialize_task_logic,
    should_deliver_reward,
    update_bat_state_after_reward,
)
