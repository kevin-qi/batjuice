#!/usr/bin/env python3
"""
Main entry point for the bat feeder control system.
"""
import argparse
import sys
import time
from config.settings import Settings
from position_tracking.mock_tracker import MockTracker
from position_tracking.cortex_tracker import CortexTracker
from position_tracking.ciholas_tracker import CiholasTracker
from hardware.arduino_controller import ArduinoController
from hardware.mock_arduino import MockArduino
from controller.feeder_controller import FeederController
from data_logging.data_logger import DataLogger
from data_logging.event_logger import EventLogger
from gui.main_window import MainWindow
from utils.data_structures import TrackingSystem
from task_logic.task_logic import initialize_task_logic


class BatFeederSystem:
    """Main system coordinator"""
    
    def __init__(self, mock_arduino: bool = False, mock_rtls: bool = False, settings=None):
        """
        Initialize the bat feeder system
        
        Args:
            mock_arduino: Run Arduino in mock mode (log communication instead of using hardware)
            mock_rtls: Run RTLS (position tracking) in mock mode
            settings: Pre-loaded Settings instance (if None, will load default config)
        """
        self.mock_arduino = mock_arduino
        self.mock_rtls = mock_rtls
        
        # Load or use provided configuration
        if settings is None:
            self.settings = Settings()
        else:
            self.settings = settings
        
        # Initialize task logic with settings
        initialize_task_logic(self.settings)
        
        # Initialize logging
        self.data_logger = DataLogger(self.settings.get_logging_config())
        self.event_logger = EventLogger(self.settings.get_logging_config())
        
        # Initialize components
        self.position_tracker = None
        self.arduino_controller = None
        self.feeder_controller = None
        self.gui = None
        
        # System state
        self.running = False
        
    def initialize(self) -> bool:
        """
        Initialize all system components
        
        Returns:
            bool: True if initialization successful
        """
        try:
            self.event_logger.log_system_start(self.settings.config)
            
            # Initialize position tracking
            if not self._init_position_tracking():
                return False
            
            # Initialize Arduino controller
            if not self._init_arduino():
                return False
            
            # Initialize feeder manager
            if not self._init_feeder_controller():
                return False
            
            # Initialize GUI
            if not self._init_gui():
                return False
            
            # Connect GUI to system controls
            self.gui.system = self
            
            return True
            
        except Exception as e:
            self.event_logger.error(f"System initialization failed: {e}")
            return False
    
    def _init_position_tracking(self) -> bool:
        """Initialize position tracking system"""
        try:
            if self.mock_rtls:
                # Use real experimental data for mock mode
                mock_config = self.settings.get_mock_config()
                self.position_tracker = MockTracker(
                    mock_config,
                    callback=self._on_position_update
                )
                # Set frame rate based on configured RTLS backend
                rtls_backend = self.settings.get_rtls_backend()
                self.position_tracker.set_frame_rate(rtls_backend)
                print(f"Using mock tracker with real experimental data (simulating {rtls_backend})")
            else:
                tracking_system = self.settings.get_tracking_system()
                
                # Create tracker based on system type
                if tracking_system == TrackingSystem.CORTEX:
                    self.position_tracker = CortexTracker(
                        self.settings.get_cortex_config(),
                        callback=self._on_position_update
                    )
                    print("Using Cortex MotionAnalysis system")
                elif tracking_system == TrackingSystem.CIHOLAS:
                    self.position_tracker = CiholasTracker(
                        self.settings.get_ciholas_config(),
                        callback=self._on_position_update
                    )
                    print("Using Ciholas UWB system")
                else:
                    # Fallback to mock tracker for unknown systems
                    self.position_tracker = MockTracker(
                        self.settings.get_mock_config(),
                        callback=self._on_position_update
                    )
            
            # Connect to tracking system
            if self.position_tracker.connect():
                self.event_logger.log_connection("Position tracking", "connected")
                return True
            else:
                self.event_logger.log_connection("Position tracking", "failed")
                return False
                
        except Exception as e:
            self.event_logger.error(f"Position tracking initialization failed: {e}")
            return False
    
    def _init_arduino(self) -> bool:
        """Initialize Arduino controller"""
        try:
            if self.mock_arduino:
                self.arduino_controller = MockArduino(
                    self.settings.get_arduino_config(),
                    ttl_callback=self._on_ttl_pulse,
                    motor_callback=self._on_motor_event
                )
            else:
                self.arduino_controller = ArduinoController(
                    self.settings.get_arduino_config(),
                    ttl_callback=self._on_ttl_pulse,
                    motor_callback=self._on_motor_event
                )
            
            # Connect to Arduino
            if self.arduino_controller.connect():
                self.event_logger.log_connection("Arduino", "connected")
                return True
            else:
                self.event_logger.log_connection("Arduino", "failed")
                return False
                
        except Exception as e:
            self.event_logger.error(f"Arduino initialization failed: {e}")
            return False
    
    def _init_feeder_controller(self) -> bool:
        """Initialize feeder controller"""
        try:
            feeder_configs = self.settings.get_feeder_configs()
            
            self.feeder_controller = FeederController(
                feeder_configs,
                self.arduino_controller,
                reward_callback=self._on_reward_delivery,
                data_logger=self.data_logger
            )
            
            # Log initial configuration
            self.data_logger.log_config_change(feeder_configs, "System startup")
            
            return True
            
        except Exception as e:
            self.event_logger.error(f"Feeder manager initialization failed: {e}")
            return False
    
    def _init_gui(self) -> bool:
        """Initialize GUI"""
        try:
            self.gui = MainWindow(
                self.feeder_controller,
                self.settings,
                self.data_logger,
                self.event_logger
            )
            return True
            
        except Exception as e:
            self.event_logger.error(f"GUI initialization failed: {e}")
            return False
    
    def start(self):
        """Start the system (GUI only, components start with session)"""
        try:
            self.event_logger.info("GUI starting")
            
            # Run GUI (blocking call)
            self.gui.run()
            
        except Exception as e:
            self.event_logger.error(f"GUI start failed: {e}")
    
    def start_components(self):
        """Start the system components"""
        if self.running:
            return
            
        try:
            self.running = True
            
            # Start position tracking
            self.position_tracker.start_tracking()
            
            # Start Arduino reading
            self.arduino_controller.start_reading()
            
            # Start feeder manager
            self.feeder_controller.start()
            
            self.event_logger.info("System components started successfully")
            
        except Exception as e:
            self.event_logger.error(f"System start failed: {e}")
            self.stop_components()
    
    def stop_components(self):
        """Stop the system components"""
        if not self.running:
            return
            
        self.running = False
        
        try:
            # Stop components in reverse order
            if self.feeder_controller:
                self.feeder_controller.stop()
            
            if self.arduino_controller:
                self.arduino_controller.stop_reading()
            
            if self.position_tracker:
                self.position_tracker.stop_tracking()
            
            self.event_logger.info("System components stopped")
            
        except Exception as e:
            self.event_logger.error(f"Error during system shutdown: {e}")
    
    def stop(self):
        """Stop the entire system"""
        self.stop_components()
        
        try:
            # Disconnect hardware
            if self.arduino_controller:
                self.arduino_controller.disconnect()
            
            if self.position_tracker:
                self.position_tracker.disconnect()
                
        except Exception as e:
            self.event_logger.error(f"Error during disconnection: {e}")
    
    def _on_position_update(self, position):
        """Handle position update from tracking system"""
        try:
            # Position logging disabled - not needed for analysis
            
            # Update feeder manager
            self.feeder_controller.update_position(position)
            
            # Update GUI if available
            if self.gui:
                bat_states = self.feeder_controller.get_bat_states()
                self.gui.update_flight_display(bat_states)
                
        except Exception as e:
            self.event_logger.error(f"Error processing position update: {e}")
    
    def _on_reward_delivery(self, reward_event):
        """Handle reward delivery event"""
        try:
            # Log reward event
            self.data_logger.log_reward(reward_event)
            
            # Log to event logger
            self.event_logger.log_reward_delivery(
                reward_event.feeder_id,
                reward_event.bat_id,
                reward_event.manual
            )
            
        except Exception as e:
            self.event_logger.error(f"Error processing reward delivery: {e}")
    
    def _on_ttl_pulse(self, ttl_event):
        """Handle TTL pulse event"""
        try:
            # Log TTL event
            self.data_logger.log_ttl(ttl_event)
            self.event_logger.log_ttl_pulse()
            
        except Exception as e:
            self.event_logger.error(f"Error processing TTL pulse: {e}")
    
    def _on_motor_event(self, feeder_id: int, action: str, duration_ms: int):
        """Handle motor start/stop event"""
        try:
            # Log motor event
            self.data_logger.log_motor_event(feeder_id, action, duration_ms)
            print(f"Motor {feeder_id} {action} logged (duration: {duration_ms}ms)")
            
        except Exception as e:
            self.event_logger.error(f"Error processing motor event: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Bat Feeder Control System')
    parser.add_argument('--config', '-c', 
                       default='config/user_config.json',
                       help='Configuration file path (default: config/user_config.json)')
    parser.add_argument('--mock', action='store_true', 
                       help='Run in full mock mode (both Arduino and RTLS)')
    parser.add_argument('--mock-arduino', action='store_true',
                       help='Mock Arduino only - log serial communication to mock_arduino.txt')
    parser.add_argument('--mock-rtls', action='store_true', 
                       help='Mock RTLS (position tracking) only - generate simulated bat movements')
    parser.add_argument('--validate', action='store_true',
                       help='Validate configuration and exit')
    
    args = parser.parse_args()
    
    # Load and validate configuration
    try:
        from config.settings import Settings
        from config.validator import ConfigurationError
        
        settings = Settings(config_file=args.config)
        
        if args.validate:
            print(f"Configuration file '{args.config}' is valid!")
            print("Loaded experiment:", settings.config.get('experiment', {}).get('name', 'Unnamed'))
            print("Task logic:", settings.get_task_logic_module())
            return 0
            
    except ConfigurationError as e:
        print(f"Configuration error in '{args.config}':")
        print(str(e))
        return 1
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return 1
    
    # Handle mock mode flags (can override config)
    mock_arduino = args.mock or args.mock_arduino
    mock_rtls = args.mock or args.mock_rtls
    
    # Create and initialize system with custom settings
    system = BatFeederSystem(mock_arduino=mock_arduino, mock_rtls=mock_rtls, settings=settings)
    
    if not system.initialize():
        print("Failed to initialize system")
        return 1
    
    try:
        # Start system (blocks until GUI is closed)
        system.start()
        return 0
    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    finally:
        system.stop()


if __name__ == "__main__":
    main()