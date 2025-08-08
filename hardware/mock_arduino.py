"""
Mock Arduino controller that logs serial communication instead of using hardware.
This provides a simple way to test the software without requiring physical Arduino.
"""
import time
import queue
import threading
from typing import Optional, Dict, Any, Callable
from utils.data_structures import TTLEvent


class MockArduino:
    """Mock Arduino controller that logs communication to file instead of using hardware"""
    
    def __init__(self, config: Dict[str, Any], ttl_callback: Optional[Callable[[TTLEvent], None]] = None, motor_callback: Optional[Callable[[int, str, int], None]] = None):
        """
        Initialize mock Arduino
        
        Args:
            config: Arduino configuration dictionary (unused in mock)
            ttl_callback: Function to call when TTL pulse is received (unused in simple mock)
            motor_callback: Function to call when motor events occur (unused in simple mock)
        """
        self.config = config
        self.ttl_callback = ttl_callback
        self.motor_callback = motor_callback
        self.connected = False
        self.beam_break_queue = queue.Queue()
        self.ttl_queue = queue.Queue()
        
        # Mock logging
        self.log_file = "mock_arduino.txt"
        self._init_log_file()
    
    def _init_log_file(self):
        """Initialize the mock Arduino log file"""
        try:
            with open(self.log_file, 'w') as f:
                f.write(f"=== Mock Arduino Communication Log ===\n")
                f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Port: {self.config.get('port', 'COM3')} (MOCKED)\n")
                f.write(f"Baudrate: {self.config.get('baudrate', 9600)}\n\n")
        except Exception as e:
            print(f"Error initializing mock Arduino log: {e}")
    
    def _log_communication(self, direction: str, message: str):
        """Log communication message to file"""
        try:
            # Get current time with milliseconds
            now = time.time()
            timestamp = time.strftime('%H:%M:%S', time.localtime(now))
            milliseconds = int((now % 1) * 1000)
            full_timestamp = f"{timestamp}.{milliseconds:03d}"
            
            with open(self.log_file, 'a') as f:
                f.write(f"[{full_timestamp}] {direction}: {message}\n")
                f.flush()
        except Exception as e:
            print(f"Error logging mock Arduino communication: {e}")
    
    def connect(self) -> bool:
        """Mock connection always succeeds"""
        self.connected = True
        self._log_communication("SYSTEM", "Mock Arduino connected")
        print("Mock Arduino connected (logging to mock_arduino.txt)")
        return True
    
    def disconnect(self):
        """Mock disconnection"""
        self.stop_reading()
        self._log_communication("SYSTEM", "Mock Arduino disconnected")
        self.connected = False
        print("Mock Arduino disconnected")
    
    def start_reading(self):
        """Mock start reading - no actual simulation needed for simple logging"""
        if not self.connected:
            return
        self._log_communication("SYSTEM", "Started reading from Arduino")
        print("Mock Arduino ready for commands")
    
    def stop_reading(self):
        """Mock stop reading"""
        if self.connected:
            self._log_communication("SYSTEM", "Stopped reading from Arduino")
    
    def activate_motor(self, feeder_id: int, duration_ms: int, speed: int = 255) -> bool:
        """
        Mock motor activation - log what would have been sent to Arduino
        
        Args:
            feeder_id: ID of the feeder (0-3)
            duration_ms: Duration to run motor in milliseconds
            speed: Motor speed (0-255, default 255)
            
        Returns:
            bool: True if command accepted
        """
        if not self.connected:
            print("Mock Arduino not connected")
            return False
        
        # Log the command that would have been sent to real Arduino
        command = f"MOTOR:{feeder_id}:{duration_ms}:{speed}"
        self._log_communication("TX", command)
        print(f"Mock Arduino: Would send -> {command}")
        
        # Simulate immediate response that real Arduino would send
        self._log_communication("RX", f"MOTOR_START:{feeder_id}:{duration_ms}")
        
        # Log motor stop after delay (simulated)
        def delayed_log():
            time.sleep(duration_ms / 1000.0)
            self._log_communication("RX", f"MOTOR_STOP:{feeder_id}")
        
        threading.Thread(target=delayed_log, daemon=True).start()
        
        return True
    
    def get_beam_breaks(self) -> list[int]:
        """
        Get all beam break events from queue
        
        Returns:
            list[int]: List of feeder IDs with beam break events
        """
        beam_breaks = []
        while not self.beam_break_queue.empty():
            try:
                feeder_id = self.beam_break_queue.get_nowait()
                beam_breaks.append(feeder_id)
                self._log_communication("EVENT", f"BEAM_BREAK:{feeder_id}")
            except queue.Empty:
                break
        return beam_breaks
    
    def simulate_beam_break(self, feeder_id: int):
        """Simulate a beam break event for testing"""
        self.beam_break_queue.put(feeder_id)
        print(f"Mock Arduino: Simulated beam break on feeder {feeder_id}")
        self._log_communication("SIM", f"BEAM_BREAK:{feeder_id}")
    
    def get_ttl_events(self) -> list[TTLEvent]:
        """
        Get all TTL events from queue (empty in simple mock)
        
        Returns:
            list[TTLEvent]: Empty list (no TTL events simulated)
        """
        # In simple mock mode, we don't simulate TTL events
        # User can manually trigger these if needed for testing
        return []