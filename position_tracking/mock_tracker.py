"""
Mock tracker that streams experimental data from flight_positions.npy.
Provides realistic bat flight data for testing and development.
"""
import time
import threading
import numpy as np
from typing import Callable, Optional, Dict, Any
from utils.data_structures import Position


class MockTracker:
    """Mock tracker that streams real experimental data from flight_positions.npy at correct frame rate"""
    
    def __init__(self, config: Dict[str, Any], callback: Optional[Callable[[Position], None]] = None):
        """
        Initialize mock tracker
        
        Args:
            config: Mock configuration with data file path and bat settings
            callback: Function to call when new position data is available
        """
        self.position_callback = callback
        self.connected = False
        self.running = False
        self.stream_thread: Optional[threading.Thread] = None
        
        # Get RTLS mock config
        rtls_config = config.get("mock_rtls", {})
        
        # Load real experimental data
        self.flight_data = None
        self.bat_configs = []
        self.current_indices = []
        self.frame_rate = 120  # Default, will be updated based on RTLS backend
        
        self._load_flight_data(rtls_config)
        self._setup_bats(rtls_config)
    
    def _load_flight_data(self, rtls_config: Dict[str, Any]):
        """Load real experimental data from numpy file"""
        try:
            data_file = rtls_config.get("data_file", "data/flight_positions.npy")
            self.flight_data = np.load(data_file)
            print(f"Loaded real flight data: {self.flight_data.shape} positions")
            
            # Validate data format
            if len(self.flight_data.shape) != 2 or self.flight_data.shape[1] != 3:
                raise ValueError(f"Expected flight data shape (N, 3), got {self.flight_data.shape}")
                
        except Exception as e:
            print(f"Error loading flight data: {e}")
            raise Exception(f"Could not load experimental data: {e}")
    
    def _setup_bats(self, rtls_config: Dict[str, Any]):
        """Setup bat configurations for streaming"""
        bat_count = rtls_config.get("bat_count", 2)
        bat_ids = rtls_config.get("bat_ids", [f"Bat_{i+1:03d}" for i in range(bat_count)])
        tag_ids = rtls_config.get("tag_ids", list(range(1, bat_count + 1)))
        
        self.bat_configs = []
        self.current_indices = []
        
        for i in range(bat_count):
            bat_id = bat_ids[i] if i < len(bat_ids) else f"Bat_{i+1:03d}"
            tag_id = tag_ids[i] if i < len(tag_ids) else i + 1
            
            # For multiple bats: First bat uses original data, others use time-shifted versions
            if i == 0:
                positions = self.flight_data.copy()
            else:
                # Time-shift for other bats (different starting points in the trajectory)
                shift = (i * len(self.flight_data) // bat_count) % len(self.flight_data)
                positions = np.roll(self.flight_data, shift, axis=0)
            
            self.bat_configs.append({
                'bat_id': bat_id,
                'tag_id': tag_id,
                'positions': positions,
                'total_frames': len(positions)
            })
            self.current_indices.append(0)
        
        print(f"Setup {len(self.bat_configs)} bats for real data streaming")
    
    def set_frame_rate(self, rtls_backend: str):
        """Set frame rate based on RTLS backend"""
        if rtls_backend == "cortex":
            self.frame_rate = 120
        elif rtls_backend == "ciholas":
            self.frame_rate = 100
        else:
            self.frame_rate = 100  # Default
        
        print(f"Real data tracker frame rate set to {self.frame_rate} Hz for {rtls_backend}")
        
    def connect(self) -> bool:
        """Connect to data stream"""
        if len(self.bat_configs) == 0:
            print("No bat configurations available")
            return False
        
        self.connected = True
        print(f"Real data tracker connected with {len(self.bat_configs)} bats")
        return True
    
    def disconnect(self):
        """Disconnect from data stream"""
        self.stop_reading()
        self.connected = False
        print("Real data tracker disconnected")
    
    def start_reading(self):
        """Start streaming real experimental data"""
        if not self.connected or self.running:
            return
        
        self.running = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        print(f"Started streaming real data at {self.frame_rate} Hz")
    
    def stop_reading(self):
        """Stop streaming data"""
        self.running = False
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=1.0)
        print("Stopped streaming real data")
    
    def start_tracking(self):
        """Alias for start_reading to match expected interface"""
        self.start_reading()
    
    def stop_tracking(self):
        """Alias for stop_reading to match expected interface"""
        self.stop_reading()
    
    def _stream_loop(self):
        """Main streaming loop - stream the experimental data"""
        frame_interval = 1.0 / self.frame_rate
        
        print("Mock tracker started")
        
        while self.running:
            start_time = time.time()
            
            try:
                # Stream data for each bat
                for bat_idx, bat_config in enumerate(self.bat_configs):
                    current_index = self.current_indices[bat_idx]
                    
                    if current_index >= bat_config['total_frames']:
                        # Reset to beginning (loop the data)
                        self.current_indices[bat_idx] = 0
                        current_index = 0
                    
                    # Get current position (real experimental data, no modifications)
                    pos = bat_config['positions'][current_index]
                    
                    # Skip NaN positions
                    if np.isnan(pos).any():
                        # Advance to next frame and continue
                        self.current_indices[bat_idx] += 1
                        continue
                    
                    # Create position object
                    position = Position(
                        bat_id=bat_config['bat_id'],
                        tag_id=bat_config['tag_id'],
                        x=float(pos[0]),
                        y=float(pos[1]),
                        z=float(pos[2]),
                        timestamp=time.time()
                    )
                    
                    # Send to callback
                    if self.position_callback:
                        self.position_callback(position)
                    
                    # Advance to next frame
                    self.current_indices[bat_idx] += 1
                
                # Maintain frame rate
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                import traceback
                print(f"Error in mock tracker streaming in {__file__}:")
                print(f"Error: {e}")
                traceback.print_exc()
                time.sleep(0.1)
        
        print("Mock tracker stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current streaming status"""
        if not self.connected:
            return {"status": "disconnected"}
        
        total_frames = [bat['total_frames'] for bat in self.bat_configs]
        current_progress = [idx / total for idx, total in zip(self.current_indices, total_frames)]
        
        return {
            "status": "streaming" if self.running else "connected",
            "bats": len(self.bat_configs),
            "frame_rate": self.frame_rate,
            "progress": current_progress,
            "data_shape": self.flight_data.shape if self.flight_data is not None else None
        }