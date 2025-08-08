"""
Position processing utilities for feeder control.
"""
import math
from utils.data_structures import Position, FeederConfig

class PositionProcessor:
    """Handles position calculations for feeder control"""
    
    @staticmethod
    def calculate_distance(position: Position, feeder_config: FeederConfig) -> float:
        """
        Calculate 3D distance between bat position and feeder
        
        Args:
            position: Bat position
            feeder_config: Feeder configuration with position
            
        Returns:
            float: Distance in cm
        """
        dx = position.x - feeder_config.x_position
        dy = position.y - feeder_config.y_position
        dz = position.z - feeder_config.z_position
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    @staticmethod
    def calculate_2d_distance(position: Position, feeder_config: FeederConfig) -> float:
        """
        Calculate 2D distance (ignoring Z) between bat position and feeder
        
        Args:
            position: Bat position
            feeder_config: Feeder configuration with position
            
        Returns:
            float: Distance in cm
        """
        dx = position.x - feeder_config.x_position
        dy = position.y - feeder_config.y_position
        
        return math.sqrt(dx*dx + dy*dy)
    
    @staticmethod
    def is_position_valid(position: Position, bounds: dict = None) -> bool:
        """
        Check if position is within valid bounds
        
        Args:
            position: Position to check
            bounds: Dictionary with x_min, x_max, y_min, y_max, z_min, z_max
            
        Returns:
            bool: True if position is valid
        """
        if bounds is None:
            return True
            
        if 'x_min' in bounds and position.x < bounds['x_min']:
            return False
        if 'x_max' in bounds and position.x > bounds['x_max']:
            return False
        if 'y_min' in bounds and position.y < bounds['y_min']:
            return False
        if 'y_max' in bounds and position.y > bounds['y_max']:
            return False
        if 'z_min' in bounds and position.z < bounds['z_min']:
            return False
        if 'z_max' in bounds and position.z > bounds['z_max']:
            return False
            
        return True