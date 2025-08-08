"""
Configuration interface for task logic parameters.

This module provides utilities for loading and saving task logic configurations.
"""
import json
import os
from typing import Dict, Any
from .task_logic import task_logic


class TaskLogicConfig:
    """Configuration manager for task logic parameters"""
    
    def __init__(self, config_file: str = "config/task_logic_config.json"):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = config_file
        self.default_config = {
            "reactivation_distance": 0.5,
            "reactivation_time": 0.2,
            "feeder_ownership_distance": 0.5,
            "position_timeout": 1.0
        }
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Dict: Configuration parameters
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                print(f"Loaded task logic config from {self.config_file}")
                return config
            else:
                print(f"No task logic config file found, using defaults")
                return self.default_config.copy()
        except Exception as e:
            print(f"Error loading task logic config: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]):
        """
        Save configuration to file.
        
        Args:
            config: Configuration parameters to save
        """
        try:
            # Ensure config directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"Saved task logic config to {self.config_file}")
        except Exception as e:
            print(f"Error saving task logic config: {e}")
    
    def apply_config(self, config: Dict[str, Any] = None):
        """
        Apply configuration to task logic endpoint.
        
        Args:
            config: Configuration to apply (loads from file if None)
        """
        if config is None:
            config = self.load_config()
        
        task_logic.update_parameters(**config)
        print("Applied task logic configuration")
    
    def get_current_config(self) -> Dict[str, Any]:
        """
        Get current task logic configuration.
        
        Returns:
            Dict: Current configuration
        """
        return task_logic.get_parameters()
    
    def reset_to_defaults(self):
        """Reset task logic to default parameters"""
        task_logic.update_parameters(**self.default_config)
        print("Reset task logic to default parameters")


# Global config manager instance
config_manager = TaskLogicConfig()


def load_and_apply_config():
    """Load and apply task logic configuration"""
    config_manager.apply_config()


def save_current_config():
    """Save current task logic configuration"""
    current_config = config_manager.get_current_config()
    config_manager.save_config(current_config)


def get_config_manager() -> TaskLogicConfig:
    """Get the global config manager instance"""
    return config_manager
