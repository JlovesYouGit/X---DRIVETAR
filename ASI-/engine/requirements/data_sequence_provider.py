"""
Data Sequence Provider — Light-ASI LLM Gateway
Provides missing data sequences that pipeline architectures require for activation.
Generates the specific data types that each system component needs.
"""

import time
import math
import random
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np

# Import coordinate system
try:
    from lidar_sonar_engine import Coordinate
except ImportError:
    Coordinate = None

logger = logging.getLogger("light-asi.data_sequence")


class SequenceType(Enum):
    """Types of data sequences that can be provided."""
    HASH_SEQUENCES = "hash_sequences"
    NODE_METADATA = "node_metadata" 
    ROUTING_TABLE = "routing_table"
    COORDINATE_DATA = "coordinate_data"
    DENSITY_MAPPINGS = "density_mappings"
    SONAR_SCAN_DATA = "sonar_scan_data"
    SPECTRUM_FREQUENCIES = "spectrum_frequencies"
    ROUTE_COORDINATES = "route_coordinates"
    PATH_COORDINATES = "path_coordinates"
    SEQUENCE_METADATA = "sequence_metadata"


@dataclass
class DataSequence:
    """Generated data sequence for system components."""
    sequence_type: SequenceType
    data: Any
    size: int
    generation_time: float
    metadata: Dict[str, Any]

