"""
Mock position tracker for testing and development.
"""
import time
import random
import math
from typing import Optional, Callable, Dict, Any
from .base_tracker import BaseTracker
from utils.data_structures import Position


class MockTracker(BaseTracker):
    """Mock position tracker that simulates bat movement"""
    
    def __init__(self, config: Dict[str, Any], callback: Optional[Callable[[Position], None]] = None):
        """
        Initialize mock tracker
        
        Args:
            config: Mock configuration dictionary
            callback: Function to call when new position data is received
        """
        super().__init__(callback)
        self.config = config
        self.num_bats = config.get('num_bats', 3)
        self.flight_area = config.get('flight_area', {})
        self.flight_speed = config.get('flight_speed', 50.0)  # cm/s
        
        # Initialize bat states
        self.bats = {}
        for i in range(self.num_bats):
            bat_id = f"bat_{i:02d}"
            tag_id = f"tag_{i:02d}"
            
            # Start bats in different areas of the room
            x_start = random.uniform(self.flight_area.get('x_min', -2.9), 
                                   self.flight_area.get('x_max', 2.9))
            y_start = random.uniform(self.flight_area.get('y_min', -2.6), 
                                   self.flight_area.get('y_max', 2.6))
            z_start = random.uniform(self.flight_area.get('z_min', 0.2), 
                                   self.flight_area.get('z_max', 2.5))
            
            # Start in random state for realistic behavior
            is_moving = random.choice([True, False])
            
            self.bats[bat_id] = {
                'tag_id': tag_id,
                'x': x_start,
                'y': y_start,
                'z': z_start,
                'vx': 0,
                'vy': 0,
                'vz': 0,
                'last_update': time.time(),
                'target_speed': random.uniform(1.5, 3.0),  # Faster when moving
                'is_moving': is_moving,
                'state_start_time': time.time(),
                'next_state_duration': self._get_state_duration(is_moving)
            }
            
            # Set initial velocity based on state
            if is_moving:
                self._set_moving_velocity(self.bats[bat_id])
        
        self.sampling_rate = 100  # Hz
        self.update_interval = 1.0 / self.sampling_rate
        
    def connect(self) -> bool:
        """Mock connection always succeeds"""
        print("Mock tracker connected")
        return True
    
    def disconnect(self):
        """Mock disconnection"""
        print("Mock tracker disconnected")
    
    def _fetch_data(self):
        """Generate mock position data"""
        current_time = time.time()
        
        for bat_id, bat_state in self.bats.items():
            dt = current_time - bat_state['last_update']
            
            if dt >= self.update_interval:
                # Update position based on velocity
                bat_state['x'] += bat_state['vx'] * dt
                bat_state['y'] += bat_state['vy'] * dt
                bat_state['z'] += bat_state['vz'] * dt
                
                # Update realistic behavior state
                self._update_bat_state(bat_state)
                
                # Handle movement based on state
                if bat_state['is_moving']:
                    # Bounce off boundaries
                    self._handle_boundaries(bat_state)
                    
                    # Add some randomness to velocity
                    self._update_velocity(bat_state)
                else:
                    # Stationary - slight drift only
                    drift_mag = 0.02  # 2cm drift
                    bat_state['x'] += random.uniform(-drift_mag, drift_mag)
                    bat_state['y'] += random.uniform(-drift_mag, drift_mag)
                    bat_state['z'] += random.uniform(-drift_mag, drift_mag)
                
                # Create position object
                position = Position(
                    bat_id=bat_id,
                    tag_id=bat_state['tag_id'],
                    x=bat_state['x'],
                    y=bat_state['y'],
                    z=bat_state['z'],
                    timestamp=current_time
                )
                
                self._add_position(position)
                bat_state['last_update'] = current_time
        
        time.sleep(0.001)  # Small sleep to prevent busy waiting
    
    def _get_state_duration(self, is_moving: bool) -> float:
        """Get duration for current state"""
        if is_moving:
            return random.uniform(2.0, 4.0)  # Move for 2-4 seconds
        else:
            return random.uniform(5.0, 10.0)  # Stop for 5-10 seconds
    
    def _set_moving_velocity(self, bat_state: Dict):
        """Set velocity for moving state"""
        # Random direction
        angle_xy = random.uniform(0, 2 * math.pi)
        angle_z = random.uniform(-math.pi/6, math.pi/6)  # Mostly horizontal
        
        speed = bat_state['target_speed']
        bat_state['vx'] = speed * math.cos(angle_xy) * math.cos(angle_z)
        bat_state['vy'] = speed * math.sin(angle_xy) * math.cos(angle_z)
        bat_state['vz'] = speed * math.sin(angle_z)
    
    def _update_bat_state(self, bat_state: Dict):
        """Update bat movement state (stationary vs moving)"""
        current_time = time.time()
        elapsed = current_time - bat_state['state_start_time']
        
        if elapsed >= bat_state['next_state_duration']:
            # Switch state
            bat_state['is_moving'] = not bat_state['is_moving']
            bat_state['state_start_time'] = current_time
            bat_state['next_state_duration'] = self._get_state_duration(bat_state['is_moving'])
            
            if bat_state['is_moving']:
                # Start moving
                self._set_moving_velocity(bat_state)
            else:
                # Stop moving
                bat_state['vx'] = bat_state['vy'] = bat_state['vz'] = 0
    
    def _handle_boundaries(self, bat_state: Dict[str, float]):
        """Handle boundary collisions with realistic bat behavior"""
        x_min = self.flight_area.get('x_min', -2.9)
        x_max = self.flight_area.get('x_max', 2.9)
        y_min = self.flight_area.get('y_min', -2.6)
        y_max = self.flight_area.get('y_max', 2.6)
        z_min = self.flight_area.get('z_min', 0.2)
        z_max = self.flight_area.get('z_max', 2.5)
        
        # Add small margin to avoid bats getting stuck at boundaries
        margin = 0.05  # 5 cm margin
        
        if bat_state['x'] <= x_min + margin:
            bat_state['vx'] = abs(bat_state['vx']) * 0.9  # Bounce away from wall
            bat_state['x'] = x_min + margin
            
        if bat_state['x'] >= x_max - margin:
            bat_state['vx'] = -abs(bat_state['vx']) * 0.9
            bat_state['x'] = x_max - margin
            
        if bat_state['y'] <= y_min + margin:
            bat_state['vy'] = abs(bat_state['vy']) * 0.9
            bat_state['y'] = y_min + margin
            
        if bat_state['y'] >= y_max - margin:
            bat_state['vy'] = -abs(bat_state['vy']) * 0.9
            bat_state['y'] = y_max - margin
            
        if bat_state['z'] <= z_min + margin:
            bat_state['vz'] = abs(bat_state['vz']) * 0.9
            bat_state['z'] = z_min + margin
            
        if bat_state['z'] >= z_max - margin:
            bat_state['vz'] = -abs(bat_state['vz']) * 0.9
            bat_state['z'] = z_max - margin
    
    def _update_velocity(self, bat_state: Dict[str, float]):
        """Add random changes to velocity to simulate natural bat flight patterns"""
        # Realistic bat flight characteristics
        accel_mag = 2.0  # m/s² - realistic acceleration for bats
        
        # Add some randomness to simulate natural flight variations
        bat_state['vx'] += random.uniform(-accel_mag, accel_mag) * 0.1
        bat_state['vy'] += random.uniform(-accel_mag, accel_mag) * 0.1
        bat_state['vz'] += random.uniform(-accel_mag, accel_mag) * 0.05
        
        # Bats tend to maintain certain speed ranges
        current_speed = math.sqrt(bat_state['vx']**2 + bat_state['vy']**2 + bat_state['vz']**2)
        target_speed = bat_state['target_speed']
        
        # Gradually adjust towards target speed
        if current_speed > 0:
            speed_factor = target_speed / current_speed
            # Apply gentle correction towards target speed
            correction = 0.95 + 0.1 * speed_factor
            bat_state['vx'] *= correction
            bat_state['vy'] *= correction
            bat_state['vz'] *= correction
        
        # Enforce maximum and minimum realistic speeds
        final_speed = math.sqrt(bat_state['vx']**2 + bat_state['vy']**2 + bat_state['vz']**2)
        if final_speed > 2.5:  # Max speed limit
            factor = 2.5 / final_speed
            bat_state['vx'] *= factor
            bat_state['vy'] *= factor
            bat_state['vz'] *= factor
        elif final_speed < 0.3:  # Min speed to keep moving
            factor = 0.3 / final_speed if final_speed > 0 else 1
            bat_state['vx'] *= factor
            bat_state['vy'] *= factor
            bat_state['vz'] *= factor