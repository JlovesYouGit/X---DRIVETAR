"""
Neural Brain Integration - Zero-Brain Concepts for Autonomous Navigation
Integrates zero-brain concepts (brain mesh, neural paths, cortex latch) with Python
for autonomous smart decision algorithms and driver experience learning.
"""

import json
import math
import time
import hashlib
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from lidar_sonar_engine import LidarSonarEngine, Coordinate, VehicleControlInput


class BrainState(Enum):
    """Brain state similar to zero-brain node states."""
    ACTIVE = "active"
    DORMANT = "dormant"
    LOCKED = "locked"
    BREACH = "breach"
    LEARNING = "learning"


class NeuralPathType(Enum):
    """Types of neural paths for decision making."""
    SAFETY = "safety"
    EFFICIENCY = "efficiency"
    COMFORT = "comfort"
    COMPLIANCE = "compliance"
    EMERGENCY = "emergency"


@dataclass
class NeuralWeight:
    """Neural network weight for learning."""
    layer_id: str
    neuron_id: str
    weight: float
    bias: float
    gradient: float = 0.0
    last_updated: float = field(default_factory=time.time)
    importance: float = 1.0


@dataclass
class NeuralPath:
    """Neural path for decision routing."""
    path_id: str
    path_type: NeuralPathType
    source_neuron: str
    target_neuron: str
    activation_threshold: float
    current_activation: float
    weight: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrainMeshNode:
    """Node in brain mesh network."""
    node_id: str
    position: Tuple[float, float, float]
    activation: float
    connections: List[str]
    layer: int  # Depth in neural network
    state: BrainState = BrainState.ACTIVE
    lock_seed: Optional[str] = None


@dataclass
class CortexLatch:
    """Cortex latch for pattern matching and replay (zero-brain concept)."""
    latch_id: str
    pattern_hash: str
    capability_profile: Dict[str, Any]
    success_count: int
    failure_count: int
    last_used: float = field(default_factory=time.time)
    confidence: float = 1.0


@dataclass
class DriverExperience:
    """Driver experience learning data."""
    experience_id: str
    driver_id: str
    scenario_type: str
    control_inputs: List[VehicleControlInput]
    outcomes: List[Dict[str, Any]]
    success_rate: float
    comfort_score: float
    compliance_score: float
    learned_weights: Dict[str, NeuralWeight] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SpatialCacheEntry:
    """Cached spatial data for AI fallback."""
    cache_id: str
    spatial_hash: str
    coordinate: Coordinate
    density: float
    optimal_control: VehicleControlInput
    confidence: float
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class CoordinationSavePoint:
    """Save point for coordination actuation logic."""
    save_id: str
    spatial_context: Dict[str, Any]
    control_state: VehicleControlInput
    brain_state: Dict[str, float]
    success_outcome: bool
    timestamp: float = field(default_factory=time.time)


