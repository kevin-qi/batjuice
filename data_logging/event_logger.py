"""
Event logging system using Python's logging module.
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any


class EventLogger:
    """Handles system event logging"""
    
    def __init__(self, log_config: Dict[str, Any]):
        """
        Initialize event logger
        
        Args:
            log_config: Logging configuration dictionary
        """
        self.config = log_config
        self.log_level = getattr(logging, log_config.get('log_level', 'INFO'))
        
        # Create logs directory
        log_dir = log_config.get('data_directory', './data')
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger('batfeeder')
        self.logger.setLevel(self.log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = log_config.get('log_filename', 'feeder_session.log')
        log_file = os.path.join(log_dir, f'{session_id}_{log_filename}')
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(self.log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def log_system_start(self, config: Dict[str, Any]):
        """Log system startup"""
        self.info("Bat feeder system starting")
        self.info(f"Tracking system: {config.get('tracking_system', 'unknown')}")
        self.info(f"Number of feeders: {len(config.get('feeders', []))}")
    
    def log_connection(self, component: str, status: str):
        """Log connection status"""
        self.info(f"{component} connection: {status}")
    
    def log_feeder_activation(self, feeder_id: int, bat_id: str, state: str):
        """Log feeder state change"""
        self.info(f"Feeder {feeder_id} {state} for bat {bat_id}")
    
    def log_reward_delivery(self, feeder_id: int, bat_id: str, manual: bool = False):
        """Log reward delivery"""
        reward_type = "manual" if manual else "automatic"
        self.info(f"Reward delivered ({reward_type}): Feeder {feeder_id}, Bat {bat_id}")
    
    def log_config_change(self, feeder_id: int, parameter: str, old_value, new_value):
        """Log configuration change"""
        self.info(f"Config change - Feeder {feeder_id}: {parameter} {old_value} -> {new_value}")
    
    def log_error(self, component: str, error: str):
        """Log component error"""
        self.error(f"{component} error: {error}")
    
    def log_beam_break(self, feeder_id: int):
        """Log beam break event"""
        self.debug(f"Beam break detected on feeder {feeder_id}")
    
    def log_ttl_pulse(self):
        """Log TTL pulse reception"""
        self.debug("TTL pulse received")