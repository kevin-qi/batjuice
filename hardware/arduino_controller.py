"""
Arduino controller for motor control and sensor input.
"""
import serial
import time
import threading
import queue
from typing import Optional, Dict, Any, Callable
from utils.data_structures import TTLEvent


class ArduinoController:
    """Controls Arduino for motor operations and sensor reading"""
    
    def __init__(self, config: Dict[str, Any], ttl_callback: Optional[Callable[[TTLEvent], None]] = None, motor_callback: Optional[Callable[[int, str, int], None]] = None):
        """
        Initialize Arduino controller
        
        Args:
            config: Arduino configuration dictionary
            ttl_callback: Function to call when TTL pulse is received
            motor_callback: Function to call when motor events occur (feeder_id, action, duration_ms)
        """
        self.config = config
        self.ttl_callback = ttl_callback
        self.motor_callback = motor_callback
        self.serial_conn: Optional[serial.Serial] = None
        self.running = False
        self.read_thread: Optional[threading.Thread] = None
        self.beam_break_queue = queue.Queue()
        self.ttl_queue = queue.Queue()
        
    def connect(self) -> bool:
        """
        Connect to Arduino
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            port = self.config.get('port', 'COM3')
            baudrate = self.config.get('baudrate', 9600)
            timeout = self.config.get('timeout', 1.0)
            
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout
            )
            
            # Wait for Arduino to initialize
            time.sleep(2)
            
            # Clear any existing data in buffer
            self.serial_conn.reset_input_buffer()
            
            # Start reading thread
            self.running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            
            print(f"✓ Arduino connected successfully on {port}")
            print("  Listening for Arduino messages...")
            return True
                
        except serial.SerialException as e:
            if "Access is denied" in str(e):
                print(f"✗ Arduino connection failed: {port} is in use by another program")
                print("  Please close Arduino IDE, serial monitor, or other programs using this port")
            elif "No such file or directory" in str(e) or "[Errno 2]" in str(e):
                print(f"✗ Arduino connection failed: {port} not found")
                print("  Available ports: ", end="")
                try:
                    from serial.tools import list_ports
                    ports = [p.device for p in list_ports.comports()]
                    if ports:
                        print(", ".join(ports))
                        print(f"  Try updating config to use one of: {ports}")
                    else:
                        print("No serial ports found")
                except ImportError:
                    print("Cannot list available ports")
            else:
                print(f"✗ Arduino connection failed: {e}")
            return False
        except Exception as e:
            print(f"✗ Unexpected error connecting to Arduino: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def disconnect(self):
        """Disconnect from Arduino"""
        self.stop_reading()
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Arduino disconnected")
    
    def start_reading(self):
        """Start reading sensor data from Arduino"""
        if self.running or not self.serial_conn:
            return
            
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
    
    def stop_reading(self):
        """Stop reading sensor data"""
        self.running = False
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
    
    def _read_loop(self):
        """Main reading loop for sensor data"""
        while self.running and self.serial_conn:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode().strip()
                    self._process_arduino_message(line)
            except Exception as e:
                print(f"Error reading from Arduino: {e}")
                time.sleep(0.1)
    
    def _process_arduino_message(self, message: str):
        """Process incoming message from Arduino"""
        if not message:
            return
            
        parts = message.split(':')
        if len(parts) < 2:
            return
            
        msg_type = parts[0]
        
        if msg_type == 'BEAM':
            # Beam break message: BEAM:feeder_id
            try:
                feeder_id = int(parts[1])
                self.beam_break_queue.put(feeder_id)
            except ValueError:
                print(f"Invalid beam break message: {message}")
                
        elif msg_type == 'TTL':
            # TTL pulse message: TTL
            ttl_event = TTLEvent.create_now()
            self.ttl_queue.put(ttl_event)
            if self.ttl_callback:
                self.ttl_callback(ttl_event)
                
        elif msg_type == 'MOTOR_START':
            # Motor activation message: MOTOR_START:feeder_id:duration_ms
            try:
                feeder_id = int(parts[1])
                duration_ms = int(parts[2])
                print(f"Motor {feeder_id} started for {duration_ms}ms")
                # Log motor activation event
                if hasattr(self, 'motor_callback') and self.motor_callback:
                    self.motor_callback(feeder_id, 'start', duration_ms)
            except (ValueError, IndexError):
                print(f"Invalid motor start message: {message}")
                
        elif msg_type == 'MOTOR_STOP':
            # Motor stop message: MOTOR_STOP:feeder_id
            try:
                feeder_id = int(parts[1])
                print(f"Motor {feeder_id} stopped")
                # Log motor stop event
                if hasattr(self, 'motor_callback') and self.motor_callback:
                    self.motor_callback(feeder_id, 'stop', 0)
            except (ValueError, IndexError):
                print(f"Invalid motor stop message: {message}")
                
        elif msg_type == 'ERROR':
            print(f"Arduino error: {parts[1]}")
    
    def activate_motor(self, feeder_id: int, duration_ms: int, speed: int = 255) -> bool:
        """
        Activate motor for specified duration and speed
        
        Args:
            feeder_id: ID of the feeder (0-3)
            duration_ms: Duration to run motor in milliseconds
            speed: Motor speed (0-255, default 255)
            
        Returns:
            bool: True if command sent successfully
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            print("✗ Arduino not connected - cannot activate motor")
            return False
            
        try:
            command = f"MOTOR:{feeder_id}:{duration_ms}:{speed}\n"
            print(f"Sending to Arduino: {command.strip()}")
            self.serial_conn.write(command.encode())
            self.serial_conn.flush()  # Ensure command is sent immediately
            print(f"✓ Motor command sent successfully")
            return True
        except Exception as e:
            print(f"✗ Error sending motor command: {e}")
            return False
    
    def get_beam_breaks(self) -> list[int]:
        """
        Get all beam break events from queue
        
        Returns:
            list[int]: List of feeder IDs with beam breaks
        """
        events = []
        try:
            while True:
                events.append(self.beam_break_queue.get_nowait())
        except queue.Empty:
            pass
        return events
    
    def get_ttl_events(self) -> list[TTLEvent]:
        """
        Get all TTL events from queue
        
        Returns:
            list[TTLEvent]: List of TTL events
        """
        events = []
        try:
            while True:
                events.append(self.ttl_queue.get_nowait())
        except queue.Empty:
            pass
        return events