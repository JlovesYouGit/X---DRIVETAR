"""
Spectrum Real-World Engine — ASI Integration for Autonomous Driving
Converts spectrum engine calculations to work with actual sonar-scanned spaces.
Forces rendering onto actual maps for real autonomous driving use cases.
"""

import math
import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import logging

# Import real-world components
from .sonar_celestial_bridge import SonarCelestialBridge, RealSpaceMapping
from lidar_sonar_engine import LidarSonarEngine, Coordinate

logger = logging.getLogger("light-asi.spectrum_real_world")


@dataclass
class SpectrumMapPoint:
    """Point on spectrum map with real-world coordinates."""
    coordinate: Coordinate
    spectrum_frequency: float
    physical_density: float
    navigation_safety: str  # "safe", "caution", "obstacle", "emergency"
    confidence_score: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class RealWorldRenderData:
    """Rendered map data for autonomous driving systems."""
    map_bounds: Tuple[float, float, float, float]
    resolution: float
    grid_data: np.ndarray  # 2D array of navigation values
    safe_paths: List[List[Coordinate]]
    obstacle_zones: List[Tuple[Coordinate, float]]  # (center, radius)
    spectrum_overlay: Dict[float, List[Coordinate]]
    metadata: Dict[str, Any]


class SpectrumRealWorldEngine:
    """
    Integrates spectrum engine with real-world sonar data for autonomous driving.
    Ensures spectrum calculations match actual physical spaces being scanned.
    """
    
    def __init__(self, sonar_engine: LidarSonarEngine):
        self.sonar_engine = sonar_engine
        self.sonar_bridge = SonarCelestialBridge(sonar_engine)
        
        # Real-world spectrum mapping
        self.spectrum_map_points: List[SpectrumMapPoint] = []
        self.real_world_grid: Optional[np.ndarray] = None
        self.grid_bounds: Optional[Tuple[float, float, float, float]] = None
        self.grid_resolution: float = 0.5  # meters per grid cell
        
        # MSFB spectrum parameters adapted for real world
        self.base_frequency = 432.0  # Hz - MSFB base
        self.frequency_scale = 1.0
        self.navigation_frequency_ranges = {
            "safe_navigation": (400.0, 450.0),      # Low density areas
            "caution_zone": (450.0, 500.0),        # Medium density
            "obstacle_detection": (500.0, 550.0),   # High density areas
            "emergency_stop": (550.0, 600.0)       # Critical obstacles
        }
        
        # Real-time state
        self.current_vehicle_position: Optional[Coordinate] = None
        self.active_scan_region: Optional[Tuple[float, float, float, float]] = None
        self.last_full_scan: float = 0.0
        
        # Performance optimization
        self.scan_cache: Dict[str, SpectrumMapPoint] = {}
        self.cache_expiry = 30.0  # seconds
        
    def initialize_real_world_mapping(self, scan_bounds: Tuple[float, float, float, float],
                                     resolution: float = 0.5) -> Dict[str, Any]:
        """
        Initialize real-world mapping by scanning the environment.
        Creates spectrum-to-space mapping for autonomous driving.
        """
        
        logger.info(f"Initializing real-world spectrum mapping: bounds {scan_bounds}, resolution {resolution}m")
        
        self.grid_bounds = scan_bounds
        self.grid_resolution = resolution
        self.active_scan_region = scan_bounds
        
        # Perform initial scan and mapping
        real_mappings = self.sonar_bridge.scan_and_map_real_space(scan_bounds, resolution)
        
        # Convert to spectrum map points
        spectrum_points = []
        for mapping in real_mappings:
            
            # Classify navigation safety based on density
            nav_safety = self._classify_navigation_safety(mapping.physical_density)
            
            spectrum_point = SpectrumMapPoint(
                coordinate=mapping.sonar_coordinate,
                spectrum_frequency=mapping.spectrum_frequency,
                physical_density=mapping.physical_density,
                navigation_safety=nav_safety,
                confidence_score=mapping.route_confidence
            )
            
            spectrum_points.append(spectrum_point)
        
        self.spectrum_map_points = spectrum_points
        
        # Create navigation grid
        self._create_navigation_grid()
        
        self.last_full_scan = time.time()
        
        return {
            "mapping_points": len(spectrum_points),
            "grid_size": self.real_world_grid.shape if self.real_world_grid is not None else None,
            "scan_bounds": scan_bounds,
            "resolution": resolution,
            "safety_distribution": self._calculate_safety_distribution()
        }
    
    def _classify_navigation_safety(self, density: float) -> str:
        """Classify navigation safety based on physical density."""
        
        if density <= 0.2:
            return "safe"
        elif density <= 0.4:
            return "caution"
        elif density <= 0.7:
            return "obstacle"
        else:
            return "emergency"
    
    def _create_navigation_grid(self):
        """Create 2D navigation grid from spectrum map points."""
        
        if not self.grid_bounds:
            return
            
        x_min, x_max, y_min, y_max = self.grid_bounds
        
        # Calculate grid dimensions
        x_cells = int((x_max - x_min) / self.grid_resolution)
        y_cells = int((y_max - y_min) / self.grid_resolution)
        
        # Initialize grid with unknown values (-1)
        self.real_world_grid = np.full((y_cells, x_cells), -1.0, dtype=float)
        
        # Fill grid with spectrum map data
        for point in self.spectrum_map_points:
            
            # Convert coordinate to grid indices
            x_idx = int((point.coordinate.x_center - x_min) / self.grid_resolution)
            y_idx = int((point.coordinate.y - y_min) / self.grid_resolution)
            
            # Ensure indices are within bounds
            if 0 <= x_idx < x_cells and 0 <= y_idx < y_cells:
                
                # Assign navigation value based on safety
                if point.navigation_safety == "safe":
                    nav_value = 1.0
                elif point.navigation_safety == "caution":
                    nav_value = 0.5
                elif point.navigation_safety == "obstacle":
                    nav_value = 0.1
                else:  # emergency
                    nav_value = 0.0
                
                # Weight by confidence
                final_value = nav_value * point.confidence_score
                
                self.real_world_grid[y_idx, x_idx] = final_value
        
        logger.info(f"Created navigation grid: {x_cells}x{y_cells} cells")
    
    def _calculate_safety_distribution(self) -> Dict[str, int]:
        """Calculate distribution of safety classifications."""
        
        distribution = {"safe": 0, "caution": 0, "obstacle": 0, "emergency": 0}
        
        for point in self.spectrum_map_points:
            distribution[point.navigation_safety] += 1
            
        return distribution
    
    def update_vehicle_position(self, position: Coordinate):
        """Update current vehicle position for real-time calculations."""
        self.current_vehicle_position = position
        
        # Clear nearby cache entries that may be outdated
        self._invalidate_nearby_cache(position, radius=10.0)
    
    def _invalidate_nearby_cache(self, position: Coordinate, radius: float):
        """Invalidate cache entries near the given position."""
        
        keys_to_remove = []
        
        for cache_key in self.scan_cache:
            # Extract coordinates from cache key
            parts = cache_key.split("_")
            if len(parts) >= 2:
                try:
                    cached_x = float(parts[0])
                    cached_y = float(parts[1])
                    
                    distance = math.sqrt(
                        (cached_x - position.x_center)**2 + 
                        (cached_y - position.y)**2
                    )
                    
                    if distance <= radius:
                        keys_to_remove.append(cache_key)
                        
                except ValueError:
                    continue
        
        for key in keys_to_remove:
            del self.scan_cache[key]
    
    def get_real_time_spectrum_data(self, query_coordinate: Coordinate,
                                   scan_radius: float = 5.0) -> Dict[str, Any]:
        """
        Get real-time spectrum data for a coordinate using actual sonar scanning.
        Returns navigation-relevant spectrum information.
        """
        
        # Check cache first
        cache_key = f"{query_coordinate.x_center:.1f}_{query_coordinate.y:.1f}"
        current_time = time.time()
        
        if cache_key in self.scan_cache:
            cached_point = self.scan_cache[cache_key]
            if current_time - cached_point.timestamp < self.cache_expiry:
                return self._format_spectrum_response(cached_point)
        
        # Perform real-time sonar scan
        current_density = self.sonar_engine._get_density_at_point(
            query_coordinate.x_center, query_coordinate.y
        )
        
        # Map to spectrum frequency using calibrated mapping
        spectrum_freq = self.sonar_bridge._map_physical_to_spectrum(
            current_density, query_coordinate
        )
        
        # Classify safety
        nav_safety = self._classify_navigation_safety(current_density)
        
        # Calculate confidence based on scan quality
        confidence = self._calculate_scan_confidence(query_coordinate, current_density)
        
        # Create spectrum map point
        spectrum_point = SpectrumMapPoint(
            coordinate=query_coordinate,
            spectrum_frequency=spectrum_freq,
            physical_density=current_density,
            navigation_safety=nav_safety,
            confidence_score=confidence
        )
        
        # Cache result
        self.scan_cache[cache_key] = spectrum_point
        
        return self._format_spectrum_response(spectrum_point)
    
    def _calculate_scan_confidence(self, coordinate: Coordinate, density: float) -> float:
        """Calculate confidence in scan data quality."""
        
        confidence = 1.0
        
        # Reduce confidence for edge coordinates
        if self.grid_bounds:
            x_min, x_max, y_min, y_max = self.grid_bounds
            
            # Distance from boundaries
            x_dist_from_edge = min(
                coordinate.x_center - x_min,
                x_max - coordinate.x_center
            ) / ((x_max - x_min) / 2.0)
            
            y_dist_from_edge = min(
                coordinate.y - y_min,
                y_max - coordinate.y
            ) / ((y_max - y_min) / 2.0)
            
            edge_penalty = min(x_dist_from_edge, y_dist_from_edge)
            confidence *= max(0.5, edge_penalty)  # Minimum 50% confidence
        
        # Reduce confidence for extreme densities (sensor limits)
        if density > 0.9 or density < 0.05:
            confidence *= 0.8
            
        return max(0.1, min(1.0, confidence))
    
    def _format_spectrum_response(self, spectrum_point: SpectrumMapPoint) -> Dict[str, Any]:
        """Format spectrum data for autonomous driving systems."""
        
        return {
            "coordinate": {
                "x": spectrum_point.coordinate.x_center,
                "y": spectrum_point.coordinate.y,
                "z": spectrum_point.coordinate.z
            },
            "spectrum_frequency": spectrum_point.spectrum_frequency,
            "physical_density": spectrum_point.physical_density,
            "navigation_safety": spectrum_point.navigation_safety,
            "confidence_score": spectrum_point.confidence_score,
            "frequency_classification": self._classify_frequency(spectrum_point.spectrum_frequency),
            "navigation_recommendations": self._get_navigation_recommendations(spectrum_point),
            "timestamp": spectrum_point.timestamp
        }
    
    def _classify_frequency(self, frequency: float) -> str:
        """Classify spectrum frequency for navigation purposes."""
        
        for class_name, (min_freq, max_freq) in self.navigation_frequency_ranges.items():
            if min_freq <= frequency <= max_freq:
                return class_name
                
        return "unclassified"
    
    def _get_navigation_recommendations(self, spectrum_point: SpectrumMapPoint) -> List[str]:
        """Get navigation recommendations based on spectrum data."""
        
        recommendations = []
        
        if spectrum_point.navigation_safety == "safe":
            recommendations.append("Safe for normal navigation")
            
        elif spectrum_point.navigation_safety == "caution":
            recommendations.append("Proceed with caution - reduce speed")
            recommendations.append("Increase sensor scanning frequency")
            
        elif spectrum_point.navigation_safety == "obstacle":
            recommendations.append("Obstacle detected - plan alternative route")
            recommendations.append("Minimum safe distance: 2.0m")
            
        else:  # emergency
            recommendations.append("EMERGENCY - Immediate stop required")
            recommendations.append("Critical obstacle - do not proceed")
        
        # Confidence-based recommendations
        if spectrum_point.confidence_score < 0.7:
            recommendations.append("Low confidence data - verify with additional sensors")
            
        return recommendations
    
    def render_autonomous_driving_map(self, map_bounds: Optional[Tuple[float, float, float, float]] = None,
                                     include_predictions: bool = True) -> RealWorldRenderData:
        """
        Render complete map for autonomous driving systems.
        Includes real sonar data, spectrum overlays, and navigation paths.
        """
        
        bounds = map_bounds or self.grid_bounds
        if not bounds:
            raise ValueError("No map bounds available - run initialize_real_world_mapping first")
        
        logger.info("Rendering autonomous driving map with real-world data")
        
        # Get current sonar-based map data
        sonar_map = self.sonar_bridge.render_to_actual_map(bounds, self.grid_resolution)
        
        # Extract safe paths from spectrum data
        safe_paths = self._extract_safe_paths(bounds)
        
        # Create obstacle zones
        obstacle_zones = self._create_obstacle_zones()
        
        # Build spectrum frequency overlay
        spectrum_overlay = self._build_spectrum_overlay()
        
        # Create final grid data for autonomous systems
        if self.real_world_grid is not None:
            grid_data = self.real_world_grid.copy()
        else:
            x_cells = int((bounds[1] - bounds[0]) / self.grid_resolution)
            y_cells = int((bounds[3] - bounds[2]) / self.grid_resolution)
            grid_data = np.zeros((y_cells, x_cells))
        
        # Add real-time vehicle position if available
        metadata = {
            "render_timestamp": time.time(),
            "data_sources": ["sonar", "spectrum", "celestial"],
            "vehicle_position": self.current_vehicle_position,
            "scan_quality": self._assess_scan_quality(),
            "navigation_summary": self._create_navigation_summary()
        }
        
        if include_predictions and self.current_vehicle_position:
            metadata["predicted_paths"] = self._predict_navigation_paths(
                self.current_vehicle_position, bounds
            )
        
        return RealWorldRenderData(
            map_bounds=bounds,
            resolution=self.grid_resolution,
            grid_data=grid_data,
            safe_paths=safe_paths,
            obstacle_zones=obstacle_zones,
            spectrum_overlay=spectrum_overlay,
            metadata=metadata
        )
    
    def _extract_safe_paths(self, bounds: Tuple[float, float, float, float]) -> List[List[Coordinate]]:
        """Extract safe navigation paths from spectrum map data."""
        
        safe_paths = []
        
        # Group safe coordinates by connectivity
        safe_coords = [
            point.coordinate for point in self.spectrum_map_points 
            if point.navigation_safety == "safe" and point.confidence_score >= 0.7
        ]
        
        if len(safe_coords) < 2:
            return safe_paths
        
        # Simple path extraction using nearest neighbor clustering
        remaining_coords = safe_coords.copy()
        
        while len(remaining_coords) > 1:
            path = [remaining_coords.pop(0)]  # Start new path
            current_coord = path[0]
            
            # Build path by connecting nearby safe coordinates
            while remaining_coords:
                # Find nearest remaining coordinate
                nearest = min(
                    remaining_coords,
                    key=lambda coord: math.sqrt(
                        (coord.x_center - current_coord.x_center)**2 + 
                        (coord.y - current_coord.y)**2
                    )
                )
                
                # Check if close enough to connect (within 3 meters)
                distance = math.sqrt(
                    (nearest.x_center - current_coord.x_center)**2 + 
                    (nearest.y - current_coord.y)**2
                )
                
                if distance <= 3.0:
                    path.append(nearest)
                    remaining_coords.remove(nearest)
                    current_coord = nearest
                else:
                    break  # End this path
            
            # Only keep paths with multiple waypoints
            if len(path) >= 3:
                safe_paths.append(path)
        
        return safe_paths
    
    def _create_obstacle_zones(self) -> List[Tuple[Coordinate, float]]:
        """Create obstacle zones for autonomous driving avoidance."""
        
        obstacle_zones = []
        
        # Find high-density areas that represent obstacles
        obstacle_coords = [
            point.coordinate for point in self.spectrum_map_points
            if point.navigation_safety in ["obstacle", "emergency"]
        ]
        
        # Cluster nearby obstacle coordinates
        processed = set()
        
        for coord in obstacle_coords:
            coord_key = f"{coord.x_center:.1f}_{coord.y:.1f}"
            if coord_key in processed:
                continue
                
            # Find nearby obstacles to form a zone
            zone_coords = [coord]
            
            for other_coord in obstacle_coords:
                other_key = f"{other_coord.x_center:.1f}_{other_coord.y:.1f}"
                if other_key in processed:
                    continue
                    
                distance = math.sqrt(
                    (other_coord.x_center - coord.x_center)**2 + 
                    (other_coord.y - coord.y)**2
                )
                
                if distance <= 2.0:  # Group obstacles within 2 meters
                    zone_coords.append(other_coord)
                    processed.add(other_key)
            
            # Create obstacle zone with center and radius
            if zone_coords:
                # Calculate zone center
                center_x = sum(c.x_center for c in zone_coords) / len(zone_coords)
                center_y = sum(c.y for c in zone_coords) / len(zone_coords)
                center_coord = Coordinate(center_x, center_x, center_y, 0.0)
                
                # Calculate zone radius (max distance from center + safety margin)
                max_dist = max(
                    math.sqrt((c.x_center - center_x)**2 + (c.y - center_y)**2)
                    for c in zone_coords
                )
                radius = max_dist + 1.5  # 1.5m safety margin
                
                obstacle_zones.append((center_coord, radius))
                processed.add(coord_key)
        
        return obstacle_zones
    
    def _build_spectrum_overlay(self) -> Dict[float, List[Coordinate]]:
        """Build spectrum frequency overlay for visualization."""
        
        overlay = {}
        
        # Group coordinates by frequency ranges
        for point in self.spectrum_map_points:
            
            # Round frequency to 10Hz buckets for grouping
            freq_bucket = round(point.spectrum_frequency / 10.0) * 10.0
            
            if freq_bucket not in overlay:
                overlay[freq_bucket] = []
                
            overlay[freq_bucket].append(point.coordinate)
        
        return overlay
    
    def _assess_scan_quality(self) -> Dict[str, float]:
        """Assess overall quality of scan data."""
        
        if not self.spectrum_map_points:
            return {"overall": 0.0, "coverage": 0.0, "confidence": 0.0}
        
        # Calculate average confidence
        avg_confidence = sum(p.confidence_score for p in self.spectrum_map_points) / len(self.spectrum_map_points)
        
        # Calculate coverage (how much of scan area has data)
        coverage = 1.0  # Assume full coverage for now
        if self.grid_bounds and self.real_world_grid is not None:
            total_cells = self.real_world_grid.size
            filled_cells = np.count_nonzero(self.real_world_grid >= 0)
            coverage = filled_cells / total_cells if total_cells > 0 else 0.0
        
        overall_quality = (avg_confidence * 0.7) + (coverage * 0.3)
        
        return {
            "overall": overall_quality,
            "coverage": coverage,
            "confidence": avg_confidence,
            "data_points": len(self.spectrum_map_points)
        }
    
    def _create_navigation_summary(self) -> Dict[str, Any]:
        """Create navigation summary for autonomous driving systems."""
        
        safety_counts = {"safe": 0, "caution": 0, "obstacle": 0, "emergency": 0}
        
        for point in self.spectrum_map_points:
            safety_counts[point.navigation_safety] += 1
        
        total_points = len(self.spectrum_map_points)
        
        return {
            "total_scan_points": total_points,
            "safety_distribution": safety_counts,
            "safe_percentage": (safety_counts["safe"] / total_points * 100) if total_points > 0 else 0,
            "navigable_percentage": ((safety_counts["safe"] + safety_counts["caution"]) / total_points * 100) if total_points > 0 else 0,
            "critical_obstacles": safety_counts["emergency"],
            "last_scan_time": self.last_full_scan
        }
    
    def _predict_navigation_paths(self, vehicle_pos: Coordinate, 
                                 bounds: Tuple[float, float, float, float]) -> List[List[Coordinate]]:
        """Predict optimal navigation paths from current vehicle position."""
        
        # Simple prediction: find safe paths leading away from vehicle position
        predicted_paths = []
        
        # Get nearby safe coordinates
        nearby_safe = []
        for point in self.spectrum_map_points:
            if point.navigation_safety == "safe":
                distance = math.sqrt(
                    (point.coordinate.x_center - vehicle_pos.x_center)**2 + 
                    (point.coordinate.y - vehicle_pos.y)**2
                )
                if distance <= 20.0:  # Within 20 meters
                    nearby_safe.append(point.coordinate)
        
        # Create paths in different directions
        directions = [0, 45, 90, 135, 180, 225, 270, 315]  # 8 directions
        
        for angle in directions:
            path = self._build_directional_path(vehicle_pos, angle, nearby_safe)
            if len(path) >= 3:  # Minimum path length
                predicted_paths.append(path)
        
        return predicted_paths
    
    def _build_directional_path(self, start: Coordinate, angle_degrees: float,
                               available_coords: List[Coordinate]) -> List[Coordinate]:
        """Build a path in a specific direction using available safe coordinates."""
        
        angle_rad = math.radians(angle_degrees)
        direction_x = math.cos(angle_rad)
        direction_y = math.sin(angle_rad)
        
        path = [start]
        current = start
        
        # Build path up to 15 meters in the given direction
        for step in range(1, 16):  # 1-meter steps
            
            target_x = start.x_center + direction_x * step
            target_y = start.y + direction_y * step
            
            # Find nearest available coordinate to target
            nearest = None
            min_distance = float('inf')
            
            for coord in available_coords:
                distance = math.sqrt(
                    (coord.x_center - target_x)**2 + 
                    (coord.y - target_y)**2
                )
                
                if distance < min_distance and distance <= 2.0:  # Within 2 meters
                    min_distance = distance
                    nearest = coord
            
            if nearest:
                path.append(nearest)
                current = nearest
                # Remove from available to avoid reuse
                available_coords = [c for c in available_coords if c != nearest]
            else:
                break  # No more safe coordinates in this direction
        
        return path
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get current engine status and performance metrics."""
        
        return {
            "initialized": self.grid_bounds is not None,
            "map_bounds": self.grid_bounds,
            "grid_resolution": self.grid_resolution,
            "spectrum_points": len(self.spectrum_map_points),
            "cache_entries": len(self.scan_cache),
            "vehicle_position": self.current_vehicle_position,
            "last_full_scan": self.last_full_scan,
            "scan_quality": self._assess_scan_quality(),
            "frequency_ranges": self.navigation_frequency_ranges,
            "base_frequency": self.base_frequency
        }