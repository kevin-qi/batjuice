"""
Thread-safe flight data manager for sharing position data between displays.
"""
import threading
import math
from collections import defaultdict, deque
from typing import Dict, Optional


class FlightDataManager:
    """Thread-safe manager for flight trajectory data shared between 2D and 3D displays"""

    def __init__(self, max_points: int = 10000):
        """
        Initialize flight data manager

        Args:
            max_points: Maximum number of points to store per bat
        """
        self.max_points = max_points

        # Thread-safe flight data storage
        self.flight_data = defaultdict(lambda: {
            'x': deque(maxlen=max_points),
            'y': deque(maxlen=max_points),
            'z': deque(maxlen=max_points),
            'timestamps': deque(maxlen=max_points)
        })

        # Thread safety
        self.lock = threading.Lock()

        # Point counters for downsampling
        self._point_counters = {}
        self.display_subsample_rate = 10  # Show every 10th point (100Hz → 10Hz)
        
        # Stationary point cleanup
        self.last_cleanup_time = {}  # bat_id -> last cleanup time
        self.cleanup_interval = 5.0  # Clean up every 5 seconds  # Show every 10th point (100Hz → 10Hz)

    def add_position(self, bat_id: str, position):
        """
        Add a position with 10x downsampling (thread-safe)

        Args:
            bat_id: Bat identifier
            position: Position object with x, y, z, timestamp attributes
        """
        import time as time_module
        
        # Skip NaN positions
        if any(math.isnan(val) for val in [position.x, position.y, position.z]):
            return

        # Initialize counter for this bat if needed
        if bat_id not in self._point_counters:
            self._point_counters[bat_id] = 0
            self.last_cleanup_time[bat_id] = time_module.time()

        self._point_counters[bat_id] += 1

        # Add every position (downsampling now handled by GUI update rate)
        if True:  # Always add - rate limiting done by caller
            with self.lock:
                self.flight_data[bat_id]['x'].append(position.x)
                self.flight_data[bat_id]['y'].append(position.y)
                self.flight_data[bat_id]['z'].append(position.z)
                self.flight_data[bat_id]['timestamps'].append(position.timestamp)

            # Diagnostic logs removed for clean console output
            
            # Periodic cleanup of stationary points
            current_time = time_module.time()
            if current_time - self.last_cleanup_time[bat_id] > self.cleanup_interval:
                self._cleanup_stationary_points(bat_id)
                self.last_cleanup_time[bat_id] = current_time

    def _cleanup_stationary_points(self, bat_id: str):
        """
        Remove stationary points (< 30cm movement over 2 seconds) for a bat
        
        Args:
            bat_id: Bat identifier
        """
        import time as time_module
        
        with self.lock:
            data = self.flight_data[bat_id]
            
            if len(data['x']) < 200:  # Need enough points to analyze
                return
            
            x_data = list(data['x'])
            y_data = list(data['y'])
            z_data = list(data['z'])
            timestamps = list(data['timestamps'])
            
            # Find stationary sequences - remove if average displacement < 30cm over 2 seconds
            keep_indices = []
            for i in range(len(x_data)):
                # Always keep first and last points
                if i == 0 or i == len(x_data) - 1:
                    keep_indices.append(i)
                    continue
                
                # Calculate average displacement over 2-second window
                current_time = timestamps[i]
                window_start_time = current_time - 2.0  # 2 seconds
                
                # Find all points within the 2-second window
                window_points = []
                for j in range(i - 1, -1, -1):
                    if timestamps[j] < window_start_time:
                        break
                    window_points.append(j)
                
                # Calculate average displacement from points in window
                if len(window_points) > 0:
                    total_displacement = 0
                    for j in window_points:
                        dx = x_data[i] - x_data[j]
                        dy = y_data[i] - y_data[j]
                        dz = z_data[i] - z_data[j]
                        displacement = math.sqrt(dx*dx + dy*dy + dz*dz)
                        total_displacement += displacement
                    
                    avg_displacement = total_displacement / len(window_points)
                    
                    # Keep point if average displacement > 30cm (0.3m)
                    if avg_displacement > 0.3:
                        keep_indices.append(i)
                    # Otherwise skip this point (it's stationary)
                else:
                    # No window points, keep the point
                    keep_indices.append(i)
            
            # Apply cleanup if any points were removed
            if len(keep_indices) < len(x_data):
                filtered_x = [x_data[i] for i in keep_indices]
                filtered_y = [y_data[i] for i in keep_indices]
                filtered_z = [z_data[i] for i in keep_indices]
                filtered_timestamps = [timestamps[i] for i in keep_indices]
                
                # Replace data
                data['x'].clear()
                data['y'].clear()
                data['z'].clear()
                data['timestamps'].clear()
                
                data['x'].extend(filtered_x)
                data['y'].extend(filtered_y)
                data['z'].extend(filtered_z)
                data['timestamps'].extend(filtered_timestamps)

    def get_snapshot(self) -> Dict:
        """
        Get thread-safe snapshot copy of all flight data

        Returns:
            dict: Copy of flight data with all bat trajectories
        """
        with self.lock:
            snapshot = {}
            for bat_id, data in self.flight_data.items():
                snapshot[bat_id] = {
                    'x': list(data['x']),
                    'y': list(data['y']),
                    'z': list(data['z']),
                    'timestamps': list(data['timestamps'])
                }
            return snapshot

    def get_bat_ids(self) -> list:
        """
        Get list of bat IDs currently in the system (thread-safe)

        Returns:
            list: List of bat ID strings
        """
        with self.lock:
            return list(self.flight_data.keys())

    def clear(self):
        """Clear all flight data (thread-safe)"""
        with self.lock:
            self.flight_data.clear()
            self._point_counters.clear()

    def get_data_length(self, bat_id: str) -> int:
        """
        Get number of points for a specific bat (thread-safe)

        Args:
            bat_id: Bat identifier

        Returns:
            int: Number of points stored for this bat
        """
        with self.lock:
            if bat_id in self.flight_data:
                return len(self.flight_data[bat_id]['x'])
            return 0
