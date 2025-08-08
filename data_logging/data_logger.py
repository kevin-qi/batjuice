"""
Data logging system for the bat feeder experiment.
"""
import os
import csv
import json
import time
from datetime import datetime
from typing import List, Dict, Any
from utils.data_structures import Position, RewardEvent, TTLEvent, FeederConfig


class DataLogger:
    """Handles logging of experimental data"""
    
    def __init__(self, log_config: Dict[str, Any]):
        """
        Initialize data logger
        
        Args:
            log_config: Logging configuration dictionary
        """
        self.config = log_config
        self.data_dir = log_config.get('data_directory', './data')
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_info = None
        
        # Create data directory
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize log files will be called when session starts
        self.files_initialized = False
        
    def update_session_info(self, session_info: Dict[str, Any]):
        """Update session information and initialize log files"""
        self.session_info = session_info
        self.data_dir = session_info.get('data_path', './data')
        
        # Create session-specific filename
        name = session_info.get('name', 'BatFeeder').replace(' ', '_')
        date = session_info.get('date', datetime.now().strftime('%y%m%d'))
        self.session_id = f"{name}_{date}"
        
        # Create data directory
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize log files
        self._init_log_files()
        self.files_initialized = True
    
    def _init_log_files(self):
        """Initialize log files with headers"""
        self.files_initialized = True
        
        # Single events file for all experimental events
        self.events_file = os.path.join(self.data_dir, f'{self.session_id}_events.csv')
        with open(self.events_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'event_type', 'feeder_id', 'bat_id', 'manual', 'duration_ms', 'details'])
        
        # Config log
        self.config_file = os.path.join(self.data_dir, f'{self.session_id}_config.json')
    
    def log_position(self, position: Position):
        """Position logging disabled - not needed for analysis"""
        # Positions not logged to reduce file size and improve performance
        pass
    
    def log_positions(self, positions: List[Position]):
        """Log multiple positions efficiently"""
        # Positions not logged to reduce file size and improve performance
        pass
    
    def log_reward(self, reward_event: RewardEvent):
        """Log reward delivery event"""
        if not self.files_initialized:
            return
            
        try:
            with open(self.events_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    reward_event.timestamp,
                    'reward',
                    reward_event.feeder_id,
                    reward_event.bat_id,
                    reward_event.manual,
                    '',  # duration_ms not in RewardEvent - get from config if needed
                    ''  # details field for future use
                ])
                f.flush()  # Force write to disk immediately
            print(f"Logged reward: feeder_{reward_event.feeder_id}, bat_{reward_event.bat_id}")
        except Exception as e:
            print(f"Error logging reward: {e}")
    
    def log_ttl(self, ttl_event: TTLEvent):
        """Log TTL pulse event"""
        if not self.files_initialized:
            return
            
        try:
            with open(self.events_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    ttl_event.timestamp,
                    'ttl',
                    -1,  # TTL feeder_id = -1 to distinguish from actual feeders
                    'TTL',  # bat_id = "TTL"
                    False,  # manual = False
                    '',  # duration_ms field empty for TTL
                    'pulse'  # details contains signal type
                ])
                f.flush()  # Force write to disk immediately
            print(f"Logged TTL: pulse")
        except Exception as e:
            print(f"Error logging TTL: {e}")
    
    def log_beam_break(self, feeder_id: int, timestamp: float = None):
        """Log beam break event"""
        if not self.files_initialized:
            return
            
        if timestamp is None:
            timestamp = time.time()
            
        try:
            with open(self.events_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    'beam_break',
                    feeder_id,
                    '',  # bat_id empty for beam breaks
                    False,  # manual = False
                    '',  # duration_ms empty for beam breaks
                    ''  # details empty for beam breaks
                ])
                f.flush()  # Force write to disk immediately
            print(f"Logged beam break: feeder_{feeder_id}")
        except Exception as e:
            print(f"Error logging beam break: {e}")
    
    def log_motor_event(self, feeder_id: int, action: str, duration_ms: int = 0):
        """Log motor start/stop event to events.csv"""
        if not self.files_initialized:
            return
            
        try:
            timestamp = time.time()
            with open(self.events_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    f'motor_{action}',  # 'motor_start' or 'motor_stop'
                    feeder_id,
                    '',  # bat_id empty for motor events
                    False,  # manual = False
                    duration_ms if action == 'start' else '',  # duration only for start
                    ''  # details empty for motor events
                ])
                f.flush()
        except Exception as e:
            print(f"Error logging motor event: {e}")
    
    def log_session_start(self):
        """Log session start event"""
        if not self.files_initialized:
            return
            
        try:
            with open(self.events_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    time.time(),
                    'session_start',
                    '',  # feeder_id empty
                    '',  # bat_id empty
                    False,  # manual = False
                    '',  # duration_ms empty
                    self.session_id  # details contains session ID
                ])
                f.flush()
            print(f"Logged session start: {self.session_id}")
        except Exception as e:
            print(f"Error logging session start: {e}")
    
    def log_session_end(self):
        """Log session end event"""
        if not self.files_initialized:
            return
            
        try:
            with open(self.events_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    time.time(),
                    'session_end',
                    '',  # feeder_id empty
                    '',  # bat_id empty
                    False,  # manual = False
                    '',  # duration_ms empty
                    self.session_id  # details contains session ID
                ])
                f.flush()
            print(f"Logged session end: {self.session_id}")
        except Exception as e:
            print(f"Error logging session end: {e}")

    def log_config_change(self, feeder_configs: List[FeederConfig], 
                         change_description: str = ""):
        """Log configuration changes"""
        try:
            config_data = {
                'timestamp': time.time(),
                'session_id': self.session_id,
                'change_description': change_description,
                'feeders': []
            }
            
            for config in feeder_configs:
                config_data['feeders'].append({
                    'feeder_id': config.feeder_id,
                    'duration_ms': config.duration_ms,
                    'probability': config.probability,
                    'x_position': config.x_position,
                    'y_position': config.y_position,
                    'z_position': config.z_position,
                    'activation_distance': config.activation_distance
                })
            
            # Append to config file
            config_log = []
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    try:
                        config_log = json.load(f)
                        if not isinstance(config_log, list):
                            config_log = [config_log]
                    except:
                        config_log = []
            
            config_log.append(config_data)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_log, f, indent=2)
                
        except Exception as e:
            print(f"Error logging config change: {e}")
    
    def get_session_id(self) -> str:
        """Get current session ID"""
        return self.session_id
    
    def get_log_files(self) -> Dict[str, str]:
        """Get paths to all log files"""
        return {
            'events': self.events_file,
            'config': self.config_file
        }