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
    
    def __init__(self, log_config: Dict[str, Any], feeder_state_getter=None):
        """
        Initialize data logger
        
        Args:
            log_config: Logging configuration dictionary
            feeder_state_getter: Optional callable that returns JSON string of current feeder states
        """
        self.config = log_config
        self.data_dir = log_config.get('data_directory', './data')
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_info = None
        self.get_feeder_states = feeder_state_getter
        
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

    def _write_event(self, timestamp: float, event_type: str, feeder_id, bat_id, 
                     manual: bool, duration_ms, details_override=None):
        """
        Internal helper to write any event with automatic feeder state capture.
        Single source of truth for all event logging - implements DRY principle.
        
        Args:
            timestamp: Event timestamp
            event_type: Type of event (e.g., 'beam_break', 'reward', 'motor_start')
            feeder_id: ID of feeder involved (or -1/'' for global events)
            bat_id: ID of bat involved (or '' if not applicable)
            manual: Whether this was a manual action
            duration_ms: Duration in milliseconds (or '' if not applicable)
            details_override: If provided, use this instead of feeder states (for special events)
        """
        if not self.files_initialized:
            return
        
        try:
            # Get current feeder states automatically (unless overridden)
            if details_override is not None:
                details = details_override
            else:
                details = self.get_feeder_states() if self.get_feeder_states else ''
            
            with open(self.events_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    event_type,
                    feeder_id,
                    bat_id,
                    manual,
                    duration_ms,
                    details
                ])
                f.flush()  # Force write to disk immediately
        except Exception as e:
            print(f"Error writing event: {e}")
    
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
        try:
            self._write_event(
                timestamp=reward_event.timestamp,
                event_type='reward',
                feeder_id=reward_event.feeder_id,
                bat_id=reward_event.bat_id,
                manual=reward_event.manual,
                duration_ms=''  # duration_ms not in RewardEvent
            )
            print(f"Logged reward: feeder_{reward_event.feeder_id}, bat_{reward_event.bat_id}")
        except Exception as e:
            print(f"Error logging reward: {e}")
    
    def log_ttl(self, ttl_event: TTLEvent):
        """Log TTL pulse event"""
        try:
            self._write_event(
                timestamp=ttl_event.timestamp,
                event_type='ttl',
                feeder_id=-1,  # TTL feeder_id = -1 to distinguish from actual feeders
                bat_id='TTL',  # bat_id = "TTL"
                manual=False,
                duration_ms=''
            )
            print(f"Logged TTL: pulse")
        except Exception as e:
            print(f"Error logging TTL: {e}")
    
    def log_beam_break(self, feeder_id: int, timestamp: float = None):
        """Log beam break event"""
        if timestamp is None:
            timestamp = time.time()
            
        try:
            self._write_event(
                timestamp=timestamp,
                event_type='beam_break',
                feeder_id=feeder_id,
                bat_id='',  # bat_id empty for beam breaks
                manual=False,
                duration_ms=''
            )
            print(f"Logged beam break: feeder_{feeder_id}")
        except Exception as e:
            print(f"Error logging beam break: {e}")
    
    def log_motor_event(self, feeder_id: int, action: str, duration_ms: int = 0, arduino_timestamp: float = None):
        """Log motor start/stop event to events.csv"""
        try:
            # Use Arduino timestamp if provided, otherwise use PC timestamp
            timestamp = arduino_timestamp if arduino_timestamp is not None else time.time()

            self._write_event(
                timestamp=timestamp,
                event_type=f'motor_{action}',  # 'motor_start' or 'motor_stop'
                feeder_id=feeder_id,
                bat_id='',  # bat_id empty for motor events
                manual=False,
                duration_ms=duration_ms if action == 'start' else ''
            )
        except Exception as e:
            print(f"Error logging motor event: {e}")
    
    def log_session_start(self):
        """Log session start event"""
        try:
            self._write_event(
                timestamp=time.time(),
                event_type='session_start',
                feeder_id='',  # feeder_id empty
                bat_id='',  # bat_id empty
                manual=False,
                duration_ms='',
                details_override=self.session_id  # details contains session ID
            )
            print(f"Logged session start: {self.session_id}")
        except Exception as e:
            print(f"Error logging session start: {e}")
    
    def log_session_end(self):
        """Log session end event"""
        try:
            self._write_event(
                timestamp=time.time(),
                event_type='session_end',
                feeder_id='',  # feeder_id empty
                bat_id='',  # bat_id empty
                manual=False,
                duration_ms='',
                details_override=self.session_id  # details contains session ID
            )
            print(f"Logged session end: {self.session_id}")
        except Exception as e:
            print(f"Error logging session end: {e}")

    
    def log_feeder_position_change(self, feeder_id: int, old_position_index: int, 
                                  new_position_index: int, position_name: str, 
                                  coordinates: tuple, timestamp: float = None):
        """Log feeder position change event"""
        if timestamp is None:
            timestamp = time.time()
            
        try:
            # Keep position details in addition to feeder states for this special event
            position_details = f"from_idx:{old_position_index} to_idx:{new_position_index} name:{position_name} coords:{coordinates}"
            
            self._write_event(
                timestamp=timestamp,
                event_type='feeder_position_change',
                feeder_id=feeder_id,
                bat_id='',  # bat_id empty for feeder events
                manual=False,  # manual = False (system triggered)
                duration_ms='',
                details_override=position_details  # Keep position info for this special event
            )
            print(f"Logged feeder position change: feeder_{feeder_id} -> {position_name}")
        except Exception as e:
            print(f"Error logging feeder position change: {e}")

    def log_config_change(self, feeder_configs: List[FeederConfig], 
                         change_description: str = ""):
        """Log configuration changes"""
        try:
            # Ensure config_file is set
            if not hasattr(self, 'config_file') or not self.config_file:
                # Create default config file path if not initialized
                self.config_file = os.path.join(self.data_dir, f'{self.session_id}_config.json')
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
                    'activation_radius': config.activation_radius
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