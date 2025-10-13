"""
Cortex motion capture system integration using pycortex SDK.
"""
import sys
import os
import time
import threading
from typing import Optional, Callable, Dict, Any, List
from .base_tracker import BaseTracker
from utils.data_structures import Position

# Add pycortex to path if needed
pycortex_path = os.path.join(os.path.dirname(__file__), '..', 'pycortex')
if os.path.exists(pycortex_path) and pycortex_path not in sys.path:
    sys.path.insert(0, pycortex_path)

try:
    from pycortex import CortexSDK, CortexConfig, CortexPresets, maVerbosityLevel
    from pycortex.cortex_sdk import sFrameOfData, XEMPTY
    PYCORTEX_AVAILABLE = True
except ImportError as e:
    print(f"Warning: pycortex not available: {e}")
    PYCORTEX_AVAILABLE = False
    # Define placeholder constants
    XEMPTY = 9999999.0


class CortexTracker(BaseTracker):
    """Cortex motion capture system tracker using pycortex SDK"""
    
    def __init__(self, config: Dict[str, Any], callback: Optional[Callable[[Position], None]] = None):
        """
        Initialize Cortex tracker
        
        Args:
            config: Cortex configuration dictionary containing:
                - server_ip: IP address of Cortex host
                - server_port: Port for Cortex communication
                - frame_rate: Expected frame rate (Hz)
                - timeout: Connection timeout (seconds)
            callback: Function to call when new position data is received
        """
        super().__init__(callback)
        self.config = config
        self.sdk: Optional['CortexSDK'] = None
        self.connected = False
        self.streaming = False
        
        # Configuration
        self.server_ip = config.get('server_ip', '127.0.0.1')
        self.server_port = config.get('server_port', 1001)
        self.frame_rate = config.get('frame_rate', 120)
        self.timeout = config.get('timeout', 5.0)
        self.coordinate_scale = config.get('coordinate_scale', 1000.0)  # mm to meters
        
        # Body/marker mapping
        self.body_mapping: Dict[str, str] = {}  # Maps body names to bat IDs
        self.last_frame_time = 0
        self.frame_count = 0
        self.tracking_start_time = 0
        self.connection_lock = threading.Lock()
        
        # Reconnection settings
        self.auto_reconnect = True
        self.reconnect_interval = 5.0
        self.reconnect_thread: Optional[threading.Thread] = None
        
        # Bat state management
        self.enabled_bats = set()  # Track which bats are enabled
        self.all_bats = set()  # Track all known bats
        
    def connect(self) -> bool:
        """
        Connect to Cortex system
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not PYCORTEX_AVAILABLE:
            print("Error: pycortex SDK not available. Please ensure pycortex is installed.")
            return False
            
        with self.connection_lock:
            try:
                # Create pycortex configuration
                cortex_config = self._create_cortex_config()
                
                # Initialize SDK
                self.sdk = CortexSDK(config=cortex_config)
                
                # Set up error callback for logging
                self.sdk.set_error_msg_handler(self._on_sdk_error)
                
                # Set verbosity for debugging
                self.sdk.set_verbosity(maVerbosityLevel.VL_Warning)
                
                # Connect to Cortex
                print(f"Connecting to Cortex at {self.server_ip}:{self.server_port}...")
                
                if self.sdk.connect():
                    self.connected = True
                    
                    # Get and display Cortex info
                    info = self.sdk.get_cortex_info()
                    if info:
                        print(f"Connected to Cortex: {info['program_name']} v{info['program_version']}")
                        print(f"Host: {info['host_name']} ({info['host_ip']})")
                    
                    # Get body definitions
                    bodies = self.sdk.get_bodies()
                    print(f"Available bodies: {len(bodies)}")
                    for i, body in enumerate(bodies):
                        # Map body names to bat IDs
                        bat_id = f"bat_{i:02d}"
                        self.body_mapping[body['name']] = bat_id
                        self.all_bats.add(bat_id)
                        self.enabled_bats.add(bat_id)  # Enable all bats by default
                        print(f"  {body['name']} -> {bat_id}: {body['markers']} markers")
                    
                    # Set up frame callback
                    self.sdk.set_data_handler(self._on_frame_received)
                    self.streaming = True
                    self.tracking_start_time = time.time()
                    
                    return True
                else:
                    print(f"Failed to connect to Cortex at {self.server_ip}:{self.server_port}")
                    self.connected = False
                    return False
                    
            except Exception as e:
                print(f"Failed to connect to Cortex: {e}")
                self.connected = False
                return False
    
    def disconnect(self):
        """Disconnect from Cortex system"""
        with self.connection_lock:
            self.auto_reconnect = False  # Prevent reconnection attempts
            
            if self.reconnect_thread and self.reconnect_thread.is_alive():
                self.reconnect_thread.join(timeout=1.0)
            
            if self.sdk:
                try:
                    self.sdk.disconnect()
                except:
                    pass
                self.sdk = None
            
            self.connected = False
            self.streaming = False
            print("Cortex tracker disconnected")
    
    def _create_cortex_config(self) -> 'CortexConfig':
        """Create pycortex configuration from batjuice config"""
        # Check if connecting to localhost or remote
        if self.server_ip in ['127.0.0.1', 'localhost']:
            config = CortexPresets.localhost()
        else:
            config = CortexPresets.remote_host(self.server_ip)
        
        # Override with specific settings
        config.host_port = self.server_port
        config.host_multicast_port = self.server_port
        config.min_timeout_ms = int(self.timeout * 1000)
        
        return config
    
    def _on_sdk_error(self, level: int, message: bytes):
        """Handle SDK error messages"""
        try:
            msg = message.decode(errors='replace')
            if level <= 1:  # Error level
                print(f"Cortex SDK Error: {msg}")
                # Check for connection loss
                if "connection" in msg.lower() or "timeout" in msg.lower():
                    self._handle_connection_loss()
            elif level == 2:  # Warning level
                print(f"Cortex SDK Warning: {msg}")
        except Exception as e:
            print(f"Error handling SDK message: {e}")
    
    def _on_frame_received(self, frame: 'sFrameOfData'):
        """
        Callback for receiving frame data from Cortex
        
        Args:
            frame: Frame data from Cortex SDK
        """
        try:
            current_time = time.time()
            self.frame_count += 1
            
            # Process each body in the frame
            for i in range(frame.nBodies):
                body = frame.BodyData[i]
                body_name = body.szName.decode(errors='replace').strip('\x00')
                
                # Get bat ID from mapping
                bat_id = self.body_mapping.get(body_name, f"unknown_{body_name}")
                
                # Skip disabled bats
                if bat_id not in self.enabled_bats:
                    continue
                
                # Process markers for this body
                valid_markers = []
                for j in range(body.nMarkers):
                    marker = body.Markers[j]
                    x, y, z = float(marker[0]), float(marker[1]), float(marker[2])
                    
                    # Check if marker is valid (not occluded)
                    if x != XEMPTY and y != XEMPTY and z != XEMPTY:
                        # Convert from mm to meters
                        valid_markers.append((
                            x / self.coordinate_scale,
                            y / self.coordinate_scale,
                            z / self.coordinate_scale
                        ))
                
                # If we have valid markers, compute position
                if valid_markers:
                    # Calculate centroid of valid markers
                    x_avg = sum(m[0] for m in valid_markers) / len(valid_markers)
                    y_avg = sum(m[1] for m in valid_markers) / len(valid_markers)
                    z_avg = sum(m[2] for m in valid_markers) / len(valid_markers)
                    
                    # Create position object
                    position = Position(
                        bat_id=bat_id,
                        tag_id=f"{body_name}_centroid",
                        x=x_avg,
                        y=y_avg,
                        z=z_avg,
                        timestamp=current_time
                    )
                    
                    # Add position to queue and trigger callback
                    self._add_position(position)
            
            # Process unidentified markers if needed
            if frame.nUnidentifiedMarkers > 0:
                for j in range(frame.nUnidentifiedMarkers):
                    marker = frame.UnidentifiedMarkers[j]
                    x, y, z = float(marker[0]), float(marker[1]), float(marker[2])
                    
                    if x != XEMPTY and y != XEMPTY and z != XEMPTY:
                        position = Position(
                            bat_id="unidentified",
                            tag_id=f"marker_{j}",
                            x=x / self.coordinate_scale,
                            y=y / self.coordinate_scale,
                            z=z / self.coordinate_scale,
                            timestamp=current_time
                        )
                        self._add_position(position)
            
            self.last_frame_time = current_time
            
        except Exception as e:
            print(f"Error processing Cortex frame: {e}")
    
    def _flush_buffer(self):
        """
        Flush stale data from buffer before starting tracking
        
        Clear the position queue and reset frame counters to ensure
        we start with fresh data when tracking begins.
        """
        # Clear the position queue
        while not self.position_queue.empty():
            try:
                self.position_queue.get_nowait()
            except queue.Empty:
                break
        
        # Reset frame counters
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.tracking_start_time = time.time()
        
    def _fetch_data(self):
        """
        Fetch data from Cortex system
        
        Note: With pycortex SDK, data is pushed via callbacks rather than polled.
        This method checks connection health and handles reconnection.
        """
        if not self.connected:
            return
            
        # Check connection health
        current_time = time.time()
        if current_time - self.last_frame_time > 2.0:  # No data for 2 seconds
            if self.sdk and self.sdk.is_connected():
                # Connection is up but no data
                if not self.sdk.is_streaming():
                    print("Cortex connected but not streaming")
            else:
                # Connection lost
                self._handle_connection_loss()
        
        # Sleep briefly to prevent busy waiting
        time.sleep(0.01)
    
    def _handle_connection_loss(self):
        """Handle loss of connection to Cortex"""
        with self.connection_lock:
            if not self.connected:
                return  # Already handling disconnection
                
            print("Lost connection to Cortex")
            self.connected = False
            self.streaming = False
            
            # Start reconnection thread if enabled
            if self.auto_reconnect and not (self.reconnect_thread and self.reconnect_thread.is_alive()):
                self.reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
                self.reconnect_thread.start()
    
    def _reconnect_loop(self):
        """Attempt to reconnect to Cortex periodically"""
        print(f"Starting reconnection attempts every {self.reconnect_interval} seconds...")
        
        while self.auto_reconnect and not self.connected:
            time.sleep(self.reconnect_interval)
            
            if not self.auto_reconnect:
                break
                
            print("Attempting to reconnect to Cortex...")
            if self.connect():
                print("Successfully reconnected to Cortex")
                break
            else:
                print(f"Reconnection failed, retrying in {self.reconnect_interval} seconds...")
    
    def is_connected(self) -> bool:
        """Check if connected to Cortex"""
        return self.connected and self.sdk is not None
    
    def is_streaming(self) -> bool:
        """Check if actively streaming data"""
        if not self.is_connected():
            return False
        return self.streaming and (time.time() - self.last_frame_time < 2.0)
    
    def get_frame_rate(self) -> float:
        """Get current frame rate"""
        if self.frame_count > 0 and self.tracking_start_time > 0:
            elapsed = time.time() - self.tracking_start_time
            if elapsed > 0:
                return self.frame_count / elapsed
        return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current tracker status"""
        status = {
            'connected': self.is_connected(),
            'streaming': self.is_streaming(),
            'frame_rate': self.get_frame_rate(),
            'frame_count': self.frame_count,
            'bodies': len(self.body_mapping),
            'enabled_bats': len(self.enabled_bats),
            'last_frame_time': self.last_frame_time
        }
        
        if self.sdk and self.connected:
            info = self.sdk.get_cortex_info()
            if info:
                status['cortex_info'] = info
        
        return status
    
    # Bat management methods (matching Ciholas interface)
    def enable_bat(self, bat_id: str):
        """Enable tracking for a specific bat"""
        if bat_id in self.all_bats:
            self.enabled_bats.add(bat_id)
            print(f"Enabled tracking for {bat_id}")
    
    def disable_bat(self, bat_id: str):
        """Disable tracking for a specific bat"""
        if bat_id in self.enabled_bats:
            self.enabled_bats.remove(bat_id)
            print(f"Disabled tracking for {bat_id}")
    
    def is_bat_enabled(self, bat_id: str) -> bool:
        """Check if a bat is enabled for tracking"""
        return bat_id in self.enabled_bats
    
    def get_all_bats(self) -> List[str]:
        """Get list of all known bat IDs"""
        return list(self.all_bats)
    
    def get_enabled_bats(self) -> List[str]:
        """Get list of enabled bat IDs"""
        return list(self.enabled_bats)