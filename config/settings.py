"""
Configuration management for the bat feeder system.
"""
import json
import os
from typing import Dict, Any, Optional
from utils.data_structures import TrackingSystem


class Settings:
    """Manages system configuration settings"""
    
    def __init__(self, config_file: str = "config/user_config.json", mock_config_file: str = "config/mock_config.json"):
        """
        Initialize settings from configuration files
        
        Args:
            config_file: Path to the main user configuration file
            mock_config_file: Path to the mock configuration file (loaded only when needed)
        """
        self.config_file = config_file
        self.mock_config_file = mock_config_file
        self.config = self._load_and_validate_config()
        self.mock_config = None  # Loaded only when mock mode is used  # Loaded only when mock mode is used
    
    def _load_and_validate_config(self) -> Dict[str, Any]:
        """Load and validate configuration from JSON file"""
        from .validator import ConfigurationValidator, ConfigurationError
        
        try:
            # Check if file exists
            if not os.path.exists(self.config_file):
                raise ConfigurationError(f"Configuration file not found: {self.config_file}")
            
            # Load configuration
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                print(f"Loaded configuration from {self.config_file}")
            
            # Validate configuration
            validator = ConfigurationValidator()
            validator.validate_and_raise(config)
            print("Configuration validation passed")
            
            # Apply defaults for missing optional values
            config = self._apply_defaults(config)
            
            return config
            
        except ConfigurationError:
            raise  # Re-raise configuration errors as-is
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {self.config_file}: {e}")
    
    def _apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values for missing optional configuration"""
        # Apply Arduino defaults
        arduino = config.setdefault('arduino', {})
        arduino.setdefault('port', 'COM3')
        arduino.setdefault('baudrate', 9600)
        arduino.setdefault('timeout', 1.0)
        
        # Apply GUI defaults
        gui = config.setdefault('gui', {})
        gui.setdefault('update_rate_hz', 30)
        gui.setdefault('plot_update_rate_hz', 10)
        gui.setdefault('window_title', 'BatFeeder Control System')
        
        # Apply logging defaults
        logging_config = config.setdefault('logging', {})
        logging_config.setdefault('data_directory', 'data')
        logging_config.setdefault('session_prefix', 'BatFeeder')
        logging_config.setdefault('log_level', 'INFO')
        
        return config
    
    def load_mock_config(self) -> Dict[str, Any]:
        """Load mock configuration when needed"""
        if self.mock_config is None:
            try:
                with open(self.mock_config_file, 'r') as f:
                    self.mock_config = json.load(f)
                    print(f"Loaded mock configuration from {self.mock_config_file}")
            except Exception as e:
                raise RuntimeError(f"Failed to load mock configuration from {self.mock_config_file}: {e}. Fix the mock configuration file - no default fallback available.")
        return self.mock_config
    
    
    # Updated getter methods for new config structure
    def get_rtls_backend(self) -> str:
        """Get the selected RTLS backend (cortex or ciholas)"""
        return self.config.get("rtls_system", {}).get("backend", "cortex")
    
    def get_tracking_system(self) -> TrackingSystem:
        """Get the tracking system enum based on backend"""
        backend = self.get_rtls_backend()
        if backend == "cortex":
            return TrackingSystem.CORTEX
        elif backend == "ciholas":
            return TrackingSystem.CIHOLAS
        else:
            return TrackingSystem.MOCK
    
    def get_cortex_config(self) -> Dict[str, Any]:
        """Get Cortex system configuration"""
        return self.config.get("cortex", {})
    
    def get_ciholas_config(self) -> Dict[str, Any]:
        """Get Ciholas system configuration"""
        return self.config.get("ciholas", {})
    
    def get_room_config(self) -> Dict[str, Any]:
        """Get room boundaries and settings"""
        return self.config.get("room", {})
    
    def get_feeder_configs(self) -> list:
        """Get feeder configurations (convert to FeederConfig objects)"""
        from utils.data_structures import FeederConfig
        
        feeder_data = self.config.get("feeders", [])
        feeder_configs = []
        
        for feeder in feeder_data:
            # Convert new config format to FeederConfig object
            config = FeederConfig(
                feeder_id=feeder.get("id", 0),  # Use "id" from new config
                x_position=feeder.get("position", [0, 0, 0])[0],
                y_position=feeder.get("position", [0, 0, 0])[1], 
                z_position=feeder.get("position", [0, 0, 0])[2],
                activation_radius=feeder.get("activation_radius", 3.0),
                reactivation_distance=feeder.get("reactivation_distance", 2.0),
                duration_ms=feeder.get("duration_ms", 500),
                speed=feeder.get("speed", 255),
                probability=feeder.get("probability", 1.0)
            )
            feeder_configs.append(config)
        
        return feeder_configs
    
    def get_arduino_config(self) -> Dict[str, Any]:
        """Get Arduino configuration"""
        return self.config.get("arduino", {})
    
    def get_gui_config(self) -> Dict[str, Any]:
        """Get GUI settings"""
        return self.config.get("gui", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config.get("logging", {})
    
    def get_session_config(self) -> Dict[str, Any]:
        """Get default session configuration"""
        return self.config.get("session", {})
    
    def get_task_logic_config(self) -> Dict[str, Any]:
        """Get task logic configuration"""
        return self.config.get("task_logic", {})
    
    # Mock configuration getters (only when needed)
    def get_mock_config(self) -> Dict[str, Any]:
        """Get mock configuration (loads file if not already loaded)"""
        return self.load_mock_config()
    
    def get_mock_rtls_config(self) -> Dict[str, Any]:
        """Get mock RTLS configuration"""
        mock_config = self.get_mock_config()
        return mock_config.get("mock_rtls", {})
    
    def get_mock_arduino_config(self) -> Dict[str, Any]:
        """Get mock Arduino configuration"""
        mock_config = self.get_mock_config()
        return mock_config.get("mock_arduino", {})
    
    def get_task_logic_module(self) -> str:
        """Get task logic module name"""
        experiment = self.config.get('experiment', {})
        return experiment.get('task_logic', 'standard')
    
    def get_task_logic_config(self) -> Dict[str, Any]:
        """Get configuration for the active task logic"""
        logic_name = self.get_task_logic_module()
        task_logic_configs = self.config.get('task_logic_config', {})
        return task_logic_configs.get(logic_name, {})

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration for display"""
        return {
            "RTLS Backend": self.get_rtls_backend().upper(),
            "Room Bounds": f"{self.get_room_config().get('units', 'meters')}",
            "Arduino Port": self.get_arduino_config().get('port', 'Unknown'),
            "Data Directory": self.get_logging_config().get('data_directory', 'data'),
            "Feeders": len(self.get_feeder_configs()),
            "GUI Update Rate": f"{self.get_gui_config().get('update_rate_hz', 30)} Hz"
        }