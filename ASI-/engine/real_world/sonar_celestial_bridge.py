"""
Sonar-Celestial Bridge — Real World Integration
Connects celestial routes with actual sonar data for autonomous driving.
Maps spectrum engine output to real physical spaces scanned by sonar.
"""

import math
import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import logging

# Import actual sonar engine
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from lidar_sonar_engine import LidarSonarEngine, Coordinate

logger = logging.getLogger("light-asi.sonar_celestial")


@dataclass
class RealSpaceMapping:
    """Maps celestial calculations to real sonar-scanned spaces."""
    sonar_coordinate: Coordinate
    celestial_route_id: str
    spectrum_frequency: float  # Hz from spectrum engine
    physical_density: float    # Actual density from sonar
    route_confidence: float    # How well celestial matches real space
    timestamp: float = field(default_factory=time.time)
    
    
@dataclass
class AutonomousDrivingContext:
    """Context for autonomous driving decisions."""
    vehicle_position: Coordinate
    target_destination: Coordinate
    current_velocity: float  # m/s
    safe_zones: List[Coordinate]
    obstacle_zones: List[Coordinate]
    route_alternatives: List[List[Coordinate]]


class SonarCelestialBridge:
    """
    Bridges celestial route calculations with real sonar data.
    Ensures spectrum engine works with actual physical spaces for autonomous driving.
    """
    
    def __init__(self, sonar_engine: LidarSonarEngine):
        self.sonar_engine = sonar_engine
        
        # Real-world mapping state
        self.real_space_mappings: List[RealSpaceMapping] = []
        self.active_routes: Dict[str, List[Coordinate]] = {}
        self.spectrum_to_space_map: Dict[float, List[Coordinate]] = {}
        
        # Autonomous driving state
        self.current_driving_context: Optional[AutonomousDrivingContext] = None
        self.safe_navigation_zones: List[Coordinate] = []
        self.real_time_obstacles: List[Coordinate] = []
        
        # Spectrum engine integration
        self.base_frequency = 432.0  # Hz from MSFB model
        self.frequency_ranges = {
            "safe_navigation": (400.0, 450.0),
            "obstacle_detection": (450.0, 500.0),
            "route_planning": (500.0, 550.0),
            "emergency_response": (550.0, 600.0)
        }
        
        # Real-world calibration
        self.sonar_to_spectrum_calibration = 1.0
        self.celestial_accuracy_threshold = 0.85
        
    def scan_and_map_real_space(self, scan_region: Tuple[float, float, float, float],
                                grid_resolution: float = 1.0) -> List[RealSpaceMapping]:
        """
        Scan real space with sonar and map to celestial route calculations.
        Returns mappings between physical sonar data and spectrum frequencies.
        """
        x_min, x_max, y_min, y_max = scan_region
        
        real_mappings = []
        
        # Generate scan grid based on sonar capabilities
        x_steps = int((x_max - x_min) / grid_resolution)
        y_steps = int((y_max - y_min) / grid_resolution)
        
        logger.info(f"Scanning real space: {x_steps}x{y_steps} grid points")
        
        for i in range(x_steps + 1):
            for j in range(y_steps + 1):
                x = x_min + i * grid_resolution
                y = y_min + j * grid_resolution
                
                # Create coordinate for sonar scanning
                scan_coord = Coordinate(
                    x_left=x - 0.5,
                    x_right=x + 0.5,
                    y=y,
                    z=0.0
                )
                
                # Get actual sonar density at this point
                physical_density = self.sonar_engine._get_density_at_point(x, y)
                
                # Calculate corresponding celestial route
                celestial_route_id = self._calculate_celestial_route_id(scan_coord, physical_density)
                
                # Map to spectrum frequency based on physical properties
                spectrum_freq = self._map_physical_to_spectrum(physical_density, scan_coord)
                
                # Calculate confidence of celestial-to-real mapping
                route_confidence = self._calculate_route_confidence(
                    scan_coord, physical_density, spectrum_freq
                )
                
                # Only keep high-confidence mappings for autonomous driving
                if route_confidence >= self.celestial_accuracy_threshold:
                    mapping = RealSpaceMapping(
                        sonar_coordinate=scan_coord,
                        celestial_route_id=celestial_route_id,
                        spectrum_frequency=spectrum_freq,
                        physical_density=physical_density,
                        route_confidence=route_confidence
                    )
                    
                    real_mappings.append(mapping)
                    self.real_space_mappings.append(mapping)
        
        # Update spectrum-to-space mapping for fast lookup
        self._update_spectrum_space_mapping(real_mappings)
        
        logger.info(f"Created {len(real_mappings)} high-confidence real-space mappings")
        return real_mappings
    
    def _calculate_celestial_route_id(self, coord: Coordinate, density: float) -> str:
        """Calculate celestial route ID based on coordinate and physical density."""
        # Use coordinate hash + density for unique route identification
        coord_hash = hash(f"{coord.x_center:.2f}_{coord.y:.2f}_{density:.3f}")
        return f"route_{coord_hash % 1000000:06d}"
    
    def _map_physical_to_spectrum(self, density: float, coord: Coordinate) -> float:
        """Map physical sonar density to spectrum frequency for celestial routes."""
        
        # Base frequency from spectrum engine
        base_freq = self.base_frequency
        
        # Modulate frequency based on physical density
        # Higher density = higher frequency for obstacle detection
        density_factor = 1.0 + (density * 0.5)  # 0.5-1.5 range
        
        # Add spatial component based on coordinate
        spatial_component = math.sin(coord.x_center * 0.1) * math.cos(coord.y * 0.1)
        spatial_factor = 1.0 + (spatial_component * 0.1)  # Small modulation
        
        # Calculate final spectrum frequency
        spectrum_freq = base_freq * density_factor * spatial_factor
        
        # Ensure frequency stays in valid range for autonomous driving
        spectrum_freq = max(400.0, min(600.0, spectrum_freq))
        
        return spectrum_freq
    
    def _calculate_route_confidence(self, coord: Coordinate, density: float, 
                                   spectrum_freq: float) -> float:
        """Calculate confidence that celestial route matches real space."""
        
        # Check if frequency is in expected range for this density
        expected_freq_min = self.base_frequency * (1.0 + density * 0.4)
        expected_freq_max = self.base_frequency * (1.0 + density * 0.6)
        
        freq_match = 0.0
        if expected_freq_min <= spectrum_freq <= expected_freq_max:
            freq_match = 1.0
        else:
            # Gradual falloff for frequencies outside expected range
            freq_distance = min(
                abs(spectrum_freq - expected_freq_min),
                abs(spectrum_freq - expected_freq_max)
            )
            freq_match = max(0.0, 1.0 - (freq_distance / 50.0))
        
        # Check coordinate stability (less variation = higher confidence)
        coord_stability = 1.0 / (1.0 + abs(coord.x_delta))
        
        # Check density reasonableness for autonomous driving
        density_validity = 1.0 if 0.0 <= density <= 1.0 else max(0.0, 1.0 - abs(density - 0.5))
        
        # Overall confidence
        confidence = (freq_match * 0.5) + (coord_stability * 0.3) + (density_validity * 0.2)
        
        return max(0.0, min(1.0, confidence))
    
    def _update_spectrum_space_mapping(self, mappings: List[RealSpaceMapping]):
        """Update spectrum-to-space mapping for fast autonomous driving queries."""
        
        # Clear old mappings
        self.spectrum_to_space_map.clear()
        
        # Group coordinates by spectrum frequency ranges
        for mapping in mappings:
            freq_bucket = int(mapping.spectrum_frequency / 10.0) * 10.0  # 10Hz buckets
            
            if freq_bucket not in self.spectrum_to_space_map:
                self.spectrum_to_space_map[freq_bucket] = []
                
            self.spectrum_to_space_map[freq_bucket].append(mapping.sonar_coordinate)
    
    def plan_autonomous_route(self, start: Coordinate, destination: Coordinate,
                             vehicle_constraints: Dict[str, float]) -> List[Coordinate]:
        """
        Plan autonomous driving route using real sonar data and celestial calculations.
        Returns waypoint coordinates for safe autonomous navigation.
        """
        
        # Update driving context
        self.current_driving_context = AutonomousDrivingContext(
            vehicle_position=start,
            target_destination=destination,
            current_velocity=vehicle_constraints.get("max_velocity", 15.0),
            safe_zones=[],
            obstacle_zones=[],
            route_alternatives=[]
        )
        
        # Find safe navigation frequencies
        safe_frequencies = self._find_safe_navigation_frequencies(start, destination)
        
        # Get coordinates corresponding to safe frequencies
        safe_waypoints = []
        for freq in safe_frequencies:
            coords = self._get_coordinates_for_frequency(freq)
            safe_waypoints.extend(coords)
        
        # Filter waypoints that form a viable path
        route_waypoints = self._filter_viable_path(start, destination, safe_waypoints)
        
        # Validate route with real sonar data
        validated_route = self._validate_route_with_sonar(route_waypoints)
        
        # Store route for real-time updates
        route_id = f"route_{int(time.time())}"
        self.active_routes[route_id] = validated_route
        
        logger.info(f"Planned autonomous route with {len(validated_route)} waypoints")
        return validated_route
    
    def _find_safe_navigation_frequencies(self, start: Coordinate, 
                                         destination: Coordinate) -> List[float]:
        """Find spectrum frequencies corresponding to safe navigation zones."""
        
        safe_freqs = []
        
        # Scan between start and destination
        direction_vector = (
            destination.x_center - start.x_center,
            destination.y - start.y
        )
        
        distance = math.sqrt(direction_vector[0]**2 + direction_vector[1]**2)
        
        # Sample points along the route
        num_samples = max(10, int(distance / 2.0))  # Every 2 meters
        
        for i in range(num_samples + 1):
            t = i / num_samples if num_samples > 0 else 0
            
            sample_x = start.x_center + direction_vector[0] * t
            sample_y = start.y + direction_vector[1] * t
            
            # Check density at sample point
            density = self.sonar_engine._get_density_at_point(sample_x, sample_y)
            
            # Only include low-density (safe) areas
            if density <= 0.3:  # Safe density threshold for autonomous driving
                freq = self._map_physical_to_spectrum(density, Coordinate(sample_x, sample_x, sample_y, 0.0))
                
                # Check if frequency is in safe navigation range
                safe_range = self.frequency_ranges["safe_navigation"]
                if safe_range[0] <= freq <= safe_range[1]:
                    safe_freqs.append(freq)
        
        return safe_freqs
    
    def _get_coordinates_for_frequency(self, target_freq: float) -> List[Coordinate]:
        """Get real coordinates that correspond to a spectrum frequency."""
        
        coords = []
        
        # Find frequency bucket
        freq_bucket = int(target_freq / 10.0) * 10.0
        
        # Check exact match first
        if freq_bucket in self.spectrum_to_space_map:
            coords.extend(self.spectrum_to_space_map[freq_bucket])
        
        # Check nearby buckets for more options
        for offset in [-10.0, 10.0]:
            nearby_bucket = freq_bucket + offset
            if nearby_bucket in self.spectrum_to_space_map:
                coords.extend(self.spectrum_to_space_map[nearby_bucket])
        
        return coords
    
    def _filter_viable_path(self, start: Coordinate, destination: Coordinate,
                           waypoints: List[Coordinate]) -> List[Coordinate]:
        """Filter waypoints to create a viable path for autonomous driving."""
        
        if not waypoints:
            return [start, destination]
        
        # Sort waypoints by distance from start
        sorted_waypoints = sorted(
            waypoints,
            key=lambda wp: math.sqrt(
                (wp.x_center - start.x_center)**2 + (wp.y - start.y)**2
            )
        )
        
        # Build path using nearest neighbor approach
        path = [start]
        current = start
        remaining = sorted_waypoints.copy()
        
        while remaining and len(path) < 50:  # Limit path complexity
            # Find nearest safe waypoint
            nearest = min(
                remaining,
                key=lambda wp: math.sqrt(
                    (wp.x_center - current.x_center)**2 + (wp.y - current.y)**2
                )
            )
            
            # Check if waypoint brings us closer to destination
            current_dist_to_dest = math.sqrt(
                (destination.x_center - current.x_center)**2 + (destination.y - current.y)**2
            )
            
            waypoint_dist_to_dest = math.sqrt(
                (destination.x_center - nearest.x_center)**2 + (destination.y - nearest.y)**2
            )
            
            # Only add waypoint if it gets us closer (or we're stuck)
            if waypoint_dist_to_dest < current_dist_to_dest or len(path) == 1:
                path.append(nearest)
                current = nearest
                remaining.remove(nearest)
            else:
                remaining.remove(nearest)
        
        # Always end at destination
        path.append(destination)
        
        return path
    
    def _validate_route_with_sonar(self, route: List[Coordinate]) -> List[Coordinate]:
        """Validate route waypoints with real-time sonar data."""
        
        validated = []
        
        for waypoint in route:
            # Check current density at waypoint
            current_density = self.sonar_engine._get_density_at_point(
                waypoint.x_center, waypoint.y
            )
            
            # Only keep waypoints in safe zones
            if current_density <= 0.4:  # Safety threshold
                validated.append(waypoint)
            else:
                # Try to find nearby safe alternative
                alternative = self._find_safe_alternative(waypoint, radius=3.0)
                if alternative:
                    validated.append(alternative)
        
        return validated
    
    def _find_safe_alternative(self, unsafe_waypoint: Coordinate, 
                              radius: float = 3.0) -> Optional[Coordinate]:
        """Find safe alternative near an unsafe waypoint."""
        
        # Search in expanding circles
        for r in [1.0, 2.0, 3.0]:
            if r > radius:
                break
                
            # Check 8 directions around the unsafe point
            for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
                angle_rad = math.radians(angle)
                
                alt_x = unsafe_waypoint.x_center + r * math.cos(angle_rad)
                alt_y = unsafe_waypoint.y + r * math.sin(angle_rad)
                
                density = self.sonar_engine._get_density_at_point(alt_x, alt_y)
                
                if density <= 0.3:  # Safe alternative found
                    return Coordinate(alt_x - 0.5, alt_x + 0.5, alt_y, 0.0)
        
        return None  # No safe alternative found
    
    def real_time_obstacle_detection(self) -> List[Coordinate]:
        """
        Real-time obstacle detection using sonar data and spectrum analysis.
        Returns coordinates of detected obstacles for immediate avoidance.
        """
        
        if not self.current_driving_context:
            return []
        
        current_pos = self.current_driving_context.vehicle_position
        
        # Define detection perimeter around vehicle
        detection_radius = 10.0  # meters
        detection_resolution = 0.5  # 0.5m grid
        
        obstacles = []
        
        # Scan around current vehicle position
        for x_offset in np.arange(-detection_radius, detection_radius + detection_resolution, detection_resolution):
            for y_offset in np.arange(-detection_radius, detection_radius + detection_resolution, detection_resolution):
                
                scan_x = current_pos.x_center + x_offset
                scan_y = current_pos.y + y_offset
                
                # Get real-time density
                density = self.sonar_engine._get_density_at_point(scan_x, scan_y)
                
                # Obstacle threshold for autonomous driving
                if density > 0.6:  # High density = obstacle
                    obstacle_coord = Coordinate(scan_x, scan_x, scan_y, 0.0)
                    obstacles.append(obstacle_coord)
        
        # Update real-time obstacle list
        self.real_time_obstacles = obstacles
        
        # Update driving context
        if self.current_driving_context:
            self.current_driving_context.obstacle_zones = obstacles
        
        return obstacles
    
    def update_route_real_time(self, route_id: str) -> List[Coordinate]:
        """
        Update active route based on real-time sonar data.
        Adjusts route to avoid newly detected obstacles.
        """
        
        if route_id not in self.active_routes:
            return []
        
        current_route = self.active_routes[route_id]
        
        # Detect current obstacles
        current_obstacles = self.real_time_obstacle_detection()
        
        # Check if route needs updating
        route_blocked = self._check_route_blocked(current_route, current_obstacles)
        
        if not route_blocked:
            return current_route  # Route is still safe
        
        # Re-plan route avoiding new obstacles
        if self.current_driving_context:
            start = self.current_driving_context.vehicle_position
            destination = self.current_driving_context.target_destination
            
            # Re-plan with updated obstacle awareness
            updated_route = self.plan_autonomous_route(
                start, destination, {"max_velocity": 15.0}
            )
            
            # Update stored route
            self.active_routes[route_id] = updated_route
            
            logger.info(f"Updated route {route_id} to avoid {len(current_obstacles)} obstacles")
            return updated_route
        
        return current_route
    
    def _check_route_blocked(self, route: List[Coordinate], 
                            obstacles: List[Coordinate]) -> bool:
        """Check if any obstacles block the current route."""
        
        obstacle_threshold = 2.0  # meters - minimum clearance needed
        
        for waypoint in route:
            for obstacle in obstacles:
                distance = math.sqrt(
                    (waypoint.x_center - obstacle.x_center)**2 +
                    (waypoint.y - obstacle.y)**2
                )
                
                if distance < obstacle_threshold:
                    return True  # Route is blocked
        
        return False  # Route is clear
    
    def render_to_actual_map(self, map_bounds: Tuple[float, float, float, float],
                            resolution: float = 0.5) -> Dict[str, Any]:
        """
        Render celestial routes and spectrum data onto actual map coordinates.
        Creates a real-world map suitable for autonomous driving visualization.
        """
        
        x_min, x_max, y_min, y_max = map_bounds
        
        # Create map grid
        x_steps = int((x_max - x_min) / resolution)
        y_steps = int((y_max - y_min) / resolution)
        
        map_data = {
            "bounds": map_bounds,
            "resolution": resolution,
            "grid_size": (x_steps, y_steps),
            "safe_zones": [],
            "obstacle_zones": [],
            "celestial_routes": [],
            "spectrum_overlay": [],
            "real_time_data": {
                "timestamp": time.time(),
                "vehicle_position": None,
                "active_obstacles": self.real_time_obstacles
            }
        }
        
        # Fill map grid with real sonar data
        for i in range(x_steps + 1):
            for j in range(y_steps + 1):
                x = x_min + i * resolution
                y = y_min + j * resolution
                
                # Get actual density from sonar
                density = self.sonar_engine._get_density_at_point(x, y)
                
                # Classify zones for autonomous driving
                coord = Coordinate(x - 0.5, x + 0.5, y, 0.0)
                
                if density <= 0.3:
                    map_data["safe_zones"].append({
                        "coordinate": coord,
                        "density": density,
                        "classification": "safe_navigation"
                    })
                elif density > 0.6:
                    map_data["obstacle_zones"].append({
                        "coordinate": coord,
                        "density": density,
                        "classification": "obstacle"
                    })
        
        # Add celestial route overlays
        for mapping in self.real_space_mappings:
            if mapping.route_confidence >= 0.7:  # Only high-confidence routes
                map_data["celestial_routes"].append({
                    "route_id": mapping.celestial_route_id,
                    "coordinate": mapping.sonar_coordinate,
                    "spectrum_frequency": mapping.spectrum_frequency,
                    "confidence": mapping.route_confidence
                })
        
        # Add spectrum frequency overlay
        for freq_bucket, coordinates in self.spectrum_to_space_map.items():
            for coord in coordinates:
                map_data["spectrum_overlay"].append({
                    "coordinate": coord,
                    "frequency": freq_bucket,
                    "frequency_range": self._get_frequency_range_classification(freq_bucket)
                })
        
        # Add current driving context if available
        if self.current_driving_context:
            map_data["real_time_data"]["vehicle_position"] = self.current_driving_context.vehicle_position
            map_data["real_time_data"]["target_destination"] = self.current_driving_context.target_destination
        
        logger.info(f"Rendered map: {len(map_data['safe_zones'])} safe zones, {len(map_data['obstacle_zones'])} obstacles")
        return map_data
    
    def _get_frequency_range_classification(self, frequency: float) -> str:
        """Classify frequency into driving-relevant categories."""
        
        for category, (min_freq, max_freq) in self.frequency_ranges.items():
            if min_freq <= frequency <= max_freq:
                return category
        
        return "unclassified"
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """Get current status of sonar-celestial bridge."""
        
        return {
            "real_space_mappings": len(self.real_space_mappings),
            "active_routes": len(self.active_routes),
            "spectrum_frequency_buckets": len(self.spectrum_to_space_map),
            "current_obstacles": len(self.real_time_obstacles),
            "driving_context_active": self.current_driving_context is not None,
            "calibration": {
                "sonar_to_spectrum": self.sonar_to_spectrum_calibration,
                "accuracy_threshold": self.celestial_accuracy_threshold
            },
            "frequency_ranges": self.frequency_ranges
        }
    
    def calibrate_spectrum_engine(self, reference_points: List[Tuple[Coordinate, float]]):
        """
        Calibrate spectrum engine against known real-world reference points.
        Improves accuracy of celestial route mapping to actual spaces.
        """
        
        calibration_errors = []
        
        for coord, expected_freq in reference_points:
            # Get actual density at reference point
            actual_density = self.sonar_engine._get_density_at_point(coord.x_center, coord.y)
            
            # Calculate what spectrum frequency we would predict
            predicted_freq = self._map_physical_to_spectrum(actual_density, coord)
            
            # Calculate error
            error = abs(predicted_freq - expected_freq) / expected_freq
            calibration_errors.append(error)
        
        # Calculate average calibration error
        avg_error = sum(calibration_errors) / len(calibration_errors) if calibration_errors else 0.0
        
        # Update calibration factor
        if avg_error > 0.05:  # 5% error threshold
            adjustment = 1.0 - (avg_error * 0.5)  # Conservative adjustment
            self.sonar_to_spectrum_calibration *= adjustment
            
            logger.info(f"Calibrated spectrum engine: {avg_error:.1%} error, adjustment factor: {adjustment:.3f}")
        
        return {
            "calibration_points": len(reference_points),
            "average_error": avg_error,
            "calibration_factor": self.sonar_to_spectrum_calibration,
            "errors": calibration_errors
        }