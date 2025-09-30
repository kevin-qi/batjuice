"""
Configuration management for the bat feeder system.
"""
import json
import os
from typing import Dict, Any, Optional
from utils.data_structures import TrackingSystem


class Settings:
    """Manages system configuration settings"""

    def __init__(self, config_file: str = "Kevin/proximity_study", mock_config_file: str = "config/mock_config.json"):
        """
        Initialize settings from configuration file

        Args:
            config_file: Path to experiment config file. Can be:
                - Short format: "Kevin/proximity_study" (automatically adds config/ prefix and .json suffix)
                - Full path: "config/Kevin/proximity_study.json"
            mock_config_file: Path to mock configuration file (for testing only, separate from experiments)
        """
        self.task_logic_path = None  # Initialize before _resolve_config_path
        self.config_file = self._resolve_config_path(config_file)
        self.mock_config_file = mock_config_file
        self.config = self._load_and_validate_config()
        self.mock_config = None  # Loaded on demand for mock mode

    def _resolve_config_path(self, config_file: str) -> str:
        """
        Resolve config file path and check for paired task logic file.

        Supports formats:
        - "Kevin/proximity_study" -> "config/Kevin/proximity_study.json"
        - "config/Kevin/proximity_study.json" -> as-is
        """
        # If it already has .json extension and starts with config/, use as-is
        if config_file.endswith('.json'):
            base_path = config_file.replace('.json', '')
        else:
            # Short format: add config/ prefix if not present
            if not config_file.startswith('config/'):
                base_path = f"config/{config_file}"
            else:
                base_path = config_file

        # Set paths for both .json and .py files
        json_path = f"{base_path}.json"
        py_path = f"{base_path}.py"

        # Check if paired .py file exists
        if os.path.exists(py_path):
            self.task_logic_path = py_path

        return json_path
    
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
        logging_config.setdefault('log_level', 'INFO')

        return config
    
    def _load_mock_config(self) -> Dict[str, Any]:
        """Load mock configuration file on demand"""
        if self.mock_config is None:
            try:
                with open(self.mock_config_file, 'r') as f:
                    self.mock_config = json.load(f)
                    print(f"Loaded mock configuration from {self.mock_config_file}")
            except Exception as e:
                print(f"Warning: Could not load mock config from {self.mock_config_file}: {e}")
                self.mock_config = {}
        return self.mock_config

    # Getter methods for configuration sections
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
            feeder_id = feeder.get("id", 0)
            
            # Handle both old single position and new multiple positions format
            if 'positions' in feeder:
                # New format with multiple positions
                positions = feeder.get('positions', [])
                default_index = feeder.get('default_position', 0)
                
                # Use default position coordinates for initial x,y,z
                if positions and 0 <= default_index < len(positions):
                    default_coords = positions[default_index]['coordinates']
                    x, y, z = default_coords
                else:
                    x, y, z = 0, 0, 0
                
                config = FeederConfig(
                    feeder_id=feeder_id,
                    x_position=x,
                    y_position=y,
                    z_position=z,
                    activation_radius=feeder.get("activation_radius", 3.0),
                    reactivation_distance=feeder.get("reactivation_distance", 2.0),
                    duration_ms=feeder.get("duration_ms", 500),
                    speed=feeder.get("speed", 255),
                    probability=feeder.get("probability", 1.0),
                    available_positions=positions,
                    current_position_index=default_index
                )
            else:
                # Old format with single position (backwards compatibility)
                position = feeder.get("position", [0, 0, 0])
                config = FeederConfig(
                    feeder_id=feeder_id,
                    x_position=position[0],
                    y_position=position[1], 
                    z_position=position[2],
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

    def get_mock_rtls_config(self) -> Dict[str, Any]:
        """Get mock RTLS configuration (for testing only)"""
        mock_config = self._load_mock_config()
        return mock_config.get("mock_rtls", {})

    def get_mock_arduino_config(self) -> Dict[str, Any]:
        """Get mock Arduino configuration (for testing only)"""
        mock_config = self._load_mock_config()
        return mock_config.get("mock_arduino", {})
    
    def get_task_logic_path(self) -> Optional[str]:
        """Get path to task logic Python file (if paired file exists)"""
        return self.task_logic_path

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