class DataSequenceProvider:
    """
    Provides missing data sequences for pipeline architectures.
    Generates the specific data patterns that ASI components require.
    """
    
    def __init__(self):
        self.generated_sequences: Dict[str, DataSequence] = {}
        self.generation_stats = {
            "total_generated": 0,
            "sequences_by_type": {},
            "last_generation": 0.0
        }
        
        # Sequence generation parameters
        self.default_sizes = {
            SequenceType.HASH_SEQUENCES: 100,
            SequenceType.NODE_METADATA: 50,
            SequenceType.ROUTING_TABLE: 25,
            SequenceType.COORDINATE_DATA: 75,
            SequenceType.DENSITY_MAPPINGS: 60,
            SequenceType.SONAR_SCAN_DATA: 200,
            SequenceType.SPECTRUM_FREQUENCIES: 150,
            SequenceType.ROUTE_COORDINATES: 30,
            SequenceType.PATH_COORDINATES: 20,
            SequenceType.SEQUENCE_METADATA: 40
        }
    
    def provide_sequence(self, sequence_type: SequenceType, 
                        size: Optional[int] = None,
                        custom_params: Optional[Dict[str, Any]] = None) -> DataSequence:
        """
        Provide a data sequence of the specified type.
        Auto-generates the data pattern that components need.
        """
        
        if size is None:
            size = self.default_sizes.get(sequence_type, 50)
        
        params = custom_params or {}
        
        # Generate appropriate data based on sequence type
        if sequence_type == SequenceType.HASH_SEQUENCES:
            data = self._generate_hash_sequences(size, params)
        elif sequence_type == SequenceType.NODE_METADATA:
            data = self._generate_node_metadata(size, params)
        elif sequence_type == SequenceType.ROUTING_TABLE:
            data = self._generate_routing_table(size, params)
        elif sequence_type == SequenceType.COORDINATE_DATA:
            data = self._generate_coordinate_data(size, params)
        elif sequence_type == SequenceType.DENSITY_MAPPINGS:
            data = self._generate_density_mappings(size, params)
        elif sequence_type == SequenceType.SONAR_SCAN_DATA:
            data = self._generate_sonar_scan_data(size, params)
        elif sequence_type == SequenceType.SPECTRUM_FREQUENCIES:
            data = self._generate_spectrum_frequencies(size, params)
        elif sequence_type == SequenceType.ROUTE_COORDINATES:
            data = self._generate_route_coordinates(size, params)
        elif sequence_type == SequenceType.PATH_COORDINATES:
            data = self._generate_path_coordinates(size, params)
        elif sequence_type == SequenceType.SEQUENCE_METADATA:
            data = self._generate_sequence_metadata(size, params)
        else:
            raise ValueError(f"Unknown sequence type: {sequence_type}")
        
        # Create data sequence object
        sequence = DataSequence(
            sequence_type=sequence_type,
            data=data,
            size=len(data) if isinstance(data, (list, dict)) else size,
            generation_time=time.time(),
            metadata={
                "generation_params": params,
                "provider_version": "1.0",
                "architecture_compatible": True
            }
        )
        
        # Store and update stats
        sequence_id = f"{sequence_type.value}_{int(time.time())}"
        self.generated_sequences[sequence_id] = sequence
        
        self.generation_stats["total_generated"] += 1
        self.generation_stats["sequences_by_type"][sequence_type.value] = \
            self.generation_stats["sequences_by_type"].get(sequence_type.value, 0) + 1
        self.generation_stats["last_generation"] = time.time()
        
        logger.info(f"Generated {sequence_type.value} sequence: {sequence.size} items")
        
        return sequence
    
    def _generate_hash_sequences(self, size: int, params: Dict[str, Any]) -> List[str]:
        """Generate hash sequences for node graph routing."""
        
        sequences = []
        base_string = params.get("base_string", "ASI_NODE_")
        
        for i in range(size):
            # Create hash-compatible strings for routing
            node_string = f"{base_string}{i:06d}"
            import hashlib
            hash_val = hashlib.sha256(node_string.encode()).hexdigest()[:16]
            sequences.append(hash_val)
        
        return sequences
    
    def _generate_node_metadata(self, size: int, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate node metadata for graph operations."""
        
        metadata_list = []
        base_resonance = params.get("base_resonance", 5**15)  # RESONANCE_BASE
        
        for i in range(size):
            metadata = {
                "node_id": i,
                "position": i,
                "hash_hex": f"node_{i:08x}",
                "virtual_ip_tier": random.choice([10, 100, 1000, 10000]),
                "resonance_weight": base_resonance * random.uniform(0.8, 1.2),
                "range_min": -16,
                "range_max": 10000,
                "anchor": "0x2c8151dbb2574d1393b484c8815188ac81c71c4603dd7876bd4a77e",
                "active": True,
                "last_update": time.time()
            }
            metadata_list.append(metadata)
        
        return metadata_list
    
    def _generate_routing_table(self, size: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate routing table for consistent hash routing."""
        
        routing_table = {
            "virtual_nodes": {},
            "hash_ring": [],
            "node_assignments": {},
            "replication_factor": params.get("replication_factor", 3)
        }
        
        # Generate virtual node mappings
        for i in range(size):
            node_id = f"node_{i:04d}"
            hash_val = hash(node_id) % (2**32)  # 32-bit hash space
            
            routing_table["virtual_nodes"][node_id] = {
                "hash_value": hash_val,
                "ip_tier": random.choice([10, 100, 1000]),
                "load_factor": random.uniform(0.1, 1.0),
                "status": "active"
            }
            
            routing_table["hash_ring"].append(hash_val)
        
        # Sort hash ring
        routing_table["hash_ring"].sort()
        
        return routing_table
    
    def _generate_coordinate_data(self, size: int, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate coordinate data for spatial mapping."""
        
        coordinates = []
        bounds = params.get("bounds", (-50.0, 50.0, -50.0, 50.0))
        x_min, x_max, y_min, y_max = bounds
        
        for i in range(size):
            x = random.uniform(x_min, x_max)
            y = random.uniform(y_min, y_max)
            z = random.uniform(-10.0, 10.0)
            
            coord_data = {
                "x_center": x,
                "x_left": x - 0.5,
                "x_right": x + 0.5,
                "y": y,
                "z": z,
                "timestamp": time.time(),
                "coord_id": f"coord_{i:06d}",
                "density": random.uniform(0.0, 1.0),
                "navigation_safe": random.choice([True, True, True, False])  # 75% safe
            }
            coordinates.append(coord_data)
        
        return coordinates
    
    def _generate_density_mappings(self, size: int, params: Dict[str, Any]) -> Dict[str, float]:
        """Generate density mappings for spatial analysis."""
        
        density_map = {}
        resolution = params.get("resolution", 1.0)
        
        for i in range(size):
            x = (i % 10) * resolution  # 10x grid
            y = (i // 10) * resolution
            
            coord_key = f"{x:.1f}_{y:.1f}"
            
            # Generate realistic density patterns
            distance_from_center = math.sqrt(x**2 + y**2)
            base_density = max(0.0, 0.8 - (distance_from_center * 0.1))
            noise = random.uniform(-0.2, 0.2)
            
            density_map[coord_key] = max(0.0, min(1.0, base_density + noise))
        
        return density_map
    
    def _generate_sonar_scan_data(self, size: int, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sonar scan data for real-world integration."""
        
        scan_data = []
        scan_range = params.get("range", 50.0)  # meters
        
        for i in range(size):
            angle = (i / size) * 360.0  # Full 360° scan
            distance = random.uniform(1.0, scan_range)
            
            # Convert to cartesian
            x = distance * math.cos(math.radians(angle))
            y = distance * math.sin(math.radians(angle))
            
            scan_point = {
                "angle": angle,
                "distance": distance,
                "x": x,
                "y": y,
                "intensity": random.uniform(0.1, 1.0),
                "confidence": random.uniform(0.7, 0.99),
                "timestamp": time.time() + (i * 0.001),  # Sequential timing
                "scan_id": i
            }
            scan_data.append(scan_point)
        
        return scan_data
    
    def _generate_spectrum_frequencies(self, size: int, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate spectrum frequencies for celestial routing."""
        
        frequencies = []
        base_freq = params.get("base_frequency", 432.0)  # MSFB base frequency
        
        frequency_ranges = {
            "safe_navigation": (400.0, 450.0),
            "caution_zone": (450.0, 500.0), 
            "obstacle_detection": (500.0, 550.0),
            "emergency_stop": (550.0, 600.0)
        }
        
        for i in range(size):
            # Choose frequency range based on distribution
            range_choice = random.choices(
                list(frequency_ranges.keys()),
                weights=[0.4, 0.3, 0.2, 0.1],  # More safe frequencies
                k=1
            )[0]
            
            freq_min, freq_max = frequency_ranges[range_choice]
            frequency = random.uniform(freq_min, freq_max)
            
            freq_data = {
                "frequency": frequency,
                "classification": range_choice,
                "amplitude": random.uniform(0.5, 1.0),
                "phase": random.uniform(0, 2 * math.pi),
                "confidence": random.uniform(0.8, 0.99),
                "coord_x": random.uniform(-25.0, 25.0),
                "coord_y": random.uniform(-25.0, 25.0),
                "spectrum_id": f"spec_{i:06d}"
            }
            frequencies.append(freq_data)
        
        return frequencies
    
    def _generate_route_coordinates(self, size: int, params: Dict[str, Any]) -> List[List[Dict[str, float]]]:
        """Generate route coordinates for navigation."""
        
        routes = []
        num_routes = params.get("num_routes", max(1, size // 10))
        
        for route_idx in range(num_routes):
            # Generate a route with waypoints
            waypoints_per_route = max(3, size // num_routes)
            
            # Start and end points
            start_x = random.uniform(-20.0, 20.0)
            start_y = random.uniform(-20.0, 20.0)
            end_x = random.uniform(-20.0, 20.0)
            end_y = random.uniform(-20.0, 20.0)
            
            route = []
            
            for wp_idx in range(waypoints_per_route):
                # Interpolate between start and end with some variation
                t = wp_idx / (waypoints_per_route - 1) if waypoints_per_route > 1 else 0
                
                x = start_x + t * (end_x - start_x) + random.uniform(-2.0, 2.0)
                y = start_y + t * (end_y - start_y) + random.uniform(-2.0, 2.0)
                
                waypoint = {
                    "x_center": x,
                    "x_left": x - 0.5,
                    "x_right": x + 0.5,
                    "y": y,
                    "z": 0.0,
                    "waypoint_id": wp_idx,
                    "route_id": route_idx
                }
                route.append(waypoint)
            
            routes.append(route)
        
        return routes
    
    def _generate_path_coordinates(self, size: int, params: Dict[str, Any]) -> List[Dict[str, float]]:
        """Generate path coordinates for virtual sequences."""
        
        path_coords = []
        path_type = params.get("path_type", "autonomous_navigation")
        
        for i in range(size):
            # Generate coordinates along a smooth path
            t = i / (size - 1) if size > 1 else 0
            
            # Sinusoidal path for smooth navigation
            x = t * 40.0 - 20.0  # -20 to 20 range
            y = 10.0 * math.sin(t * math.pi * 2) + random.uniform(-1.0, 1.0)
            z = random.uniform(-0.5, 0.5)
            
            coord = {
                "x_center": x,
                "x_left": x - 0.5,
                "x_right": x + 0.5, 
                "y": y,
                "z": z,
                "path_index": i,
                "path_type": path_type,
                "curvature": abs(math.cos(t * math.pi * 4)),  # Path curvature
                "speed_limit": random.uniform(5.0, 15.0)  # m/s
            }
            path_coords.append(coord)
        
        return path_coords
    
    def _generate_sequence_metadata(self, size: int, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate sequence metadata for virtual sequences."""
        
        metadata_list = []
        
        for i in range(size):
            metadata = {
                "sequence_id": f"seq_{i:08d}",
                "sequence_type": random.choice(["navigation", "exploration", "emergency", "patrol"]),
                "priority": random.randint(1, 10),
                "created_at": time.time() - random.uniform(0, 86400),  # Last 24 hours
                "last_updated": time.time() - random.uniform(0, 3600),  # Last hour
                "active": random.choice([True, True, False]),  # 2/3 active
                "confidence_score": random.uniform(0.7, 0.99),
                "path_length": random.uniform(10.0, 100.0),  # meters
                "estimated_duration": random.uniform(30.0, 300.0),  # seconds
                "waypoint_count": random.randint(5, 50),
                "route_optimization": random.choice(["speed", "safety", "fuel", "comfort"]),
                "conditions": {
                    "weather": random.choice(["clear", "cloudy", "rain", "fog"]),
                    "traffic": random.choice(["light", "moderate", "heavy"]),
                    "road_quality": random.uniform(0.5, 1.0)
                }
            }
            metadata_list.append(metadata)
        
        return metadata_list
    
    def bulk_provide_sequences(self, sequence_needs: List[SequenceType], 
                              custom_sizes: Optional[Dict[SequenceType, int]] = None) -> Dict[SequenceType, DataSequence]:
        """Provide multiple sequences at once for efficient pipeline setup."""
        
        logger.info(f"Bulk providing {len(sequence_needs)} sequence types")
        
        bulk_results = {}
        custom_sizes = custom_sizes or {}
        
        for sequence_type in sequence_needs:
            size = custom_sizes.get(sequence_type, self.default_sizes.get(sequence_type, 50))
            
            try:
                sequence = self.provide_sequence(sequence_type, size)
                bulk_results[sequence_type] = sequence
                
            except Exception as e:
                logger.error(f"Failed to generate {sequence_type.value}: {e}")
                # Continue with other sequences
        
        logger.info(f"Bulk provision complete: {len(bulk_results)}/{len(sequence_needs)} successful")
        return bulk_results
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get current provider status and statistics."""
        
        return {
            "sequences_generated": self.generation_stats["total_generated"],
            "sequences_by_type": self.generation_stats["sequences_by_type"],
            "last_generation": self.generation_stats["last_generation"],
            "cached_sequences": len(self.generated_sequences),
            "default_sizes": {seq_type.value: size for seq_type, size in self.default_sizes.items()},
            "supported_types": [seq_type.value for seq_type in SequenceType]
        }