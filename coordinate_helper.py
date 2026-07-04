"""
Coordinate Helper for Real-World Integration
Provides utilities for creating coordinates compatible with the lidar engine.
"""

from lidar_sonar_engine import Coordinate


def create_coord(x: float, y: float, z: float = 0.0, width: float = 1.0) -> Coordinate:
    """
    Create a coordinate with proper x_left/x_right from center point.
    
    Args:
        x: Center X coordinate
        y: Y coordinate  
        z: Z coordinate (default 0.0)
        width: Width of coordinate span (default 1.0m)
    
    Returns:
        Coordinate object compatible with lidar engine
    """
    half_width = width / 2.0
    return Coordinate(
        x_left=x - half_width,
        x_right=x + half_width,
        y=y,
        z=z
    )


def coord_from_center(x_center: float, y: float, z: float = 0.0) -> Coordinate:
    """Create coordinate from center point (convenience function)."""
    return create_coord(x_center, y, z)


def waypoint_coord(x: float, y: float) -> Coordinate:
    """Create a waypoint coordinate for autonomous driving."""
    return create_coord(x, y, 0.0, 0.5)  # 0.5m width for waypoints