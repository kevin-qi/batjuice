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
        self.config = self._load_config()
        self.mock_config = None  # Loaded only when mock mode is used
    
    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                print(f"Loaded configuration from {self.config_file}")
                return config
        except Exception as e:
            print(f"Error loading config from {self.config_file}: {e}")
            return self._get_default_config()
    
    def load_mock_config(self) -> Dict[str, Any]:
        """Load mock configuration when needed"""
        if self.mock_config is None:
            try:
                with open(self.mock_config_file, 'r') as f:
                    self.mock_config = json.load(f)
                    print(f"Loaded mock configuration from {self.mock_config_file}")
            except Exception as e:
                print(f"Error loading mock config from {self.mock_config_file}: {e}")
                self.mock_config = self._get_default_mock_config()
        return self.mock_config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if file loading fails"""
        return {
            "rtls_system": {"backend": "cortex"},
            "cortex": {"server_ip": "127.0.0.1", "server_port": 1001, "timeout": 5.0, "frame_rate": 120},
            "ciholas": {"server_ip": "192.168.1.100", "server_port": 7667, "timeout": 5.0, "frame_rate": 100},
            "room": {
                "boundaries": {"x_min": 0.0, "x_max": 5.0, "y_min": 0.0, "y_max": 3.0, "z_min": 0.0, "z_max": 2.5},
                "units": "meters"
            },
            "feeders": [
                {"id": 0, "position": [1.0, 1.0, 1.0], "activation_distance": 0.8, "duration_ms": 500, "probability": 1.0},
                {"id": 1, "position": [4.0, 1.0, 1.0], "activation_distance": 0.8, "duration_ms": 500, "probability": 1.0}
            ],
            "arduino": {"port": "COM3", "baudrate": 9600, "timeout": 1.0},
            "gui": {"update_rate_hz": 30, "plot_update_rate_hz": 10, "max_flight_points": 10000},
            "logging": {"data_directory": "data", "session_prefix": "BatFeeder", "log_level": "INFO"}
        }
    
    def _get_default_mock_config(self) -> Dict[str, Any]:
        """Return default mock configuration if file loading fails"""
        return {
            "mock_rtls": {
                "data_file": "data/flight_positions.npy",
                "bat_count": 2,
                "bat_ids": ["Bat_001", "Bat_002"],
                "tag_ids": [1, 2],
                "loop_data": True
            },
            "mock_arduino": {
                "log_file": "mock_arduino.txt"
            }
        }
    
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
                activation_distance=feeder.get("activation_distance", 0.8),
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