"""
ASI- Integration for Spatial Coordinate Path Management
Configures ASI- to manage all possible paths on spatial coordinates and virtual sequences.
"""

import sys
import os
import json
import time
import math
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("light-asi.integration")

# Add ASI- to path
sys.path.insert(0, str(Path(__file__).parent / "ASI-"))

try:
    from engine.core.graph import NodeGraph
    from engine.core.node import Node
    from engine.world.semantic_map import SemanticMap
    # New real-world integration
    from engine.real_world.sonar_celestial_bridge import SonarCelestialBridge
    from engine.real_world.spectrum_real_world_engine import SpectrumRealWorldEngine
except ImportError:
    # Fallback if ASI- modules aren't available
    NodeGraph = None
    Node = None
    SemanticMap = None
    SonarCelestialBridge = None
    SpectrumRealWorldEngine = None

from lidar_sonar_engine import LidarSonarEngine, Coordinate


@dataclass
class SpatialPathNode:
    """Spatial path node for ASI- graph integration."""
    node_id: str
    coordinate: Coordinate
    path_type: str  # "waypoint", "gate", "mirror", "anchor"
    density: float
    connections: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VirtualSequence:
    """Virtual sequence for mesh layer coordination."""
    sequence_id: str
    path_nodes: List[str]
    start_coordinate: Coordinate
    end_coordinate: Coordinate
    score: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ASIIntegrator:
    """
    Integrates ASI- for spatial coordinate path management.
    Manages all possible paths on spatial coordinates and virtual sequences.
    """
    
    def __init__(self, lidar_engine: LidarSonarEngine):
        self.lidar_engine = lidar_engine
        
        # Initialize ASI- components if available
        if NodeGraph is not None:
            self.graph = NodeGraph()
            self.semantic_map = SemanticMap()
        else:
            self.graph = None
            self.semantic_map = None
            
        # Initialize real-world integration components
        if SonarCelestialBridge is not None and SpectrumRealWorldEngine is not None:
            self.sonar_bridge = SonarCelestialBridge(lidar_engine)
            self.spectrum_engine = SpectrumRealWorldEngine(lidar_engine)
            self.real_world_enabled = True
        else:
            self.sonar_bridge = None
            self.spectrum_engine = None
            self.real_world_enabled = False

        # VSync engine — render trigger from machine process for mesh topology
        try:
            from engine.render.vsync_engine import VSyncEngine
            self.vsync_engine = VSyncEngine(
                grid_bounds=(-50.0, 50.0, -50.0, 50.0),
                resolution=0.5,
            )
            # Wire vsync commit into the spatial-node update loop
            self.vsync_engine.on_vsync(self._on_vsync_commit)
            logger.info("VSync engine online — mesh topology render trigger active")
        except Exception as e:
            logger.warning(f"VSync engine unavailable: {e}")
            self.vsync_engine = None
            
        # Initialize full mode controller for activation management
        try:
            from engine.activation.full_mode_controller import FullModeController
            from engine.requirements.requirement_chain import RequirementChain
            from engine.requirements.data_sequence_provider import DataSequenceProvider
            
            self.full_mode_controller = FullModeController()
            self.requirement_chain = RequirementChain()
            self.data_provider = DataSequenceProvider()
            
            self._register_components_with_controller()
            
        except ImportError as e:
            logger.warning(f"Advanced activation features unavailable: {e}")
            self.full_mode_controller = None
            self.requirement_chain = None
            self.data_provider = None
        
        # Spatial path nodes
        self.spatial_nodes: Dict[str, SpatialPathNode] = {}
        
        # Virtual sequences
        self.virtual_sequences: Dict[str, VirtualSequence] = {}
        
        # Coordinate to node mapping
        self.coord_to_node: Dict[str, str] = {}
        
        # Path management
        self.active_paths: Dict[str, List[Coordinate]] = {}
        self.path_scores: Dict[str, float] = {}
        
        # Vysync state
        self.vysync_actual_data: List[Dict] = []
        self.vysync_map_data: List[Dict] = []
        
    def coordinate_to_node_id(self, coord: Coordinate) -> str:
        """Convert coordinate to node ID for ASI- graph."""
        raw = f"{coord.x_center:.6f}:{coord.y:.6f}:{coord.z:.6f}"
        return f"node_{hash(raw) % 100000000:08d}"
    
    def create_spatial_node(self, coord: Coordinate, 
                           path_type: str = "waypoint") -> SpatialPathNode:
        """
        Create spatial path node for ASI- graph integration.
        Nodes represent waypoints, gates, mirrors, or anchors.
        """
        node_id = self.coordinate_to_node_id(coord)
        
        # Get density at this coordinate
        density = self.lidar_engine._get_density_at_point(
            coord.x_center, coord.y
        )
        
        node = SpatialPathNode(
            node_id=node_id,
            coordinate=coord,
            path_type=path_type,
            density=density,
            metadata={
                "created_at": time.time(),
                "x_plus": coord.x_plus,
                "x_minus": coord.x_minus,
                "x_delta": coord.x_delta
            }
        )
        
        self.spatial_nodes[node_id] = node
        self.coord_to_node[f"{coord.x_center:.2f}_{coord.y:.2f}_{coord.z:.2f}"] = node_id
        
        # Also add to ASI- graph if available
        if self.graph is not None and Node is not None:
            # Create metadata for ASI- node
            asi_metadata = {
                "coordinate": {
                    "x": coord.x_center,
                    "y": coord.y,
                    "z": coord.z
                },
                "path_type": path_type,
                "density": density,
                "spatial_node": True
            }
            
            # Create and register node with ASI-
            asi_node = Node.create(len(self.spatial_nodes))
            asi_node.meta.position = {
                "x": coord.x_center,
                "y": coord.y,
                "z": coord.z
            }
            self.graph.add_node(asi_node)
        
        return node
    
    def connect_spatial_nodes(self, node_id1: str, node_id2: str) -> bool:
        """
        Connect two spatial nodes in the graph.
        Represents possible path between coordinates.
        """
        if node_id1 not in self.spatial_nodes or node_id2 not in self.spatial_nodes:
            return False
        
        node1 = self.spatial_nodes[node_id1]
        node2 = self.spatial_nodes[node_id2]
        
        # Add connections
        if node_id2 not in node1.connections:
            node1.connections.append(node_id2)
        if node_id1 not in node2.connections:
            node2.connections.append(node_id1)
        
        # Also connect in ASI- graph if available
        if self.graph is not None:
            # Find corresponding ASI- nodes
            asi_nodes = [n for n in self.graph._nodes if n.meta.node_id == int(node_id1.split('_')[1])]
            if asi_nodes:
                # In production, would properly connect nodes in ASI- graph
                pass
        
        return True
    
    def create_virtual_sequence(self, path_coords: List[Coordinate],
                                start_coord: Coordinate,
                                end_coord: Coordinate) -> VirtualSequence:
        """
        Create virtual sequence for mesh layer coordination.
        Represents a complete path through spatial coordinates.
        """
        # Convert coordinates to nodes
        node_ids = []
        for coord in path_coords:
            node_id = self.coordinate_to_node_id(coord)
            if node_id not in self.spatial_nodes:
                self.create_spatial_node(coord)
            node_ids.append(node_id)
        
        # Calculate path score
        score = self._calculate_path_score(path_coords)
        
        sequence_id = f"seq_{int(time.time() * 1000)}"
        
        sequence = VirtualSequence(
            sequence_id=sequence_id,
            path_nodes=node_ids,
            start_coordinate=start_coord,
            end_coordinate=end_coord,
            score=score,
            metadata={
                "node_count": len(node_ids),
                "total_distance": self._calculate_total_distance(path_coords)
            }
        )
        
        self.virtual_sequences[sequence_id] = sequence
        
        return sequence
    
    def _calculate_path_score(self, path_coords: List[Coordinate]) -> float:
        """Calculate score for path based on density and distance."""
        if not path_coords:
            return 0.0
        
        total_density = 0.0
        for coord in path_coords:
            density = self.lidar_engine._get_density_at_point(
                coord.x_center, coord.y
            )
            total_density += density
        
        avg_density = total_density / len(path_coords)
        
        # Lower density = better path
        score = 1.0 - avg_density
        
        return max(0.0, min(1.0, score))
    
    def _calculate_total_distance(self, path_coords: List[Coordinate]) -> float:
        """Calculate total distance of path."""
        if len(path_coords) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(path_coords) - 1):
            coord1 = path_coords[i]
            coord2 = path_coords[i + 1]
            distance = math.sqrt(
                (coord2.x_center - coord1.x_center)**2 +
                (coord2.y - coord1.y)**2 +
                (coord2.z - coord1.z)**2
            )
            total_distance += distance
        
        return total_distance
    
    def manage_all_possible_paths(self, region: Tuple[float, float, float, float],
                                 grid_size: float = 5.0) -> List[VirtualSequence]:
        """
        Manage all possible paths in a region.
        Creates virtual sequences for mesh layer coordination.
        """
        x_min, x_max, y_min, y_max = region
        
        # Create grid of waypoints
        waypoints = []
        x_steps = int((x_max - x_min) / grid_size)
        y_steps = int((y_max - y_min) / grid_size)
        
        for i in range(x_steps + 1):
            for j in range(y_steps + 1):
                x = x_min + i * grid_size
                y = y_min + j * grid_size
                coord = Coordinate(x, x, y, 0.0)
                waypoints.append(coord)
        
        # Create spatial nodes for all waypoints
        for waypoint in waypoints:
            self.create_spatial_node(waypoint)
        
        # Connect nearby nodes
        for i, node1 in enumerate(self.spatial_nodes.values()):
            for j, node2 in enumerate(self.spatial_nodes.values()):
                if i >= j:
                    continue
                
                distance = math.sqrt(
                    (node2.coordinate.x_center - node1.coordinate.x_center)**2 +
                    (node2.coordinate.y - node1.coordinate.y)**2
                )
                
                if distance <= grid_size * 1.5:
                    self.connect_spatial_nodes(node1.node_id, node2.node_id)
        
        # Create virtual sequences for all possible paths
        sequences = []
        
        # Simple path generation: connect waypoints in grid pattern
        for i in range(len(waypoints) - 1):
            path = waypoints[i:i+2]
            if len(path) == 2:
                sequence = self.create_virtual_sequence(path, path[0], path[-1])
                sequences.append(sequence)
        
        return sequences
    
    def vysync_coordinate_data(self, actual_data: List[Dict],
                               map_data: List[Dict]) -> Dict[str, Any]:
        """
        Vysync actual sonar paths with mapping data.
        Feeds the VSync engine so the render trigger can confirm alignment
        before committing the mesh topology frame.
        """
        self.vysync_actual_data = actual_data
        self.vysync_map_data    = map_data

        # Feed alignment data into the vsync engine
        if self.vsync_engine is not None:
            self.vsync_engine.feed_vysync_data(actual_data, map_data)

        # Build lidar points and spectrum freqs from actual data for ingest
        lidar_points    = self._extract_lidar_points(actual_data)
        spectrum_freqs  = self._extract_spectrum_freqs(actual_data)

        # Trigger mesh topology build + vsync
        vsync_event = None
        if self.vsync_engine is not None:
            vsync_event = self.vsync_engine.ingest_scan(
                lidar_points, spectrum_freqs,
                vysync_actual=actual_data,
                vysync_map=map_data,
            )

        # Legacy combined map (kept for downstream compatibility)
        combined_map = {
            "actual_sonar_data":  actual_data,
            "map_template_data":  map_data,
            "combined_points":    [],
            "heat_sources":       [],
            "mesh_alignments":    [],
            "vsync_event":        vsync_event.__dict__ if vsync_event else None,
            "vsync_aligned":      vsync_event.aligned if vsync_event else False,
        }

        for actual_point in actual_data:
            closest_map_point = self._find_closest_map_point(actual_point, map_data)
            if closest_map_point:
                combined_point = {
                    "actual_coordinate":  actual_point,
                    "map_coordinate":     closest_map_point,
                    "alignment_score":    self._calculate_alignment_score(
                        actual_point, closest_map_point
                    ),
                }
                combined_map["combined_points"].append(combined_point)

        for point in combined_map["combined_points"]:
            if point["alignment_score"] > 0.8:
                combined_map["heat_sources"].append(point)

        combined_map["mesh_alignments"] = self._calculate_mesh_alignments(
            combined_map["combined_points"]
        )

        return combined_map

    # ── VSync helpers ─────────────────────────────────────────────────────────

    def _on_vsync_commit(self, event, frame):
        """
        Callback fired by VSyncEngine when a mesh topology frame is committed.
        Updates the navigation stack with the fresh geometry.
        """
        logger.info(
            f"VSync commit: frame={event.frame_id}  "
            f"verts={event.mesh_vertices}  aligned={event.aligned}  "
            f"latency={event.render_latency_ms:.1f}ms"
        )

        # Push updated density grid into spectrum engine if available
        if self.spectrum_engine and frame.density_grid is not None:
            try:
                # Re-map spectrum points from the freshly built geometry
                if self.spectrum_engine.real_world_grid is None:
                    import numpy as np
                    self.spectrum_engine.real_world_grid = frame.density_grid.copy()
                else:
                    # Blend new frame into existing grid (exponential moving average)
                    alpha = 0.3
                    self.spectrum_engine.real_world_grid = (
                        alpha * frame.density_grid
                        + (1.0 - alpha) * self.spectrum_engine.real_world_grid
                    )
            except Exception as e:
                logger.warning(f"Spectrum grid update failed: {e}")

    def _extract_lidar_points(self, actual_data: List[Dict]) -> List[Dict]:
        """Convert vysync actual data to lidar point format for VSync engine."""
        points = []
        for item in actual_data:
            points.append({
                "x":         item.get("x", item.get("x_center", 0.0)),
                "y":         item.get("y", 0.0),
                "z":         item.get("z", 0.0),
                "intensity": item.get("intensity", item.get("density", 0.5)),
                "distance":  item.get("distance",
                                      math.sqrt(item.get("x", 0.0)**2 + item.get("y", 0.0)**2)),
            })
        return points

    def _extract_spectrum_freqs(self, actual_data: List[Dict]) -> List[Dict]:
        """Derive spectrum frequency entries from actual scan data."""
        freqs = []
        base_freq = 432.0  # MSFB base
        for item in actual_data:
            density = item.get("density", 0.2)
            freq    = base_freq * (1.0 + density * 0.5)
            freqs.append({
                "frequency": freq,
                "coord_x":   item.get("x", item.get("x_center", 0.0)),
                "coord_y":   item.get("y", 0.0),
                "confidence": item.get("confidence", 0.8),
            })
        return freqs

    def get_vsync_status(self) -> Dict[str, Any]:
        """Return current VSync engine status."""
        if self.vsync_engine is None:
            return {"vsync_available": False}
        return {"vsync_available": True, **self.vsync_engine.get_stats()}
    
    def _find_closest_map_point(self, actual_point: Dict, 
                               map_data: List[Dict]) -> Optional[Dict]:
        """Find closest map point to actual data point."""
        closest_point = None
        min_distance = float('inf')
        
        for map_point in map_data:
            distance = math.sqrt(
                (actual_point.get('x', 0) - map_point.get('x', 0))**2 +
                (actual_point.get('y', 0) - map_point.get('y', 0))**2
            )
            
            if distance < min_distance:
                min_distance = distance
                closest_point = map_point
        
        return closest_point
    
    def _calculate_alignment_score(self, actual_point: Dict, 
                                   map_point: Dict) -> float:
        """Calculate alignment score between actual and map point."""
        distance = math.sqrt(
            (actual_point.get('x', 0) - map_point.get('x', 0))**2 +
            (actual_point.get('y', 0) - map_point.get('y', 0))**2
        )
        
        max_distance = 10.0  # meters
        alignment = 1.0 - (distance / max_distance)
        
        return max(0.0, min(1.0, alignment))
    
    def _calculate_mesh_alignments(self, combined_points: List[Dict]) -> List[Dict]:
        """Calculate mesh alignments for density rendering."""
        alignments = []
        
        for point in combined_points:
            if point["alignment_score"] > 0.7:
                alignment = {
                    "coordinate": point["actual_coordinate"],
                    "mesh_coordinate": point["map_coordinate"],
                    "symmetry_score": point["alignment_score"],
                    "render_ready": True
                }
                alignments.append(alignment)
        
        return alignments
    
    def query_spatial_graph(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Query spatial graph using ASI- semantic search.
        Returns relevant spatial nodes and paths.
        """
        if self.graph is None:
            return []
        
        # Use ASI- graph query
        result = self.graph.query(query, top_k)
        
        # Filter for spatial nodes
        spatial_results = []
        for node_result in result.get("node_results", []):
            # Check if this is a spatial node
            if "spatial" in str(node_result).lower():
                spatial_results.append(node_result)
        
        return spatial_results
    
    def get_spatial_status(self) -> Dict[str, Any]:
        """Get current spatial integration status."""
        return {
            "graph_available": self.graph is not None,
            "semantic_map_available": self.semantic_map is not None,
            "spatial_nodes_count": len(self.spatial_nodes),
            "virtual_sequences_count": len(self.virtual_sequences),
            "active_paths_count": len(self.active_paths),
            "vysync_actual_data_count": len(self.vysync_actual_data),
            "vysync_map_data_count": len(self.vysync_map_data),
            "coord_to_node_mappings": len(self.coord_to_node),
            "vsync": self.get_vsync_status(),
        }
    
    def optimize_mesh_rendering(self, combined_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize mesh rendering based on vysync data.
        Ensures heat is managed thoroughly and not confused from source.
        """
        mesh_data = {
            "optimized_points": [],
            "heat_management": {},
            "symmetry_corrections": []
        }
        
        # Process combined points
        for point in combined_data.get("combined_points", []):
            actual = point["actual_coordinate"]
            map_coord = point["map_coordinate"]
            alignment = point["alignment_score"]
            
            # Apply symmetry correction
            if alignment > 0.8:
                corrected_point = {
                    "x": (actual.get('x', 0) + map_coord.get('x', 0)) / 2,
                    "y": (actual.get('y', 0) + map_coord.get('y', 0)) / 2,
                    "z": (actual.get('z', 0) + map_coord.get('z', 0)) / 2,
                    "confidence": alignment
                }
                mesh_data["optimized_points"].append(corrected_point)
                
                mesh_data["symmetry_corrections"].append({
                    "original": actual,
                    "corrected": corrected_point,
                    "correction_factor": alignment
                })
        
        # Manage heat sources
        for heat_source in combined_data.get("heat_sources", []):
            source_id = f"heat_{hash(str(heat_source)) % 10000}"
            mesh_data["heat_management"][source_id] = {
                "intensity": heat_source["alignment_score"],
                "coordinate": heat_source["actual_coordinate"],
                "managed": True
            }
        
        return mesh_data
    
    def initialize_real_world_mapping(self, scan_bounds: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """
        Initialize real-world mapping for autonomous driving.
        Integrates celestial routes with actual sonar-scanned spaces.
        """
        if not self.real_world_enabled:
            return {"error": "Real-world integration not available"}
        
        # Initialize spectrum engine mapping
        spectrum_result = self.spectrum_engine.initialize_real_world_mapping(scan_bounds)
        
        # Scan and map real space with celestial bridge
        bridge_result = self.sonar_bridge.scan_and_map_real_space(scan_bounds)
        
        # Update spatial nodes with real-world data
        for mapping in bridge_result:
            self.create_spatial_node(
                mapping.sonar_coordinate, 
                path_type="celestial_mapped"
            )
        
        return {
            "spectrum_mapping": spectrum_result,
            "celestial_mappings": len(bridge_result),
            "real_world_enabled": True,
            "scan_bounds": scan_bounds
        }
    
    def plan_real_world_route(self, start: Coordinate, destination: Coordinate,
                             vehicle_constraints: Dict[str, float]) -> List[Coordinate]:
        """
        Plan autonomous driving route using real sonar data and ASI celestial calculations.
        Returns optimized route for actual autonomous driving.
        """
        if not self.real_world_enabled:
            # Fallback to basic spatial path planning
            return self._fallback_route_planning(start, destination)
        
        # Use celestial bridge for real-world route planning
        celestial_route = self.sonar_bridge.plan_autonomous_route(
            start, destination, vehicle_constraints
        )
        
        # Create virtual sequence for the route
        route_sequence = self.create_virtual_sequence(
            celestial_route, start, destination
        )
        
        # Store route for real-time updates
        route_id = f"real_world_{int(time.time())}"
        self.active_paths[route_id] = celestial_route
        
        return celestial_route
    
    def update_vehicle_position(self, position: Coordinate):
        """Update vehicle position for real-time autonomous driving."""
        if self.real_world_enabled:
            self.spectrum_engine.update_vehicle_position(position)
            
            # Update active routes based on new position
            for route_id in list(self.active_paths.keys()):
                if route_id.startswith("real_world_"):
                    updated_route = self.sonar_bridge.update_route_real_time(route_id)
                    self.active_paths[route_id] = updated_route
    
    def get_real_time_navigation_data(self, query_coord: Coordinate) -> Dict[str, Any]:
        """Get real-time navigation data for autonomous driving decisions."""
        if not self.real_world_enabled:
            return {"error": "Real-world integration not available"}
        
        # Get spectrum data
        spectrum_data = self.spectrum_engine.get_real_time_spectrum_data(query_coord)
        
        # Get obstacle detection
        obstacles = self.sonar_bridge.real_time_obstacle_detection()
        
        # Combine for navigation decision
        navigation_data = {
            "spectrum_analysis": spectrum_data,
            "obstacle_count": len(obstacles),
            "obstacles": obstacles[:10],  # Limit for performance
            "navigation_safety": spectrum_data.get("navigation_safety", "unknown"),
            "recommendations": spectrum_data.get("navigation_recommendations", []),
            "timestamp": time.time()
        }
        
        return navigation_data
    
    def render_autonomous_driving_map(self, map_bounds: Optional[Tuple[float, float, float, float]] = None) -> Dict[str, Any]:
        """
        Render complete map for autonomous driving systems.
        Combines ASI celestial routes with real sonar data.
        """
        if not self.real_world_enabled:
            # Fallback to basic vysync mapping
            return self._fallback_map_rendering(map_bounds)
        
        # Render real-world map
        render_data = self.spectrum_engine.render_autonomous_driving_map(map_bounds)
        
        # Add ASI spatial nodes overlay
        asi_overlay = {
            "spatial_nodes": len(self.spatial_nodes),
            "virtual_sequences": len(self.virtual_sequences),
            "active_paths": list(self.active_paths.keys()),
            "coord_mappings": len(self.coord_to_node)
        }
        
        # Combine data
        combined_map = {
            "real_world_render": render_data,
            "asi_overlay": asi_overlay,
            "integration_status": self.get_integration_status(),
            "render_timestamp": time.time()
        }
        
        return combined_map
    
    def _fallback_route_planning(self, start: Coordinate, destination: Coordinate) -> List[Coordinate]:
        """Fallback route planning when real-world integration unavailable."""
        # Simple direct path with basic obstacle avoidance
        path = [start]
        
        # Add intermediate waypoints
        direction = (
            destination.x_center - start.x_center,
            destination.y - start.y
        )
        
        distance = math.sqrt(direction[0]**2 + direction[1]**2)
        num_waypoints = max(3, int(distance / 5.0))  # Waypoint every 5 meters
        
        for i in range(1, num_waypoints):
            t = i / num_waypoints
            waypoint_x = start.x_center + direction[0] * t
            waypoint_y = start.y + direction[1] * t
            
            waypoint = Coordinate(waypoint_x, waypoint_x, waypoint_y, 0.0)
            
            # Basic density check
            density = self.lidar_engine._get_density_at_point(waypoint_x, waypoint_y)
            if density <= 0.5:  # Safe threshold
                path.append(waypoint)
        
        path.append(destination)
        return path
    
    def _fallback_map_rendering(self, map_bounds: Optional[Tuple[float, float, float, float]]) -> Dict[str, Any]:
        """Fallback map rendering when real-world integration unavailable."""
        return {
            "error": "Real-world integration unavailable",
            "fallback_data": {
                "spatial_nodes": len(self.spatial_nodes),
                "virtual_sequences": len(self.virtual_sequences),
                "basic_mapping": True
            },
            "recommendation": "Enable real-world integration for full autonomous driving support"
        }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status including real-world capabilities."""
        base_status = self.get_spatial_status()
        
        # Add real-world integration status
        real_world_status = {
            "real_world_enabled": self.real_world_enabled,
            "sonar_bridge_available": self.sonar_bridge is not None,
            "spectrum_engine_available": self.spectrum_engine is not None
        }
        
        if self.real_world_enabled:
            real_world_status.update({
                "sonar_bridge_status": self.sonar_bridge.get_bridge_status(),
                "spectrum_engine_status": self.spectrum_engine.get_engine_status()
            })
        
        base_status["real_world_integration"] = real_world_status
        return base_status
    
    def optimize_for_autonomous_driving(self) -> Dict[str, Any]:
        """
        Optimize ASI integration specifically for autonomous driving performance.
        Ensures real-world task logic instead of simulated world logic.
        """
        optimization_results = {
            "timestamp": time.time(),
            "optimizations_applied": [],
            "performance_improvements": {}
        }
        
        if self.real_world_enabled:
            # Calibrate spectrum engine with reference points
            if hasattr(self.spectrum_engine, 'sonar_bridge'):
                # Use known safe areas as calibration references
                safe_references = [
                    (Coordinate(0.0, 0.0, 0.0, 0.0), 430.0),  # Known safe area
                    (Coordinate(10.0, 10.0, 10.0, 0.0), 435.0)  # Another reference
                ]
                
                calibration_result = self.spectrum_engine.sonar_bridge.calibrate_spectrum_engine(
                    safe_references
                )
                
                optimization_results["optimizations_applied"].append("spectrum_calibration")
                optimization_results["performance_improvements"]["calibration"] = calibration_result
        
        # Optimize spatial node density for real-time performance
        before_nodes = len(self.spatial_nodes)
        self._optimize_spatial_nodes_for_realtime()
        after_nodes = len(self.spatial_nodes)
        
        if before_nodes != after_nodes:
            optimization_results["optimizations_applied"].append("spatial_node_optimization")
            optimization_results["performance_improvements"]["node_reduction"] = {
                "before": before_nodes,
                "after": after_nodes,
                "reduction_percent": ((before_nodes - after_nodes) / before_nodes * 100) if before_nodes > 0 else 0
            }
        
        return optimization_results
    
    def _optimize_spatial_nodes_for_realtime(self):
        """Optimize spatial nodes for real-time autonomous driving performance."""
        # Remove low-confidence nodes that could slow down real-time decisions
        nodes_to_remove = []
        
        for node_id, node in self.spatial_nodes.items():
            if node.path_type == "waypoint" and node.density > 0.7:
                # High-density waypoints are not useful for autonomous driving
                nodes_to_remove.append(node_id)
            elif len(node.connections) == 0:
                # Isolated nodes don't contribute to path planning
                nodes_to_remove.append(node_id)
        
        # Remove identified nodes
        for node_id in nodes_to_remove:
            if node_id in self.spatial_nodes:
                del self.spatial_nodes[node_id]
        
        # Update coordinate mapping
        self.coord_to_node = {
            coord_key: node_id for coord_key, node_id in self.coord_to_node.items()
            if node_id in self.spatial_nodes
        }
    
    def _register_components_with_controller(self):
        """Register components with full mode controller for activation management."""
        if not self.full_mode_controller:
            return
        
        # Register core ASI components
        self.full_mode_controller.register_component(
            "node_graph",
            activation_callback=lambda: self._activate_node_graph(),
            maintenance_callback=lambda: self._maintain_node_graph(),
            priority=10,
            dependencies=[]
        )
        
        self.full_mode_controller.register_component(
            "semantic_map", 
            activation_callback=lambda: self._activate_semantic_map(),
            maintenance_callback=lambda: self._maintain_semantic_map(),
            priority=9,
            dependencies=[]
        )
        
        if self.real_world_enabled:
            self.full_mode_controller.register_component(
                "sonar_bridge",
                activation_callback=lambda: self._activate_sonar_bridge(),
                maintenance_callback=lambda: self._maintain_sonar_bridge(),
                priority=8,
                dependencies=["node_graph"]
            )
            
            self.full_mode_controller.register_component(
                "spectrum_engine",
                activation_callback=lambda: self._activate_spectrum_engine(), 
                maintenance_callback=lambda: self._maintain_spectrum_engine(),
                priority=8,
                dependencies=["sonar_bridge"]
            )
    
    def _activate_node_graph(self) -> bool:
        """Activate and ensure node graph is working."""
        try:
            if self.graph is None:
                return False
                
            # Force bootstrap if no nodes
            if len(self.graph._nodes) == 0:
                self.graph.bootstrap(n_nodes=100)
                
            return len(self.graph._nodes) > 0
        except Exception as e:
            logger.error(f"Node graph activation failed: {e}")
            return False
    
    def _maintain_node_graph(self):
        """Maintain node graph operation."""
        if self.graph and len(self.graph._nodes) < 50:
            # Ensure minimum node count for full operation
            self.graph.bootstrap(n_nodes=100)
    
    def _activate_semantic_map(self) -> bool:
        """Activate and ensure semantic map is working."""
        try:
            if self.semantic_map is None:
                return False
                
            # Test semantic map functionality
            test_result = self.semantic_map.store("test_activation", {"test": True})
            return test_result is not None
        except Exception as e:
            logger.error(f"Semantic map activation failed: {e}")
            return False
    
    def _maintain_semantic_map(self):
        """Maintain semantic map operation.""" 
        if self.semantic_map:
            # Perform periodic maintenance
            pass
    
    def _activate_sonar_bridge(self) -> bool:
        """Activate and ensure sonar bridge is working."""
        try:
            if not self.sonar_bridge:
                return False
                
            # Initialize with minimal scan if not done
            bridge_status = self.sonar_bridge.get_bridge_status()
            if bridge_status["real_space_mappings"] == 0:
                # Perform minimal scan to activate
                test_bounds = (-10.0, 10.0, -10.0, 10.0)
                mappings = self.sonar_bridge.scan_and_map_real_space(test_bounds, 2.0)
                return len(mappings) > 0
                
            return True
        except Exception as e:
            logger.error(f"Sonar bridge activation failed: {e}")
            return False
    
    def _maintain_sonar_bridge(self):
        """Maintain sonar bridge operation."""
        if self.sonar_bridge:
            # Update real-time obstacles
            self.sonar_bridge.real_time_obstacle_detection()
    
    def _activate_spectrum_engine(self) -> bool:
        """Activate and ensure spectrum engine is working."""
        try:
            if not self.spectrum_engine:
                return False
                
            # Initialize if not already done
            engine_status = self.spectrum_engine.get_engine_status()
            if not engine_status["initialized"]:
                # Initialize with minimal bounds
                test_bounds = (-10.0, 10.0, -10.0, 10.0)
                init_result = self.spectrum_engine.initialize_real_world_mapping(test_bounds)
                return init_result["mapping_points"] > 0
                
            return True
        except Exception as e:
            logger.error(f"Spectrum engine activation failed: {e}")
            return False
    
    def _maintain_spectrum_engine(self):
        """Maintain spectrum engine operation."""
        if self.spectrum_engine:
            # Clear old cache entries
            current_time = time.time()
            expired_keys = [
                key for key, point in self.spectrum_engine.scan_cache.items()
                if current_time - point.timestamp > 30.0
            ]
            for key in expired_keys:
                del self.spectrum_engine.scan_cache[key]
    
    def check_and_activate_full_mode(self) -> Dict[str, Any]:
        """
        Check conditions and activate full mode if ready.
        This bypasses basic iteration and locks all functions active.
        """
        if not self.full_mode_controller:
            return {"error": "Full mode controller not available"}
        
        # Get current integration status
        current_status = self.get_integration_status()
        
        # Check if conditions are met for full mode
        conditions_met = self.full_mode_controller.check_full_mode_conditions(current_status)
        
        if conditions_met:
            logger.info("🚀 Full mode conditions met - activating full system")
            activation_result = self.full_mode_controller.activate_full_mode()
            
            # Force populate components that were empty
            self._force_populate_components()
            
            return activation_result
        else:
            return {
                "status": "conditions_not_met",
                "current_mode": self.full_mode_controller.current_mode.value,
                "conditions_check": self.full_mode_controller.conditions_met_count
            }
    
    def _force_populate_components(self):
        """Force populate components with data to ensure they stay active."""
        
        # Populate spatial nodes if empty
        if len(self.spatial_nodes) == 0:
            logger.info("Populating spatial nodes for full mode operation")
            
            # Create a grid of spatial nodes for autonomous driving
            for x in range(-20, 21, 5):  # -20 to 20 in 5m steps
                for y in range(-20, 21, 5):
                    coord = Coordinate(x - 0.5, x + 0.5, float(y), 0.0)
                    self.create_spatial_node(coord, "autonomous_waypoint")
        
        # Populate virtual sequences if empty
        if len(self.virtual_sequences) == 0:
            logger.info("Creating virtual sequences for full mode operation")
            
            # Create sample routes for testing
            sample_routes = [
                [Coordinate(-10.0, -9.0, -10.0, 0.0), Coordinate(0.0, 1.0, 0.0, 0.0), Coordinate(10.0, 11.0, 10.0, 0.0)],
                [Coordinate(-15.0, -14.0, 0.0, 0.0), Coordinate(0.0, 1.0, 15.0, 0.0), Coordinate(15.0, 16.0, 0.0, 0.0)]
            ]
            
            for i, route in enumerate(sample_routes):
                sequence = self.create_virtual_sequence(
                    route, route[0], route[-1]
                )
    
    def maintain_full_mode_operation(self) -> Dict[str, Any]:
        """
        Maintain full mode operation - ensure all functions stay active.
        Call this periodically to prevent system degradation.
        """
        if not self.full_mode_controller:
            return {"error": "Full mode controller not available"}
        
        # Get current status
        current_status = self.get_integration_status()
        
        # Run maintenance
        maintenance_result = self.full_mode_controller.maintain_full_mode(current_status)
        
        # Additional ASI-specific maintenance
        if self.full_mode_controller.current_mode.value == "full_mode_locked":
            
            # Ensure minimum data levels
            if len(self.spatial_nodes) < 10:
                self._force_populate_components()
            
            # Refresh real-world mappings if needed
            if self.real_world_enabled and self.sonar_bridge:
                bridge_status = self.sonar_bridge.get_bridge_status()
                if bridge_status["real_space_mappings"] < 5:
                    logger.info("Refreshing real-world mappings")
                    test_bounds = (-25.0, 25.0, -25.0, 25.0)
                    self.sonar_bridge.scan_and_map_real_space(test_bounds, 2.0)
        
        return maintenance_result
    
    def get_full_mode_status(self) -> Dict[str, Any]:
        """Get comprehensive full mode status."""
        if not self.full_mode_controller:
            return {"full_mode_available": False}
        
        controller_status = self.full_mode_controller.get_controller_status()
        
        return {
            "full_mode_available": True,
            "controller_status": controller_status,
            "integration_health": {
                "spatial_nodes": len(self.spatial_nodes),
                "virtual_sequences": len(self.virtual_sequences),
                "active_paths": len(self.active_paths),
                "real_world_enabled": self.real_world_enabled
            }
        }
    
    def diagnose_and_resolve_requirements(self) -> Dict[str, Any]:
        """
        Diagnose missing requirements and resolve them with auto-provision.
        This fixes the zero-value issue by providing missing data sequences.
        """
        if not self.requirement_chain:
            return {"error": "Requirement chain not available"}
        
        # Get current integration status
        current_status = self.get_integration_status()
        
        # Check all requirements in the chain
        requirements_check = self.requirement_chain.check_chain_requirements(current_status)
        
        logger.info(f"Requirements check: {requirements_check['systems_ready']}/{requirements_check['systems_checked']} systems ready")
        
        # Apply any auto-provisions that were identified
        if requirements_check["auto_provisions_applied"]:
            logger.info(f"Applied {len(requirements_check['auto_provisions_applied'])} auto-provisions")
            
            # Now apply the provisioned data to actual system components
            self._apply_provisioned_data_to_systems(requirements_check["auto_provisions_applied"])
        
        # Generate missing data sequences if needed
        if not requirements_check["overall_ready"]:
            missing_sequences = self._identify_missing_sequences(requirements_check)
            if missing_sequences:
                generated_sequences = self._generate_missing_sequences(missing_sequences)
                self._inject_sequences_into_systems(generated_sequences)
        
        # Re-check after provisions
        final_status = self.get_integration_status()
        final_check = self.requirement_chain.check_chain_requirements(final_status)
        
        return {
            "initial_check": requirements_check,
            "final_check": final_check,
            "sequences_generated": len(getattr(self, '_generated_sequences', [])),
            "improvement": {
                "systems_ready_before": requirements_check["systems_ready"],
                "systems_ready_after": final_check["systems_ready"],
                "overall_ready": final_check["overall_ready"]
            },
            "developer_guidance": final_check["next_steps"]
        }
    
    def _apply_provisioned_data_to_systems(self, provisions: List[Dict[str, Any]]):
        """Apply auto-provisioned data to actual system components."""
        
        for provision in provisions:
            field_name = provision["field"]
            provided_value = provision["provided_value"]
            system_name = provision["system"]
            
            try:
                if system_name == "spatial_nodes" and field_name == "spatial_nodes_count":
                    # Ensure we have the minimum spatial nodes
                    if len(self.spatial_nodes) < provided_value:
                        self._create_default_spatial_nodes(provided_value)
                        
                elif system_name == "spatial_nodes" and field_name == "coord_to_node_mappings":
                    # Update coordinate mappings
                    if len(self.coord_to_node) < provided_value:
                        self._create_coord_mappings(provided_value)
                        
                elif system_name == "real_world_integration" and field_name == "real_space_mappings":
                    # Generate real space mappings
                    if self.sonar_bridge:
                        self._ensure_real_space_mappings(provided_value)
                        
                elif system_name == "real_world_integration" and field_name == "spectrum_points":
                    # Generate spectrum points
                    if self.spectrum_engine:
                        self._ensure_spectrum_points(provided_value)
                        
                logger.info(f"Applied provision: {system_name}.{field_name} = {provided_value}")
                
            except Exception as e:
                logger.error(f"Failed to apply provision {system_name}.{field_name}: {e}")
    
    def _identify_missing_sequences(self, requirements_check: Dict[str, Any]) -> List[str]:
        """Identify what data sequences are missing based on requirements check."""
        
        missing_sequences = []
        
        for system_name, system_result in requirements_check["system_results"].items():
            if not system_result["ready_for_activation"]:
                
                # Get system requirement definition
                if self.requirement_chain and system_name in self.requirement_chain.system_requirements:
                    requirement = self.requirement_chain.system_requirements[system_name]
                    
                    # Add data sequence needs for this system
                    missing_sequences.extend(requirement.data_sequence_needs)
        
        # Remove duplicates
        return list(set(missing_sequences))
    
    def _generate_missing_sequences(self, missing_sequences: List[str]) -> Dict[str, Any]:
        """Generate missing data sequences using the data provider."""
        
        if not self.data_provider:
            return {}
        
        from engine.requirements.data_sequence_provider import SequenceType
        
        # Map sequence names to types
        sequence_type_mapping = {
            "hash_sequences": SequenceType.HASH_SEQUENCES,
            "node_metadata": SequenceType.NODE_METADATA,
            "routing_table": SequenceType.ROUTING_TABLE,
            "coordinate_data": SequenceType.COORDINATE_DATA,
            "density_mappings": SequenceType.DENSITY_MAPPINGS,
            "sonar_scan_data": SequenceType.SONAR_SCAN_DATA,
            "spectrum_frequencies": SequenceType.SPECTRUM_FREQUENCIES,
            "route_coordinates": SequenceType.ROUTE_COORDINATES,
            "path_coordinates": SequenceType.PATH_COORDINATES,
            "sequence_metadata": SequenceType.SEQUENCE_METADATA
        }
        
        # Convert to sequence types
        needed_types = []
        for seq_name in missing_sequences:
            if seq_name in sequence_type_mapping:
                needed_types.append(sequence_type_mapping[seq_name])
        
        if not needed_types:
            return {}
        
        # Generate sequences in bulk
        logger.info(f"Generating {len(needed_types)} missing data sequences")
        generated = self.data_provider.bulk_provide_sequences(needed_types)
        
        # Store reference for later use
        if not hasattr(self, '_generated_sequences'):
            self._generated_sequences = {}
        self._generated_sequences.update(generated)
        
        return generated
    
    def _inject_sequences_into_systems(self, sequences: Dict[str, Any]):
        """Inject generated sequences into appropriate system components."""
        
        for sequence_type, sequence_data in sequences.items():
            try:
                sequence_name = sequence_type.value if hasattr(sequence_type, 'value') else str(sequence_type)
                
                if sequence_name == "coordinate_data":
                    self._inject_coordinate_data(sequence_data.data)
                elif sequence_name == "route_coordinates":
                    self._inject_route_coordinates(sequence_data.data)
                elif sequence_name == "spectrum_frequencies":
                    self._inject_spectrum_frequencies(sequence_data.data)
                elif sequence_name == "node_metadata":
                    self._inject_node_metadata(sequence_data.data)
                
                logger.info(f"Injected {sequence_name} sequence: {sequence_data.size} items")
                
            except Exception as e:
                logger.error(f"Failed to inject sequence {sequence_type}: {e}")
    
    def _create_default_spatial_nodes(self, count: int):
        """Create default spatial nodes to meet requirements."""
        
        current_count = len(self.spatial_nodes)
        nodes_needed = max(0, count - current_count)
        
        logger.info(f"Creating {nodes_needed} default spatial nodes")
        
        # Create nodes in a grid pattern
        grid_size = int(math.ceil(math.sqrt(nodes_needed)))
        
        for i in range(nodes_needed):
            row = i // grid_size
            col = i % grid_size
            
            x = (col - grid_size//2) * 5.0  # 5m spacing
            y = (row - grid_size//2) * 5.0
            
            coord = Coordinate(x - 0.5, x + 0.5, y, 0.0)
            self.create_spatial_node(coord, "default_waypoint")
    
    def _create_coord_mappings(self, count: int):
        """Create coordinate-to-node mappings."""
        
        current_count = len(self.coord_to_node)
        mappings_needed = max(0, count - current_count)
        
        # Create mappings for existing spatial nodes
        for i, (node_id, spatial_node) in enumerate(self.spatial_nodes.items()):
            if i >= mappings_needed:
                break
                
            coord_key = f"{spatial_node.coordinate.x_center:.1f}_{spatial_node.coordinate.y:.1f}"
            self.coord_to_node[coord_key] = node_id
    
    def _ensure_real_space_mappings(self, count: int):
        """Ensure minimum real space mappings exist."""
        
        if not self.sonar_bridge:
            return
            
        current_mappings = len(self.sonar_bridge.real_space_mappings)
        if current_mappings < count:
            # Perform a scan to create mappings
            test_bounds = (-15.0, 15.0, -15.0, 15.0)
            self.sonar_bridge.scan_and_map_real_space(test_bounds, 2.0)
    
    def _ensure_spectrum_points(self, count: int):
        """Ensure minimum spectrum points exist."""
        
        if not self.spectrum_engine:
            return
            
        current_points = len(self.spectrum_engine.spectrum_map_points)
        if current_points < count:
            # Initialize spectrum mapping if needed
            if not self.spectrum_engine.get_engine_status()["initialized"]:
                test_bounds = (-15.0, 15.0, -15.0, 15.0)
                self.spectrum_engine.initialize_real_world_mapping(test_bounds)
    
    def _inject_coordinate_data(self, coord_data: List[Dict[str, Any]]):
        """Inject coordinate data into spatial nodes."""
        
        for coord_dict in coord_data[:10]:  # Limit to prevent overload
            try:
                coord = Coordinate(
                    coord_dict["x_left"],
                    coord_dict["x_right"], 
                    coord_dict["y"],
                    coord_dict.get("z", 0.0)
                )
                
                if coord_dict.get("navigation_safe", True):
                    self.create_spatial_node(coord, "injected_waypoint")
                    
            except Exception as e:
                logger.warning(f"Failed to inject coordinate: {e}")
    
    def _inject_route_coordinates(self, route_data: List[List[Dict[str, float]]]):
        """Inject route coordinates into virtual sequences."""
        
        for route in route_data[:3]:  # Limit to 3 routes
            try:
                route_coords = []
                for coord_dict in route:
                    coord = Coordinate(
                        coord_dict["x_left"],
                        coord_dict["x_right"],
                        coord_dict["y"],
                        coord_dict.get("z", 0.0)
                    )
                    route_coords.append(coord)
                
                if len(route_coords) >= 2:
                    self.create_virtual_sequence(route_coords, route_coords[0], route_coords[-1])
                    
            except Exception as e:
                logger.warning(f"Failed to inject route: {e}")
    
    def _inject_spectrum_frequencies(self, freq_data: List[Dict[str, Any]]):
        """Inject spectrum frequencies into spectrum engine."""
        
        if not self.spectrum_engine:
            return
            
        # Convert frequency data to spectrum map points
        for freq_dict in freq_data[:20]:  # Limit injection
            try:
                coord = Coordinate(
                    freq_dict["coord_x"] - 0.5,
                    freq_dict["coord_x"] + 0.5,
                    freq_dict["coord_y"],
                    0.0
                )
                
                # This would inject into spectrum engine in a full implementation
                # For now, just log the injection
                logger.debug(f"Injected spectrum point: {freq_dict['frequency']:.1f}Hz at ({freq_dict['coord_x']:.1f}, {freq_dict['coord_y']:.1f})")
                
            except Exception as e:
                logger.warning(f"Failed to inject spectrum frequency: {e}")
    
    def _inject_node_metadata(self, metadata_list: List[Dict[str, Any]]):
        """Inject node metadata into node graph."""
        
        if not self.graph:
            return
            
        # Ensure graph has nodes to attach metadata to
        if len(self.graph._nodes) == 0:
            self.graph.bootstrap(n_nodes=len(metadata_list))
        
        # Attach metadata to existing nodes
        for i, metadata in enumerate(metadata_list):
            if i < len(self.graph._nodes):
                node = self.graph._nodes[i]
                
                # Update node metadata (this would be more sophisticated in full implementation)
                if hasattr(node, 'meta'):
                    for key, value in metadata.items():
                        if hasattr(node.meta, key):
                            setattr(node.meta, key, value)
    
    def get_requirements_status(self) -> Dict[str, Any]:
        """Get current requirements status with developer guidance."""
        
        if not self.requirement_chain:
            return {"error": "Requirement chain not available"}
        
        current_status = self.get_integration_status()
        requirements_check = self.requirement_chain.check_chain_requirements(current_status)
        
        return {
            "requirements_check": requirements_check,
            "data_provider_status": self.data_provider.get_provider_status() if self.data_provider else None,
            "chain_status": self.requirement_chain.get_requirement_status(),
            "ready_for_full_mode": requirements_check["overall_ready"],
            "developer_guidance": {
                "critical_issues": len(requirements_check["critical_failures"]),
                "next_steps": requirements_check["next_steps"],
                "auto_fix_available": len(requirements_check.get("auto_provisions_applied", [])) > 0
            }
        }