"""
Ciholas UWB system integration with CDP (Ciholas Data Protocol) support.
Directly interfaces with CDP data stream for real-time position tracking.
"""
import time
import socket
import struct
import threading
from typing import Optional, Callable, Dict, Any, List
from .base_tracker import BaseTracker
from utils.data_structures import Position


class CiholasTracker(BaseTracker):
    """Ciholas UWB system tracker with CDP protocol support"""
    
    def __init__(self, config: Dict[str, Any], callback: Optional[Callable[[Position], None]] = None):
        """
        Initialize Ciholas tracker
        
        Args:
            config: Ciholas configuration dictionary
            callback: Function to call when new position data is received
        """
        super().__init__(callback)
        self.config = config
        
        # CDP network configuration
        self.multicast_group = config.get('multicast_group', '239.255.76.67')
        self.local_port = config.get('local_port', 7667)
        self.timeout = config.get('timeout', 20)
        
        # Serial numbers for bat identification (ordered list)
        self.serial_numbers = config.get('serial_numbers', [])
        if not self.serial_numbers:
            print("Warning: No serial numbers provided for Ciholas tracker")

        # Sync tag serial number (to ignore in data stream)
        self.sync_serial_number = config.get('sync_serial_number', None)
        if self.sync_serial_number:
            print(f"Ciholas: Will ignore sync tag with serial number {self.sync_serial_number}")

        # Coordinate conversion settings
        self.coordinate_scale = config.get('coordinate_scale', 1000.0)  # Default: mm to meters
        self.coordinate_units = config.get('coordinate_units', 'mm')
        
        # Tracking state
        self.bat_states = {}  # Track enabled/disabled state for each bat
        self.socket: Optional[socket.socket] = None
        self._setup_bat_states()
    
    def _setup_bat_states(self):
        """Initialize bat states for all serial numbers"""
        for i, serial_num in enumerate(self.serial_numbers):
            self.bat_states[i] = {
                'serial_number': serial_num,
                'enabled': True,
                'last_position': None,
                'last_update': 0.0
            }
    
    def connect(self) -> bool:
        """
        Connect to Ciholas CDP multicast stream
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            print(f"Connecting to Ciholas CDP stream at {self.multicast_group}:{self.local_port}")
            
            # Create UDP socket for multicast
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Enable port sharing (equivalent to MATLAB's EnablePortSharing)
            if hasattr(socket, 'SO_REUSEPORT'):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            
            # Bind to local port
            self.socket.bind(('', self.local_port))
            
            # Join multicast group
            mreq = struct.pack('4sl', socket.inet_aton(self.multicast_group), socket.INADDR_ANY)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            # Set timeout
            self.socket.settimeout(self.timeout)

            # Increase OS-level receive buffer to prevent packet loss (2MB)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2097152)

            print(f"Ciholas tracker connected to CDP multicast {self.multicast_group}:{self.local_port}")

            # Note: Buffer flushing is done when tracking starts (in start_tracking())
            # to ensure fresh data at session start, not app startup

            return True
            
        except Exception as e:
            print(f"Failed to connect to Ciholas CDP stream: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
    
    def disconnect(self):
        """Disconnect from Ciholas CDP stream"""
        if self.socket:
            try:
                # Leave multicast group
                mreq = struct.pack('4sl', socket.inet_aton(self.multicast_group), socket.INADDR_ANY)
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
            except (OSError, socket.error):
                pass  # Ignore expected errors when leaving multicast group
            
            self.socket.close()
            self.socket = None
        print("Ciholas tracker disconnected")
    
    def _fetch_data(self):
        """Fetch and decode CDP data from Ciholas system"""
        if not self.socket:
            time.sleep(0.1)
            return
            
        try:
            # Continuously look for position data packets (type 309)
            position_data = self._decode_cdp_v3()
            
            if position_data:
                sn, nt, x, y, z = position_data
                self._process_position_data(sn, nt, x, y, z)
                
        except socket.timeout:
            # No data received within timeout, continue
            pass
        except Exception as e:
            print(f"Error fetching Ciholas CDP data: {e}")
            time.sleep(0.1)
    
    def _flush_buffer(self):
        """Flush old data from buffer using time-based approach

        For continuous broadcast streams, flush for a fixed duration to ensure
        the next packet received will be current (not stale buffered data).
        """
        if not self.socket:
            return

        try:
            # Set a very short timeout for rapid packet consumption
            original_timeout = self.socket.gettimeout()
            self.socket.settimeout(0.01)  # 10ms timeout

            # Flush for 0.5 seconds - guarantees next packet is current
            start_time = time.time()
            max_flush_duration = 0.5  # seconds
            packets_flushed = 0

            # Keep flushing until enough time has passed
            while (time.time() - start_time) < max_flush_duration:
                try:
                    self.socket.recv(65536)
                    packets_flushed += 1
                except socket.timeout:
                    # No data available, can exit early
                    break

            flush_duration = time.time() - start_time
            if packets_flushed > 0:
                print(f"Flushed {packets_flushed} packets in {flush_duration:.2f}s - data now current")

            # Restore original timeout
            self.socket.settimeout(original_timeout)

        except Exception as e:
            print(f"Error flushing buffer: {e}")
    
    def _decode_cdp_v3(self) -> Optional[tuple]:
        """
        Decode CDP v3 packets to extract position data.
        
        A CDP Packet is made up of a CDP Packet Header followed by a list of CDP Data Items.
        We're only interested in position data (type 309).
        
        Returns:
            tuple: (serial_number, network_time, x, y, z) if position packet found, None otherwise
        """
        if not self.socket:
            return None
            
        packet_type = 0
        
        # Only get position V3 data (type 309)
        while packet_type != 309:
            try:
                # Read UDP packet (64KB max UDP datagram size)
                packet_data, addr = self.socket.recvfrom(65536)
                
                if len(packet_data) < 21:
                    continue  # Packet too small
                
                # Cut CDP Packet Header (first 20 bytes)
                data = packet_data[20:]
                
                if len(data) < 4:
                    continue  # Not enough data for type and size
                
                # After decoding the header, look for CDP Data Items: Type, Size and Actual Data
                packet_type = struct.unpack('<H', data[0:2])[0]  # uint16, little-endian
                data = data[2:]
                
                size = struct.unpack('<H', data[0:2])[0]  # uint16, little-endian
                data = data[2:]
                
                if len(data) < size:
                    continue  # Not enough data for the specified size
                
                di_data = data[0:size]
                
                if packet_type == 309:
                    # Position data packet found
                    if len(di_data) < 24:  # Need at least 24 bytes for full position data
                        continue
                    
                    # Extract position data
                    sn_p = struct.unpack('<I', di_data[0:4])[0]  # uint32
                    di_data = di_data[4:]
                    
                    nt_p = struct.unpack('<q', di_data[0:8])[0] * 15.65e-12  # int64 * scale factor
                    di_data = di_data[8:]
                    
                    x_p = struct.unpack('<i', di_data[0:4])[0]  # int32
                    di_data = di_data[4:]
                    
                    y_p = struct.unpack('<i', di_data[0:4])[0]  # int32
                    di_data = di_data[4:]
                    
                    z_p = struct.unpack('<i', di_data[0:4])[0]  # int32

                    # Successfully decoded position packet
                    return (sn_p, nt_p, x_p, y_p, z_p)
                    
            except socket.timeout:
                # Timeout while waiting for data
                return None
            except struct.error as e:
                print(f"Error unpacking CDP data: {e}")
                continue
            except Exception as e:
                print(f"Error in CDP decoding: {e}")
                continue
        
        return None
    
    def _process_position_data(self, serial_number: int, network_time: float, x: int, y: int, z: int):
        """
        Process decoded position data and create Position objects
        
        Args:
            serial_number: Tag serial number
            network_time: Network timestamp
            x, y, z: Position coordinates (likely in mm or other units)
        """
        try:
            # Ignore sync tag if configured
            if self.sync_serial_number and serial_number == self.sync_serial_number:
                return  # Silently skip sync tag data

            # Find bat index from serial number
            bat_index = self._get_bat_index_from_serial(serial_number)

            if bat_index is None:
                # Unknown serial number, skip
                print(f"Warning: Unknown serial number {serial_number} (not in configured list: {[s['serial_number'] for s in self.bat_states.values()]})")
                return
            
            # Check if this bat is enabled
            if not self.bat_states[bat_index]['enabled']:
                return
            
            # Convert coordinates using configured scale (mm to meters)
            x_m = float(x) / self.coordinate_scale
            y_m = float(y) / self.coordinate_scale
            z_m = float(z) / self.coordinate_scale

            # Create bat and tag IDs
            bat_id = f"bat_{bat_index:02d}"
            tag_id = str(serial_number)  # Use serial number directly, no prefix

            # Create position object
            position = Position(
                bat_id=bat_id,
                tag_id=tag_id,
                x=x_m,
                y=y_m,
                z=z_m,
                timestamp=time.time()  # Use current time since network_time might need conversion
            )

            # Update bat state
            self.bat_states[bat_index]['last_position'] = position
            self.bat_states[bat_index]['last_update'] = time.time()

            # Add to position queue and trigger callback
            self._add_position(position)

            # Note: Downsampling (10x) happens in FlightDataManager, not here

        except Exception as e:
            print(f"Error processing position data: {e}")
    
    def _get_bat_index_from_serial(self, serial_number: int) -> Optional[int]:
        """
        Get bat index from serial number
        
        Args:
            serial_number: Tag serial number
            
        Returns:
            int: Bat index if found, None otherwise
        """
        for bat_index, bat_state in self.bat_states.items():
            if bat_state['serial_number'] == serial_number:
                return bat_index
        return None
    
    def is_bat_enabled(self, bat_index: int) -> bool:
        """
        Check if a bat is enabled for tracking
        
        Args:
            bat_index: Index of the bat
            
        Returns:
            bool: True if enabled, False otherwise
        """
        if bat_index in self.bat_states:
            return self.bat_states[bat_index]['enabled']
        return False
    
    def set_bat_enabled(self, bat_index: int, enabled: bool):
        """
        Enable or disable tracking for a specific bat
        
        Args:
            bat_index: Index of the bat
            enabled: True to enable, False to disable
        """
        if bat_index in self.bat_states:
            self.bat_states[bat_index]['enabled'] = enabled
            print(f"Bat {bat_index} tracking {'enabled' if enabled else 'disabled'}")
    
    def get_closest_bat_to_feeder(self, feeder_position: tuple) -> Optional[int]:
        """
        Find the closest enabled bat to a feeder position
        
        Args:
            feeder_position: (x, y, z) position of the feeder
            
        Returns:
            int: Bat index of closest bat, None if no enabled bats found
        """
        closest_bat = None
        min_distance = float('inf')
        
        fx, fy, fz = feeder_position
        
        for bat_index, bat_state in self.bat_states.items():
            if not bat_state['enabled'] or not bat_state['last_position']:
                continue
            
            pos = bat_state['last_position']
            
            # Calculate 3D distance
            distance = ((pos.x - fx) ** 2 + (pos.y - fy) ** 2 + (pos.z - fz) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_bat = bat_index
        
        return closest_bat
    
    def get_bat_states(self) -> Dict[int, Dict]:
        """
        Get current state of all bats
        
        Returns:
            dict: Dictionary of bat states
        """
        return self.bat_states.copy()
    
    def get_bat_position(self, bat_index: int) -> Optional[Position]:
        """
        Get the last known position of a specific bat
        
        Args:
            bat_index: Index of the bat
            
        Returns:
            Position: Last known position, None if not available
        """
        if bat_index in self.bat_states:
            return self.bat_states[bat_index]['last_position']
        return None