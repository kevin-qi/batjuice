"""
Reward delivery system for controlling when feeders should provide rewards.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.data_structures import FeederConfig


class RewardSystem:
    """Manages reward delivery logic and criteria"""
    
    def __init__(self):
        """Initialize the reward system"""
        pass
    
    def should_deliver_reward(self, feeder_config: "FeederConfig") -> bool:
        """
        Determine if a reward should be delivered based on feeder configuration
        
        Args:
            feeder_config: Configuration for the feeder
            
        Returns:
            bool: True if reward should be delivered, False otherwise
        """
        # Basic implementation - could be enhanced with more sophisticated logic
        # For now, always allow reward delivery when triggered
        return True