class NeuralBrainEngine:
    """
    Neural brain engine integrating zero-brain concepts.
    Manages brain mesh, neural paths, cortex latch, and driver experience learning.
    """
    
    def __init__(self, lidar_engine: LidarSonarEngine, 
                 weight_file_path: str = "neural_weights.json"):
        self.lidar_engine = lidar_engine
        self.weight_file_path = weight_file_path
        
        # Brain mesh network
        self.brain_mesh: Dict[str, BrainMeshNode] = {}
        self.external_brain_mesh: Dict[str, BrainMeshNode] = {}
        
        # Neural paths
        self.neural_paths: Dict[str, NeuralPath] = {}
        
        # Neural weights
        self.neural_weights: Dict[str, NeuralWeight] = {}
        
        # Cortex latches
        self.cortex_latches: Dict[str, CortexLatch] = {}
        
        # Driver experiences
        self.driver_experiences: Dict[str, DriverExperience] = {}
        
        # Dual-layer cache system for AI fallback
        self.spatial_cache: Dict[str, SpatialCacheEntry] = {}
        self.coordination_save_points: Dict[str, CoordinationSavePoint] = {}
        self.cache_max_size = 1000
        self.cache_ttl = 3600  # 1 hour
        
        # Brain mesh sync state
        self.mesh_sync_state = {
            "external_detected": False,
            "internal_active": False,
            "bidirectional_sync": False,
            "sync_quality": 0.0,
            "last_sync_time": 0.0
        }
        
        # AI availability flag
        self.ai_available = True
        
        # Initialize brain mesh
        self._initialize_brain_mesh()
        
        # Load weights if available
        self.load_neural_weights()
    
    def _initialize_brain_mesh(self):
        """Initialize brain mesh network with layers."""
        # Create input layer (sensor data)
        for i in range(10):
            node = BrainMeshNode(
                node_id=f"input_{i}",
                position=(i * 1.0, 0.0, 0.0),
                activation=0.0,
                connections=[],
                layer=0
            )
            self.brain_mesh[node.node_id] = node
        
        # Create hidden layers
        for layer in range(1, 4):
            for i in range(20):
                node = BrainMeshNode(
                    node_id=f"hidden_{layer}_{i}",
                    position=(i * 0.5, layer * 1.0, 0.0),
                    activation=0.0,
                    connections=[],
                    layer=layer
                )
                self.brain_mesh[node.node_id] = node
        
        # Create output layer (control decisions)
        output_types = ["throttle", "brake", "steering_left", "steering_right", "emergency"]
        for i, output_type in enumerate(output_types):
            node = BrainMeshNode(
                node_id=f"output_{output_type}",
                position=(i * 2.0, 5.0, 0.0),
                activation=0.0,
                connections=[],
                layer=4
            )
            self.brain_mesh[node.node_id] = node
        
        # Create neural paths
        self._create_neural_paths()
    
    def _create_neural_paths(self):
        """Create neural paths between layers."""
        # Connect input to hidden layer 1
        for i in range(10):
            for j in range(20):
                path = NeuralPath(
                    path_id=f"path_input_{i}_hidden_1_{j}",
                    path_type=NeuralPathType.EFFICIENCY,
                    source_neuron=f"input_{i}",
                    target_neuron=f"hidden_1_{j}",
                    activation_threshold=0.5,
                    current_activation=0.0,
                    weight=np.random.uniform(-1, 1),
                    confidence=0.5
                )
                self.neural_paths[path.path_id] = path
        
        # Connect hidden layers
        for layer in range(1, 3):
            for i in range(20):
                for j in range(20):
                    path = NeuralPath(
                        path_id=f"path_hidden_{layer}_{i}_hidden_{layer+1}_{j}",
                        path_type=NeuralPathType.SAFETY,
                        source_neuron=f"hidden_{layer}_{i}",
                        target_neuron=f"hidden_{layer+1}_{j}",
                        activation_threshold=0.3,
                        current_activation=0.0,
                        weight=np.random.uniform(-1, 1),
                        confidence=0.7
                    )
                    self.neural_paths[path.path_id] = path
        
        # Connect hidden layer 3 to output
        for i in range(20):
            for j, output_type in enumerate(["throttle", "brake", "steering_left", "steering_right", "emergency"]):
                path = NeuralPath(
                    path_id=f"path_hidden_3_{i}_output_{output_type}",
                    path_type=NeuralPathType.COMPLIANCE,
                    source_neuron=f"hidden_3_{i}",
                    target_neuron=f"output_{output_type}",
                    activation_threshold=0.4,
                    current_activation=0.0,
                    weight=np.random.uniform(-1, 1),
                    confidence=0.8
                )
                self.neural_paths[path.path_id] = path
    
    def process_sensor_data(self, sensor_data: Dict[str, float]) -> Dict[str, float]:
        """
        Process sensor data through brain mesh.
        Returns control decisions.
        """
        # Activate input layer with sensor data
        sensor_keys = list(sensor_data.keys())[:10]
        for i, key in enumerate(sensor_keys):
            if f"input_{i}" in self.brain_mesh:
                self.brain_mesh[f"input_{i}"].activation = sensor_data[key]
        
        # Propagate through neural paths
        self._propagate_activation()
        
        # Get output layer activations
        outputs = {}
        for node_id, node in self.brain_mesh.items():
            if node_id.startswith("output_"):
                output_type = node_id.replace("output_", "")
                outputs[output_type] = node.activation
        
        return outputs
    
    def _propagate_activation(self):
        """Propagate activation through neural paths."""
        # Sort paths by layer
        paths_by_layer = {}
        for path_id, path in self.neural_paths.items():
            source_layer = self.brain_mesh[path.source_neuron].layer
            if source_layer not in paths_by_layer:
                paths_by_layer[source_layer] = []
            paths_by_layer[source_layer].append(path)
        
        # Propagate layer by layer
        for layer in sorted(paths_by_layer.keys()):
            for path in paths_by_layer[layer]:
                source_node = self.brain_mesh[path.source_neuron]
                target_node = self.brain_mesh[path.target_neuron]
                
                # Calculate activation
                activation = source_node.activation * path.weight
                
                # Apply threshold
                if activation > path.activation_threshold:
                    target_node.activation += activation * path.confidence
                
                # Clamp activation
                target_node.activation = max(0.0, min(1.0, target_node.activation))
    
    def create_cortex_latch(self, pattern: Dict[str, Any], 
                          capability_profile: Dict[str, Any]) -> CortexLatch:
        """
        Create cortex latch for pattern matching (zero-brain concept).
        Stores capability profile for replay when pattern matches.
        """
        pattern_hash = self._compute_pattern_hash(pattern)
        latch_id = f"latch_{pattern_hash[:8]}"
        
        latch = CortexLatch(
            latch_id=latch_id,
            pattern_hash=pattern_hash,
            capability_profile=capability_profile,
            success_count=0,
            failure_count=0,
            confidence=1.0
        )
        
        self.cortex_latches[latch_id] = latch
        return latch
    
    def match_cortex_latch(self, pattern: Dict[str, Any]) -> Optional[CortexLatch]:
        """Match pattern against cortex latches."""
        pattern_hash = self._compute_pattern_hash(pattern)
        
        for latch in self.cortex_latches.values():
            if latch.pattern_hash == pattern_hash:
                latch.last_used = time.time()
                return latch
        
        return None
    
    def reinforce_latch(self, latch_id: str, success: bool):
        """Reinforce cortex latch based on outcome."""
        if latch_id in self.cortex_latches:
            latch = self.cortex_latches[latch_id]
            if success:
                latch.success_count += 1
            else:
                latch.failure_count += 1
            
            # Update confidence
            total = latch.success_count + latch.failure_count
            latch.confidence = latch.success_count / total if total > 0 else 0.5
    
    def record_driver_experience(self, driver_id: str, scenario_type: str,
                               control_inputs: List[VehicleControlInput],
                               outcomes: List[Dict[str, Any]]) -> DriverExperience:
        """
        Record driver experience for learning.
        Learns from human driver behavior to improve autonomous decisions.
        """
        experience_id = f"exp_{driver_id}_{int(time.time())}"
        
        # Calculate metrics
        success_rate = sum(1 for o in outcomes if o.get("success", False)) / len(outcomes)
        comfort_score = self._calculate_comfort_score(control_inputs)
        compliance_score = self._calculate_compliance_score(outcomes)
        
        # Extract learned weights from experience
        learned_weights = self._extract_learned_weights(control_inputs, outcomes)
        
        experience = DriverExperience(
            experience_id=experience_id,
            driver_id=driver_id,
            scenario_type=scenario_type,
            control_inputs=control_inputs,
            outcomes=outcomes,
            success_rate=success_rate,
            comfort_score=comfort_score,
            compliance_score=compliance_score,
            learned_weights=learned_weights
        )
        
        self.driver_experiences[experience_id] = experience
        
        # Update neural weights based on experience
        self._update_weights_from_experience(experience)
        
        return experience
    
    def _calculate_comfort_score(self, control_inputs: List[VehicleControlInput]) -> float:
        """Calculate comfort score based on input smoothness."""
        if len(control_inputs) < 2:
            return 1.0
        
        # Calculate jerk (rate of change)
        throttle_changes = [abs(control_inputs[i].throttle - control_inputs[i-1].throttle) 
                          for i in range(1, len(control_inputs))]
        steering_changes = [abs(control_inputs[i].steering - control_inputs[i-1].steering) 
                           for i in range(1, len(control_inputs))]
        
        avg_jerk = (sum(throttle_changes) + sum(steering_changes)) / (len(throttle_changes) + len(steering_changes))
        comfort_score = 1.0 - min(avg_jerk, 1.0)
        
        return max(0.0, comfort_score)
    
    def _calculate_compliance_score(self, outcomes: List[Dict[str, Any]]) -> float:
        """Calculate compliance score based on safety outcomes."""
        if not outcomes:
            return 1.0
        
        # Check for safety violations
        violations = sum(1 for o in outcomes if o.get("safety_violation", False))
        compliance_score = 1.0 - (violations / len(outcomes))
        
        return max(0.0, compliance_score)
    
    def _extract_learned_weights(self, control_inputs: List[VehicleControlInput],
                                outcomes: List[Dict[str, Any]]) -> Dict[str, NeuralWeight]:
        """Extract learned weights from driver experience."""
        learned = {}
        
        # Simple weight extraction based on success patterns
        for i, (control_input, outcome) in enumerate(zip(control_inputs, outcomes)):
            if outcome.get("success", False):
                # Reward successful patterns
                weight_id = f"weight_{i}"
                learned[weight_id] = NeuralWeight(
                    layer_id="hidden_3",
                    neuron_id=f"neuron_{i % 20}",
                    weight=control_input.throttle * 2.0 - 1.0,  # Normalize to -1 to 1
                    bias=control_input.brake * 2.0 - 1.0,
                    importance=1.0
                )
        
        return learned
    
    def _update_weights_from_experience(self, experience: DriverExperience):
        """Update neural weights based on driver experience."""
        for weight_id, learned_weight in experience.learned_weights.items():
            if weight_id in self.neural_weights:
                # Update existing weight with moving average
                existing = self.neural_weights[weight_id]
                alpha = 0.1  # Learning rate
                existing.weight = (1 - alpha) * existing.weight + alpha * learned_weight.weight
                existing.bias = (1 - alpha) * existing.bias + alpha * learned_weight.bias
                existing.last_updated = time.time()
                existing.importance = experience.success_rate
            else:
                # Add new weight
                self.neural_weights[weight_id] = learned_weight
    
    def get_smart_decision(self, sensor_data: Dict[str, float],
                         context: Dict[str, Any]) -> VehicleControlInput:
        """
        Get smart decision from neural brain.
        Incorporates zero-brain concepts and learned driver experience.
        Falls back to cache if AI is unavailable.
        """
        # Check if AI is available
        if not self.ai_available:
            return self._get_cached_decision(sensor_data, context)
        
        # Process through brain mesh
        outputs = self.process_sensor_data(sensor_data)
        
        # Check cortex latch for pattern match
        pattern = {**sensor_data, **context}
        matched_latch = self.match_cortex_latch(pattern)
        
        if matched_latch and matched_latch.confidence > 0.7:
            # Use latched capability profile
            profile = matched_latch.capability_profile
            throttle = profile.get("throttle", 0.5)
            brake = profile.get("brake", 0.0)
            steering = profile.get("steering", 0.0)
        else:
            # Use neural network outputs
            throttle = outputs.get("throttle", 0.5)
            brake = outputs.get("brake", 0.0)
            
            # Combine steering outputs
            steering_left = outputs.get("steering_left", 0.0)
            steering_right = outputs.get("steering_right", 0.0)
            steering = steering_right - steering_left
        
        # Apply emergency override
        emergency = outputs.get("emergency", 0.0)
        if emergency > 0.8:
            throttle = 0.0
            brake = 1.0
        
        # Clamp values
        throttle = max(0.0, min(1.0, throttle))
        brake = max(0.0, min(1.0, brake))
        steering = max(-1.0, min(1.0, steering))
        
        decision = VehicleControlInput(
            throttle=throttle,
            brake=brake,
            steering=steering,
            gear="drive"
        )
        
        # Cache this decision for fallback
        self._cache_spatial_decision(sensor_data, context, decision)
        
        return decision
    
    def _cache_spatial_decision(self, sensor_data: Dict[str, float],
                                context: Dict[str, Any],
                                decision: VehicleControlInput):
        """Cache spatial decision for AI fallback."""
        # Get spatial data from lidar engine
        coord = self.lidar_engine.vehicle_state.center_coordinate
        density = self.lidar_engine._get_density_at_point(coord.x_center, coord.y)
        
        # Create spatial hash
        spatial_hash = self._compute_spatial_hash(coord, sensor_data, context)
        
        cache_entry = SpatialCacheEntry(
            cache_id=f"cache_{spatial_hash[:8]}",
            spatial_hash=spatial_hash,
            coordinate=coord,
            density=density,
            optimal_control=decision,
            confidence=1.0
        )
        
        # Add to cache
        self.spatial_cache[cache_entry.cache_id] = cache_entry
        cache_entry.access_count += 1
        
        # Prune cache if too large
        if len(self.spatial_cache) > self.cache_max_size:
            self._prune_cache()
    
    def _get_cached_decision(self, sensor_data: Dict[str, float],
                            context: Dict[str, Any]) -> VehicleControlInput:
        """Get cached decision when AI is unavailable."""
        coord = self.lidar_engine.vehicle_state.center_coordinate
        spatial_hash = self._compute_spatial_hash(coord, sensor_data, context)
        
        # Find matching cache entry
        for cache_id, entry in self.spatial_cache.items():
            if entry.spatial_hash == spatial_hash:
                # Check if cache is still valid
                if time.time() - entry.timestamp < self.cache_ttl:
                    entry.access_count += 1
                    return entry.optimal_control
        
        # No exact match, find closest by coordinate
        closest_entry = self._find_closest_cache_entry(coord)
        if closest_entry:
            closest_entry.access_count += 1
            return closest_entry.optimal_control
        
        # No cache available, return safe default
        return VehicleControlInput(throttle=0.0, brake=0.5, steering=0.0, gear="drive")
    
    def _find_closest_cache_entry(self, coord: Coordinate) -> Optional[SpatialCacheEntry]:
        """Find closest cache entry by coordinate."""
        if not self.spatial_cache:
            return None
        
        closest_entry = None
        min_distance = float('inf')
        
        for entry in self.spatial_cache.values():
            distance = math.sqrt(
                (entry.coordinate.x_center - coord.x_center)**2 +
                (entry.coordinate.y - coord.y)**2
            )
            
            if distance < min_distance:
                min_distance = distance
                closest_entry = entry
        
        return closest_entry if min_distance < 10.0 else None  # Within 10 meters
    
    def _prune_cache(self):
        """Prune old cache entries."""
        current_time = time.time()
        
        # Remove expired entries
        expired = [
            cache_id for cache_id, entry in self.spatial_cache.items()
            if current_time - entry.timestamp > self.cache_ttl
        ]
        
        for cache_id in expired:
            del self.spatial_cache[cache_id]
        
        # If still too large, remove least accessed
        if len(self.spatial_cache) > self.cache_max_size:
            sorted_entries = sorted(
                self.spatial_cache.items(),
                key=lambda x: x[1].access_count
            )
            
            # Remove 10% of entries
            remove_count = len(self.spatial_cache) // 10
            for cache_id, _ in sorted_entries[:remove_count]:
                del self.spatial_cache[cache_id]
    
    def create_coordination_save_point(self, spatial_context: Dict[str, Any],
                                      control_state: VehicleControlInput,
                                      success_outcome: bool) -> CoordinationSavePoint:
        """
        Create save point for coordination actuation logic.
        Stores spatial context, control state, and brain state for recovery.
        """
        save_id = f"save_{int(time.time() * 1000)}"
        
        # Capture current brain state
        brain_state = {
            "avg_activation": np.mean([n.activation for n in self.brain_mesh.values()]) if self.brain_mesh else 0.0,
            "active_paths": len(self.neural_paths),
            "latched_patterns": len(self.cortex_latches)
        }
        
        save_point = CoordinationSavePoint(
            save_id=save_id,
            spatial_context=spatial_context,
            control_state=control_state,
            brain_state=brain_state,
            success_outcome=success_outcome
        )
        
        self.coordination_save_points[save_id] = save_point
        
        return save_point
    
    def restore_from_save_point(self, save_id: str) -> Optional[CoordinationSavePoint]:
        """Restore coordination state from save point."""
        if save_id in self.coordination_save_points:
            save_point = self.coordination_save_points[save_id]
            
            # Restore brain state
            for node_id, node in self.brain_mesh.items():
                if "activation" in save_point.brain_state:
                    node.activation = save_point.brain_state.get("activation", 0.0)
            
            return save_point
        
        return None
    
    def get_spatial_data(self) -> Dict[str, Any]:
        """
        Get spatial data from lidar engine and integrations.
        Provides access to spatial data like other APIs handle.
        """
        coord = self.lidar_engine.vehicle_state.center_coordinate
        
        return {
            "current_coordinate": {
                "x_center": coord.x_center,
                "x_plus": coord.x_plus,
                "x_minus": coord.x_minus,
                "y": coord.y,
                "z": coord.z
            },
            "density_at_current": self.lidar_engine._get_density_at_point(coord.x_center, coord.y),
            "anchor_points": [
                {
                    "id": anchor.id,
                    "coordinate": {
                        "x": anchor.coordinate.x_center,
                        "y": anchor.coordinate.y,
                        "z": anchor.coordinate.z
                    },
                    "heat_intensity": anchor.heat_intensity,
                    "distance": anchor.distance_from_center
                }
                for anchor in self.lidar_engine.anchors.values()
            ],
            "virtual_objects": [
                {
                    "object_id": obj.object_id,
                    "geometry_type": obj.geometry_type,
                    "vertex_count": len(obj.vertices)
                }
                for obj in self.lidar_engine.get_virtual_objects()
            ],
            "mesh_layers": self.lidar_engine.mesh_layers,
            "trajectory": [
                {
                    "x": c.x_center,
                    "y": c.y,
                    "z": c.z
                }
                for c in self.lidar_engine.trajectory[-10:]  # Last 10 points
            ]
        }
    
    def set_ai_availability(self, available: bool):
        """Set AI availability flag for fallback mode."""
        self.ai_available = available
    
    def _compute_spatial_hash(self, coord: Coordinate, sensor_data: Dict[str, float],
                             context: Dict[str, Any]) -> str:
        """Compute spatial hash for cache matching."""
        hash_data = {
            "x": round(coord.x_center, 2),
            "y": round(coord.y, 2),
            "density": round(self.lidar_engine._get_density_at_point(coord.x_center, coord.y), 2),
            **{k: round(v, 2) for k, v in sensor_data.items()},
            **{k: round(v, 2) for k, v in context.items()}
        }
        
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()
    
    def minimize_failure_rate(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze historical data to minimize failure rate.
        Identifies patterns that lead to failures and adjusts weights.
        """
        failure_patterns = []
        success_patterns = []
        
        for data in historical_data:
            if data.get("success", False):
                success_patterns.append(data)
            else:
                failure_patterns.append(data)
        
        # Analyze differences
        analysis = {
            "total_failures": len(failure_patterns),
            "total_successes": len(success_patterns),
            "failure_rate": len(failure_patterns) / len(historical_data) if historical_data else 0.0,
            "identified_patterns": []
        }
        
        # Identify common failure patterns
        if failure_patterns:
            avg_density = sum(f.get("density", 0.5) for f in failure_patterns) / len(failure_patterns)
            avg_velocity = sum(f.get("velocity", 10.0) for f in failure_patterns) / len(failure_patterns)
            
            analysis["identified_patterns"].append({
                "pattern": "high_density_high_velocity",
                "avg_density": avg_density,
                "avg_velocity": avg_velocity,
                "recommendation": "reduce velocity in high density areas"
            })
        
        # Adjust weights to avoid failure patterns
        if analysis["failure_rate"] > 0.1:
            self._adjust_weights_for_safety()
        
        return analysis
    
    def _adjust_weights_for_safety(self):
        """Adjust neural weights to prioritize safety."""
        # Increase safety path weights
        for path_id, path in self.neural_paths.items():
            if path.path_type == NeuralPathType.SAFETY:
                path.weight *= 1.1  # Increase by 10%
                path.confidence = min(1.0, path.confidence + 0.05)
            elif path.path_type == NeuralPathType.EFFICIENCY:
                path.weight *= 0.9  # Decrease by 10%
    
    def ensure_compliance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure compliance with human drivers, pedestrians, and abnormal conditions.
        """
        compliance_status = {
            "pedestrian_safe": True,
            "human_driver_safe": True,
            "abnormal_condition_handled": True,
            "recommendations": []
        }
        
        # Check for pedestrians
        if context.get("pedestrians_nearby", False):
            compliance_status["pedestrian_safe"] = False
            compliance_status["recommendations"].append("reduce_speed_for_pedestrians")
            
            # Adjust neural paths for pedestrian safety
            for path_id, path in self.neural_paths.items():
                if path.path_type == NeuralPathType.COMPLIANCE:
                    path.weight *= 1.2
        
        # Check for human drivers
        if context.get("human_drivers_nearby", False):
            compliance_status["human_driver_safe"] = False
            compliance_status["recommendations"].append("maintain_safe_distance")
        
        # Check for abnormal conditions
        if context.get("abnormal_conditions", False):
            compliance_status["abnormal_condition_handled"] = False
            compliance_status["recommendations"].append("activate_emergency_protocols")
        
        return compliance_status
    
    def _compute_pattern_hash(self, pattern: Dict[str, Any]) -> str:
        """Compute hash for pattern matching."""
        sorted_keys = sorted(pattern.keys())
        sorted_values = [pattern[k] for k in sorted_keys]
        pattern_str = json.dumps(sorted_values, sort_keys=True)
        return hashlib.sha256(pattern_str.encode()).hexdigest()
    
    def save_neural_weights(self):
        """Save neural weights to JSON file."""
        data = {
            "neural_weights": {
                weight_id: {
                    "layer_id": w.layer_id,
                    "neuron_id": w.neuron_id,
                    "weight": w.weight,
                    "bias": w.bias,
                    "importance": w.importance,
                    "last_updated": w.last_updated
                }
                for weight_id, w in self.neural_weights.items()
            },
            "neural_paths": {
                path_id: {
                    "path_type": p.path_type.value,
                    "source_neuron": p.source_neuron,
                    "target_neuron": p.target_neuron,
                    "activation_threshold": p.activation_threshold,
                    "weight": p.weight,
                    "confidence": p.confidence
                }
                for path_id, p in self.neural_paths.items()
            },
            "cortex_latches": {
                latch_id: {
                    "pattern_hash": l.pattern_hash,
                    "capability_profile": l.capability_profile,
                    "success_count": l.success_count,
                    "failure_count": l.failure_count,
                    "confidence": l.confidence
                }
                for latch_id, l in self.cortex_latches.items()
            },
            "driver_experiences": {
                exp_id: {
                    "driver_id": e.driver_id,
                    "scenario_type": e.scenario_type,
                    "success_rate": e.success_rate,
                    "comfort_score": e.comfort_score,
                    "compliance_score": e.compliance_score
                }
                for exp_id, e in self.driver_experiences.items()
            }
        }
        
        with open(self.weight_file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_neural_weights(self):
        """Load neural weights from JSON file."""
        try:
            with open(self.weight_file_path, 'r') as f:
                data = json.load(f)
            
            # Load neural weights
            for weight_id, w_data in data.get("neural_weights", {}).items():
                self.neural_weights[weight_id] = NeuralWeight(
                    layer_id=w_data["layer_id"],
                    neuron_id=w_data["neuron_id"],
                    weight=w_data["weight"],
                    bias=w_data["bias"],
                    importance=w_data.get("importance", 1.0),
                    last_updated=w_data.get("last_updated", time.time())
                )
            
            # Load neural paths
            for path_id, p_data in data.get("neural_paths", {}).items():
                self.neural_paths[path_id] = NeuralPath(
                    path_id=path_id,
                    path_type=NeuralPathType(p_data["path_type"]),
                    source_neuron=p_data["source_neuron"],
                    target_neuron=p_data["target_neuron"],
                    activation_threshold=p_data["activation_threshold"],
                    current_activation=0.0,
                    weight=p_data["weight"],
                    confidence=p_data["confidence"]
                )
            
            # Load cortex latches
            for latch_id, l_data in data.get("cortex_latches", {}).items():
                self.cortex_latches[latch_id] = CortexLatch(
                    latch_id=latch_id,
                    pattern_hash=l_data["pattern_hash"],
                    capability_profile=l_data["capability_profile"],
                    success_count=l_data["success_count"],
                    failure_count=l_data["failure_count"],
                    confidence=l_data["confidence"]
                )
            
        except FileNotFoundError:
            pass  # No existing weights file
    
    def get_brain_status(self) -> Dict[str, Any]:
        """Get current brain status."""
        return {
            "brain_mesh_nodes": len(self.brain_mesh),
            "neural_paths": len(self.neural_paths),
            "neural_weights": len(self.neural_weights),
            "cortex_latches": len(self.cortex_latches),
            "driver_experiences": len(self.driver_experiences),
            "mesh_sync_state": self.mesh_sync_state,
            "avg_activation": np.mean([n.activation for n in self.brain_mesh.values()]) if self.brain_mesh else 0.0,
            "ai_available": self.ai_available,
            "spatial_cache_size": len(self.spatial_cache),
            "coordination_save_points": len(self.coordination_save_points),
            "cache_max_size": self.cache_max_size,
            "cache_ttl": self.cache_ttl
        }
