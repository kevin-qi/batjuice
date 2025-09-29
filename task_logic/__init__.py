"""Task logic module for customizable feeder reward decisions."""

# New simplified interface
from .interface import BatInfo, FeederInfo, TriggerEvent, decide_reward
from .utils import calculate_distance, calculate_2d_distance, is_within_radius
from .adapter import TaskLogicAdapter

# Legacy compatibility - will be removed in future versions
from .task_logic import (
    should_deliver_reward,
    update_task_parameters,
    get_task_parameters,
    update_bat_state_after_reward,
    reload_task_config,
    save_task_config,
    task_logic
)
