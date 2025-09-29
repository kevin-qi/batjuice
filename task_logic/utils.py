"""
Task Logic Utilities - Helper functions for scientists
"""
import math
from typing import Optional


def calculate_distance(pos1: tuple[float, float, float], pos2: tuple[float, float, float]) -> float:
    """Calculate 3D Euclidean distance between two positions"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    dz = pos1[2] - pos2[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def calculate_2d_distance(pos1: tuple[float, float, float], pos2: tuple[float, float, float]) -> float:
    """Calculate 2D distance (ignoring z coordinate)"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return math.sqrt(dx*dx + dy*dy)


def is_within_radius(bat_pos: tuple[float, float, float], 
                    feeder_pos: tuple[float, float, float], 
                    radius: float, 
                    use_2d: bool = False) -> bool:
    """Check if bat is within radius of feeder"""
    if use_2d:
        distance = calculate_2d_distance(bat_pos, feeder_pos)
    else:
        distance = calculate_distance(bat_pos, feeder_pos)
    return distance <= radius


def format_position(pos: tuple[float, float, float], precision: int = 2) -> str:
    """Format position for display"""
    return f"({pos[0]:.{precision}f}, {pos[1]:.{precision}f}, {pos[2]:.{precision}f})"


def time_since_str(seconds: Optional[float]) -> str:
    """Convert seconds to human readable time string"""
    if seconds is None:
        return "never"
    
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"