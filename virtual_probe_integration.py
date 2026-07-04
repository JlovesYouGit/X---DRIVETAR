"""
Virtual Probe X Integration for Spatial Hash Gate Management
Configures virtual-probe_X to manage spatial hash gates and coordinate mapping.
"""

import sys
import os
import hashlib
import json
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

# Add virtual-probe_X to path
sys.path.insert(0, str(Path(__file__).parent / "virtual-probe_X"))

try:
    from hashgate import XSpace, HashGate, OpenMirror
    from xspace_scanner import XSpaceScanner
except ImportError:
    # Fallback if virtual-probe_X modules aren't available
    XSpace = None
    XSpaceScanner = None

from lidar_sonar_engine import LidarSonarEngine, Coordinate, AnchorPoint


@dataclass
class SpatialGate:
    """Spatial hash gate for coordinate mapping."""
    gate_id: str
    coordinate: Coordinate
    spatial_hash: str
    density_level: float
    is_open: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpatialMirror:
    """Spatial mirror for coordinate reflection."""
    mirror_id: str
    source_gate_id: str
    coordinate: Coordinate
    content_hash: str
    similarity: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class VirtualProbeIntegrator:
    """
    Integrates virtual-probe_X for spatial hash gate management.
    Manages coordinate mapping through hash gates and mirrors.
    """
    
    def __init__(self, lidar_engine: LidarSonarEngine):
        self.lidar_engine = lidar_engine
        
        # Initialize XSpace if available
        if XSpace is not None:
            self.xspace = XSpace()
            self.scanner = XSpaceScanner(self.xspace)
        else:
            self.xspace = None
            self.scanner = None
        
        # Spatial gates and mirrors
        self.spatial_gates: Dict[str, SpatialGate] = {}
        self.spatial_mirrors: Dict[str, SpatialMirror] = {}
        
        # Coordinate to gate mapping
        self.coord_to_gate: Dict[str, str] = {}
        
        # Density-based gate management
        self.density_thresholds = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.2
        }
    
    def coordinate_to_spatial_hash(self, coord: Coordinate) -> str:
        """
        Convert coordinate to spatial hash for gate management.
        Uses hash-based coordination similar to virtual-probe_X.
        """
        raw = f"{coord.x_center:.8f}:{coord.y:.8f}:{coord.z:.8f}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    def create_spatial_gate(self, coord: Coordinate, density: float) -> SpatialGate:
        """
        Create spatial gate at coordinate with given density level.
        Gates represent entry points for spatial navigation.
        """
        spatial_hash = self.coordinate_to_spatial_hash(coord)
        gate_id = f"gate_{spatial_hash[:8]}"
        
        # Determine gate status based on density
        is_open = density < self.density_thresholds["high"]
        
        gate = SpatialGate(
            gate_id=gate_id,
            coordinate=coord,
            spatial_hash=spatial_hash,
            density_level=density,
            is_open=is_open,
            metadata={
                "created_at": time.time(),
                "density_category": self._get_density_category(density)
            }
        )
        
        self.spatial_gates[gate_id] = gate
        self.coord_to_gate[spatial_hash] = gate_id
        
        # Also add to XSpace if available
        if self.xspace is not None:
            self.xspace.add_gate(
                host=f"coord_{coord.x_center:.2f}",
                port=int(coord.y * 1000) % 65536,
                protocol="spatial",
                metadata={
                    "spatial_hash": spatial_hash,
                    "density": density,
                    "coordinate": {
                        "x": coord.x_center,
                        "y": coord.y,
                        "z": coord.z
                    }
                }
            )
        
        return gate
    
    def _get_density_category(self, density: float) -> str:
        """Get density category based on threshold."""
        if density >= self.density_thresholds["high"]:
            return "high"
        elif density >= self.density_thresholds["medium"]:
            return "medium"
        else:
            return "low"
    
    def create_spatial_mirror(self, source_gate: SpatialGate, 
                             coord: Coordinate) -> SpatialMirror:
        """
        Create spatial mirror reflecting coordinate from source gate.
        Mirrors represent alternative paths or reflections.
        """
        content_hash = self.coordinate_to_spatial_hash(coord)
        mirror_id = f"mirror_{content_hash[:8]}"
        
        # Calculate similarity to source
        similarity = self._calculate_spatial_similarity(
            source_gate.coordinate, coord
        )
        
        mirror = SpatialMirror(
            mirror_id=mirror_id,
            source_gate_id=source_gate.gate_id,
            coordinate=coord,
            content_hash=content_hash,
            similarity=similarity,
            metadata={
                "created_at": time.time(),
                "distance": self._calculate_distance(source_gate.coordinate, coord)
            }
        )
        
        self.spatial_mirrors[mirror_id] = mirror
        
        # Also add to XSpace if available
        if self.xspace is not None:
            self.xspace.add_mirror(
                host=f"coord_{coord.x_center:.2f}",
                port=int(coord.y * 1000) % 65536,
                source_gate_id=source_gate.gate_id,
                content_hash=content_hash,
                metadata={
                    "coordinate": {
                        "x": coord.x_center,
                        "y": coord.y,
                        "z": coord.z
                    },
                    "similarity": similarity
                }
            )
        
        return mirror
    
    def _calculate_spatial_similarity(self, coord1: Coordinate, 
                                     coord2: Coordinate) -> float:
        """Calculate spatial similarity between two coordinates."""
        distance = self._calculate_distance(coord1, coord2)
        max_distance = self.lidar_engine.sensor_range
        similarity = 1.0 - (distance / max_distance)
        return max(0.0, min(1.0, similarity))
    
    def _calculate_distance(self, coord1: Coordinate, coord2: Coordinate) -> float:
        """Calculate Euclidean distance between coordinates."""
        return math.sqrt(
            (coord1.x_center - coord2.x_center)**2 +
            (coord1.y - coord2.y)**2 +
            (coord1.z - coord2.z)**2
        )
    
    def map_anchors_to_gates(self, anchors: Dict[str, AnchorPoint]) -> Dict[str, SpatialGate]:
        """
        Map lidar anchor points to spatial gates.
        Creates gates at heat concentration points.
        """
        gate_mapping = {}
        
        for anchor_id, anchor in anchors.items():
            # Get density at anchor point
            density = self.lidar_engine._get_density_at_point(
                anchor.coordinate.x_center,
                anchor.coordinate.y
            )
            
            # Create spatial gate
            gate = self.create_spatial_gate(anchor.coordinate, density)
            gate_mapping[anchor_id] = gate
        
        return gate_mapping
    
    def find_open_gates(self, region: Tuple[float, float, float, float]) -> List[SpatialGate]:
        """
        Find all open gates within specified region.
        Region: (x_min, x_max, y_min, y_max)
        """
        x_min, x_max, y_min, y_max = region
        
        open_gates = [
            gate for gate in self.spatial_gates.values()
            if (gate.is_open and
                x_min <= gate.coordinate.x_center <= x_max and
                y_min <= gate.coordinate.y <= y_max)
        ]
        
        # Sort by density (lower density = better path)
        open_gates.sort(key=lambda g: g.density_level)
        
        return open_gates
    
    def find_mirrors_by_similarity(self, content_hash: str, 
                                   threshold: float = 0.8) -> List[SpatialMirror]:
        """
        Find mirrors with content hash similarity above threshold.
        Similar to virtual-probe_X retrieve functionality.
        """
        matching_mirrors = []
        
        for mirror in self.spatial_mirrors.values():
            # Calculate hash similarity
            similarity = self._hash_similarity(mirror.content_hash, content_hash)
            
            if similarity >= threshold:
                matching_mirrors.append(mirror)
        
        # Sort by similarity
        matching_mirrors.sort(key=lambda m: m.similarity, reverse=True)
        
        return matching_mirrors
    
    def _hash_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two hashes."""
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return 0.0
        
        matches = sum(1 for a, b in zip(hash1, hash2) if a == b)
        return matches / len(hash1)
    
    def scan_spatial_region(self, region: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """
        Scan spatial region for gates and mirrors.
        Similar to virtual-probe_X scan functionality.
        """
        x_min, x_max, y_min, y_max = region
        
        # Find gates in region
        region_gates = [
            gate for gate in self.spatial_gates.values()
            if (x_min <= gate.coordinate.x_center <= x_max and
                y_min <= gate.coordinate.y <= y_max)
        ]
        
        # Find mirrors in region
        region_mirrors = [
            mirror for mirror in self.spatial_mirrors.values()
            if (x_min <= mirror.coordinate.x_center <= x_max and
                y_min <= mirror.coordinate.y <= y_max)
        ]
        
        return {
            "region": region,
            "gates_found": len(region_gates),
            "mirrors_found": len(region_mirrors),
            "gates": [
                {
                    "id": g.gate_id,
                    "coordinate": {
                        "x": g.coordinate.x_center,
                        "y": g.coordinate.y,
                        "z": g.coordinate.z
                    },
                    "density": g.density_level,
                    "is_open": g.is_open
                }
                for g in region_gates
            ],
            "mirrors": [
                {
                    "id": m.mirror_id,
                    "source_gate": m.source_gate_id,
                    "coordinate": {
                        "x": m.coordinate.x_center,
                        "y": m.coordinate.y,
                        "z": m.coordinate.z
                    },
                    "similarity": m.similarity
                }
                for m in region_mirrors
            ]
        }
    
    def get_spatial_graph(self) -> Dict[str, Any]:
        """
        Get spatial graph showing gates, mirrors, and connections.
        Similar to virtual-probe_X XSpace graph.
        """
        edges = []
        
        # Create edges from gates to their mirrors
        for mirror in self.spatial_mirrors.values():
            edges.append({
                "source": mirror.source_gate_id,
                "target": mirror.mirror_id,
                "type": "mirror",
                "similarity": mirror.similarity
            })
        
        return {
            "gates": [
                {
                    "id": g.gate_id,
                    "spatial_hash": g.spatial_hash,
                    "coordinate": {
                        "x": g.coordinate.x_center,
                        "y": g.coordinate.y,
                        "z": g.coordinate.z
                    },
                    "density": g.density_level,
                    "is_open": g.is_open
                }
                for g in self.spatial_gates.values()
            ],
            "mirrors": [
                {
                    "id": m.mirror_id,
                    "source_gate_id": m.source_gate_id,
                    "content_hash": m.content_hash,
                    "coordinate": {
                        "x": m.coordinate.x_center,
                        "y": m.coordinate.y,
                        "z": m.coordinate.z
                    },
                    "similarity": m.similarity
                }
                for m in self.spatial_mirrors.values()
            ],
            "edges": edges,
            "stats": {
                "total_gates": len(self.spatial_gates),
                "open_gates": sum(1 for g in self.spatial_gates.values() if g.is_open),
                "total_mirrors": len(self.spatial_mirrors),
                "total_edges": len(edges)
            }
        }
    
    def optimize_path_through_gates(self, start: Coordinate, 
                                    end: Coordinate) -> List[Coordinate]:
        """
        Optimize path by routing through open gates.
        Uses spatial gates to find optimal navigation path.
        """
        # Find gates near start and end
        start_region = (
            start.x_center - 10, start.x_center + 10,
            start.y - 10, start.y + 10
        )
        end_region = (
            end.x_center - 10, end.x_center + 10,
            end.y - 10, end.y + 10
        )
        
        start_gates = self.find_open_gates(start_region)
        end_gates = self.find_open_gates(end_region)
        
        if not start_gates or not end_gates:
            # No gates available, return direct path
            return [start, end]
        
        # Find best path through gates
        best_start_gate = min(start_gates, key=lambda g: g.density_level)
        best_end_gate = min(end_gates, key=lambda g: g.density_level)
        
        # Create path through gates
        path = [
            start,
            best_start_gate.coordinate,
            best_end_gate.coordinate,
            end
        ]
        
        return path
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status."""
        return {
            "xspace_available": self.xspace is not None,
            "scanner_available": self.scanner is not None,
            "spatial_gates_count": len(self.spatial_gates),
            "spatial_mirrors_count": len(self.spatial_mirrors),
            "open_gates_count": sum(1 for g in self.spatial_gates.values() if g.is_open),
            "coord_to_gate_mappings": len(self.coord_to_gate),
        }


# Import math for distance calculations
import math
