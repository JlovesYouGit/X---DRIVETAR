"""
Virtual Test Layer for Vehicle Testing
Tests vehicle based on map endpoint routes to achieve perfect score without conflict.
Uses chaotic conditional scenarios and learning hash system for recalibration.
"""

import json
import math
import time
import random
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from lidar_sonar_engine import (
    LidarSonarEngine, Coordinate, VehicleControlInput, 
    VehicleControlLimits, TeslaRouteSegment
)


class ScenarioType(Enum):
    """Types of chaotic scenarios for testing."""
    TRAFFIC_JAM = "traffic_jam"
    SUDDEN_OBSTACLE = "sudden_obstacle"
    WEATHER_CONDITION = "weather_condition"
    ROAD_CONSTRUCTION = "road_construction"
    PEDESTRIAN_CROSSING = "pedestrian_crossing"
    EMERGENCY_VEHICLE = "emergency_vehicle"
    SENSOR_FAILURE = "sensor_failure"
    GPS_DRIFT = "gps_drift"
    MULTI_OBSTACLE = "multi_obstacle"
    EXTREME_WEATHER = "extreme_weather"


@dataclass
class TestScenario:
    """Chaotic test scenario."""
    scenario_id: str
    scenario_type: ScenarioType
    start_coordinate: Coordinate
    end_coordinate: Coordinate
    difficulty: float  # 0.0 to 1.0
    obstacles: List[Dict[str, Any]] = field(default_factory=list)
    weather_conditions: Dict[str, float] = field(default_factory=dict)
    traffic_density: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of virtual test."""
    test_id: str
    scenario_id: str
    success: bool
    score: float  # 0.0 to 1.0
    time_elapsed: float
    conflicts_encountered: int
    distance_traveled: float
    final_coordinate: Coordinate
    control_inputs: List[VehicleControlInput] = field(default_factory=list)
    learning_hash: str = ""
    recalibration_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class LearningHash:
    """Learning hash for parameter recalibration."""
    hash_id: str
    scenario_type: ScenarioType
    success_rate: float
    avg_score: float
    optimal_parameters: Dict[str, float]
    failure_patterns: List[str] = field(default_factory=list)
    recalibration_count: int = 0
    last_updated: float = field(default_factory=time.time)


class VirtualTestLayer:
    """
    Virtual test layer for vehicle testing.
    Tests vehicle through chaotic scenarios and learns from results.
    """
    
    def __init__(self, lidar_engine: LidarSonarEngine, 
                 learning_db_path: str = "learning_hashes.json"):
        self.lidar_engine = lidar_engine
        self.learning_db_path = learning_db_path
        
        # Test scenarios
        self.scenarios: Dict[str, TestScenario] = {}
        self.test_results: List[TestResult] = []
        
        # Learning database
        self.learning_hashes: Dict[str, LearningHash] = {}
        self.load_learning_database()
        
        # Real-world scenario templates
        self.scenario_templates = self._initialize_scenario_templates()
        
        # Perfect score threshold
        self.perfect_score_threshold = 0.95
        
    def _initialize_scenario_templates(self) -> Dict[ScenarioType, Dict]:
        """Initialize real-world scenario templates."""
        return {
            ScenarioType.TRAFFIC_JAM: {
                "traffic_density": 0.9,
                "obstacle_count": 5,
                "speed_limit_reduction": 0.5
            },
            ScenarioType.SUDDEN_OBSTACLE: {
                "obstacle_count": 1,
                "obstacle_distance": 20.0,
                "reaction_time_required": 0.5
            },
            ScenarioType.WEATHER_CONDITION: {
                "visibility": 0.6,
                "road_friction": 0.7,
                "wind_effect": 0.3
            },
            ScenarioType.ROAD_CONSTRUCTION: {
                "lane_closure": True,
                "detour_required": True,
                "narrow_passage": True
            },
            ScenarioType.PEDESTRIAN_CROSSING: {
                "pedestrian_count": 3,
                "crossing_frequency": 0.8,
                "unexpected_movement": True
            },
            ScenarioType.EMERGENCY_VEHICLE: {
                "priority_override": True,
                "yield_required": True,
                "siren_active": True
            },
            ScenarioType.SENSOR_FAILURE: {
                "sensor_reliability": 0.7,
                "backup_required": True,
                "degraded_mode": True
            },
            ScenarioType.GPS_DRIFT: {
                "position_error": 5.0,
                "heading_error": 10.0,
                "recalibration_needed": True
            },
            ScenarioType.MULTI_OBSTACLE: {
                "obstacle_count": 8,
                "obstacle_types": ["static", "dynamic", "moving"],
                "complex_navigation": True
            },
            ScenarioType.EXTREME_WEATHER: {
                "visibility": 0.3,
                "road_friction": 0.4,
                "wind_effect": 0.7,
                "hazardous_conditions": True
            }
        }
    
    def create_chaotic_scenario(self, scenario_type: ScenarioType,
                               start: Coordinate, end: Coordinate,
                               difficulty: float = 0.7) -> TestScenario:
        """Create a chaotic test scenario."""
        scenario_id = f"scenario_{int(time.time() * 1000)}"
        
        template = self.scenario_templates.get(scenario_type, {})
        
        # Generate obstacles based on scenario type
        obstacles = self._generate_obstacles(scenario_type, start, end, template)
        
        # Generate weather conditions
        weather = self._generate_weather_conditions(scenario_type, template)
        
        scenario = TestScenario(
            scenario_id=scenario_id,
            scenario_type=scenario_type,
            start_coordinate=start,
            end_coordinate=end,
            difficulty=difficulty,
            obstacles=obstacles,
            weather_conditions=weather,
            traffic_density=template.get("traffic_density", 0.5),
            metadata=template
        )
        
        self.scenarios[scenario_id] = scenario
        return scenario
    
    def _generate_obstacles(self, scenario_type: ScenarioType, 
                           start: Coordinate, end: Coordinate,
                           template: Dict) -> List[Dict[str, Any]]:
        """Generate obstacles for scenario."""
        obstacles = []
        obstacle_count = template.get("obstacle_count", 3)
        
        for i in range(obstacle_count):
            # Interpolate position along route
            t = (i + 1) / (obstacle_count + 1)
            x = start.x_center + (end.x_center - start.x_center) * t
            y = start.y + (end.y - start.y) * t
            
            # Add randomness
            x += random.uniform(-10, 10)
            y += random.uniform(-10, 10)
            
            obstacle = {
                "id": f"obs_{i}",
                "x": x,
                "y": y,
                "type": template.get("obstacle_types", ["static"])[i % len(template.get("obstacle_types", ["static"]))],
                "size": random.uniform(1.0, 3.0),
                "moving": scenario_type in [ScenarioType.MULTI_OBSTACLE, ScenarioType.EMERGENCY_VEHICLE]
            }
            
            obstacles.append(obstacle)
        
        return obstacles
    
    def _generate_weather_conditions(self, scenario_type: ScenarioType,
                                    template: Dict) -> Dict[str, float]:
        """Generate weather conditions for scenario."""
        if scenario_type not in [ScenarioType.WEATHER_CONDITION, ScenarioType.EXTREME_WEATHER]:
            return {"visibility": 1.0, "road_friction": 1.0, "wind_effect": 0.0}
        
        return {
            "visibility": template.get("visibility", 1.0),
            "road_friction": template.get("road_friction", 1.0),
            "wind_effect": template.get("wind_effect", 0.0)
        }
    
    async def run_virtual_test(self, scenario: TestScenario,
                              max_time: float = 60.0) -> TestResult:
        """
        Run virtual test for scenario.
        Tests if vehicle can achieve perfect score without conflict.
        """
        test_id = f"test_{int(time.time() * 1000)}"
        start_time = time.time()
        
        # Plan Tesla route
        path = self._generate_test_path(scenario.start_coordinate, 
                                       scenario.end_coordinate)
        route_segments = self.lidar_engine.plan_tesla_route(path)
        
        # Initialize control input
        control_input = VehicleControlInput()
        control_inputs = []
        conflicts = 0
        distance_traveled = 0.0
        
        # Simulate navigation through scenario
        current_coord = scenario.start_coordinate
        dt = 0.1  # 100ms timestep
        
        while (time.time() - start_time) < max_time:
            # Apply chaotic conditions
            control_input = self._apply_chaotic_conditions(
                control_input, scenario, current_coord
            )
            
            # Check for conflicts
            if self._check_conflict(current_coord, scenario):
                conflicts += 1
            
            # Update vehicle position
            await self.lidar_engine.update_vehicle_position_async(
                current_coord, control_input
            )
            
            control_inputs.append(control_input)
            
            # Calculate distance traveled
            distance_traveled += math.sqrt(
                (current_coord.x_center - scenario.start_coordinate.x_center)**2 +
                (current_coord.y - scenario.start_coordinate.y)**2
            )
            
            # Move to next position
            current_coord = self._move_towards_target(
                current_coord, scenario.end_coordinate, 
                control_input, scenario.weather_conditions
            )
            
            # Check if reached destination
            if self._check_arrival(current_coord, scenario.end_coordinate):
                break
            
            await asyncio.sleep(dt)
        
        time_elapsed = time.time() - start_time
        
        # Calculate score
        score = self._calculate_test_score(
            success=self._check_arrival(current_coord, scenario.end_coordinate),
            conflicts=conflicts,
            time_elapsed=time_elapsed,
            distance_traveled=distance_traveled,
            scenario=scenario
        )
        
        # Generate learning hash
        learning_hash = self._generate_learning_hash(scenario, score, control_inputs)
        
        # Recalibrate based on result
        recalibration_data = self._recalibrate_parameters(scenario, score, learning_hash)
        
        result = TestResult(
            test_id=test_id,
            scenario_id=scenario.scenario_id,
            success=score >= self.perfect_score_threshold,
            score=score,
            time_elapsed=time_elapsed,
            conflicts_encountered=conflicts,
            distance_traveled=distance_traveled,
            final_coordinate=current_coord,
            control_inputs=control_inputs,
            learning_hash=learning_hash,
            recalibration_data=recalibration_data
        )
        
        self.test_results.append(result)
        
        # Update learning database
        self._update_learning_hash(scenario, result)
        self.save_learning_database()
        
        return result
    
    def _generate_test_path(self, start: Coordinate, end: Coordinate) -> List[Coordinate]:
        """Generate test path between coordinates."""
        path = []
        
        # Create waypoints
        num_waypoints = 10
        for i in range(num_waypoints + 1):
            t = i / num_waypoints
            x = start.x_center + (end.x_center - start.x_center) * t
            y = start.y + (end.y - start.y) * t
            
            # Add slight curve for realism
            curve_offset = math.sin(t * math.pi) * 5.0
            x += curve_offset
            
            path.append(Coordinate(x, x, y, start.z))
        
        return path
    
    def _apply_chaotic_conditions(self, control_input: VehicleControlInput,
                                  scenario: TestScenario,
                                  current_coord: Coordinate) -> VehicleControlInput:
        """Apply chaotic conditions to control input."""
        # Apply weather effects
        visibility = scenario.weather_conditions.get("visibility", 1.0)
        road_friction = scenario.weather_conditions.get("road_friction", 1.0)
        wind_effect = scenario.weather_conditions.get("wind_effect", 0.0)
        
        # Reduce throttle based on visibility
        control_input.throttle *= visibility
        
        # Adjust steering based on wind
        control_input.steering += wind_effect * random.uniform(-0.1, 0.1)
        
        # Apply traffic density effects
        if scenario.traffic_density > 0.7:
            control_input.throttle *= 0.5
            control_input.brake = max(control_input.brake, 0.3)
        
        # Clamp values
        control_input.throttle = max(0.0, min(1.0, control_input.throttle))
        control_input.brake = max(0.0, min(1.0, control_input.brake))
        control_input.steering = max(-1.0, min(1.0, control_input.steering))
        
        return control_input
    
    def _check_conflict(self, coord: Coordinate, scenario: TestScenario) -> bool:
        """Check if current position conflicts with obstacles."""
        for obstacle in scenario.obstacles:
            distance = math.sqrt(
                (coord.x_center - obstacle["x"])**2 +
                (coord.y - obstacle["y"])**2
            )
            
            if distance < obstacle["size"] + 2.0:  # 2m safety margin
                return True
        
        return False
    
    def _move_towards_target(self, current: Coordinate, target: Coordinate,
                            control_input: VehicleControlInput,
                            weather: Dict[str, float]) -> Coordinate:
        """Move towards target based on control input and conditions."""
        # Calculate direction to target
        dx = target.x_center - current.x_center
        dy = target.y - current.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance < 0.1:
            return current
        
        # Normalize direction
        dx /= distance
        dy /= distance
        
        # Apply control input
        speed = control_input.throttle * 10.0  # max 10 m/s
        speed *= weather.get("road_friction", 1.0)
        
        # Apply steering
        steering_offset = control_input.steering * 5.0
        
        new_x = current.x_center + (dx * speed * 0.1) + steering_offset
        new_y = current.y + (dy * speed * 0.1)
        
        return Coordinate(new_x, new_x, new_y, current.z)
    
    def _check_arrival(self, current: Coordinate, target: Coordinate) -> bool:
        """Check if arrived at target."""
        distance = math.sqrt(
            (current.x_center - target.x_center)**2 +
            (current.y - target.y)**2
        )
        return distance < 2.0  # Within 2 meters
    
    def _calculate_test_score(self, success: bool, conflicts: int,
                             time_elapsed: float, distance_traveled: float,
                             scenario: TestScenario) -> float:
        """Calculate test score (0.0 to 1.0)."""
        # Base score from success
        score = 1.0 if success else 0.5
        
        # Penalty for conflicts
        conflict_penalty = conflicts * 0.1
        score -= conflict_penalty
        
        # Penalty for time
        expected_time = 30.0  # 30 seconds expected
        time_penalty = max(0, (time_elapsed - expected_time) / expected_time) * 0.2
        score -= time_penalty
        
        # Bonus for difficulty
        score += scenario.difficulty * 0.1
        
        # Clamp to valid range
        return max(0.0, min(1.0, score))
    
    def _generate_learning_hash(self, scenario: TestScenario, score: float,
                               control_inputs: List[VehicleControlInput]) -> str:
        """Generate learning hash from test results."""
        import hashlib
        
        # Create hash from scenario and results
        hash_data = {
            "scenario_type": scenario.scenario_type.value,
            "difficulty": scenario.difficulty,
            "score": score,
            "avg_throttle": sum(c.throttle for c in control_inputs) / len(control_inputs) if control_inputs else 0,
            "avg_brake": sum(c.brake for c in control_inputs) / len(control_inputs) if control_inputs else 0,
            "avg_steering": sum(c.steering for c in control_inputs) / len(control_inputs) if control_inputs else 0,
        }
        
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()[:16]
    
    def _recalibrate_parameters(self, scenario: TestScenario, score: float,
                                learning_hash: str) -> Dict[str, Any]:
        """Recalibrate parameters based on test result."""
        recalibration = {
            "scenario_type": scenario.scenario_type.value,
            "original_score": score,
            "learning_hash": learning_hash,
            "parameter_adjustments": {}
        }
        
        # Adjust control limits based on performance
        if score < self.perfect_score_threshold:
            # Reduce max velocity for difficult scenarios
            if scenario.scenario_type in [ScenarioType.EXTREME_WEATHER, ScenarioType.MULTI_OBSTACLE]:
                recalibration["parameter_adjustments"]["max_velocity"] = \
                    self.lidar_engine.controller.limits.max_velocity * 0.8
            
            # Increase steering sensitivity for obstacle avoidance
            if scenario.scenario_type in [ScenarioType.SUDDEN_OBSTACLE, ScenarioType.PEDESTRIAN_CROSSING]:
                recalibration["parameter_adjustments"]["max_steering_angle"] = \
                    self.lidar_engine.controller.limits.max_steering_angle * 1.1
        
        return recalibration
    
    def _update_learning_hash(self, scenario: TestScenario, result: TestResult):
        """Update learning hash database."""
        hash_key = f"{scenario.scenario_type.value}_{scenario.difficulty:.1f}"
        
        if hash_key not in self.learning_hashes:
            self.learning_hashes[hash_key] = LearningHash(
                hash_id=hash_key,
                scenario_type=scenario.scenario_type,
                success_rate=1.0 if result.success else 0.0,
                avg_score=result.score,
                optimal_parameters=result.recalibration_data.get("parameter_adjustments", {}),
                last_updated=time.time()
            )
        else:
            learning_hash = self.learning_hashes[hash_key]
            
            # Update running averages
            n = learning_hash.recalibration_count + 1
            learning_hash.success_rate = (
                (learning_hash.success_rate * learning_hash.recalibration_count + 
                 (1.0 if result.success else 0.0)) / n
            )
            learning_hash.avg_score = (
                (learning_hash.avg_score * learning_hash.recalibration_count + 
                 result.score) / n
            )
            learning_hash.recalibration_count = n
            learning_hash.last_updated = time.time()
            
            # Update optimal parameters if this was a better result
            if result.score > learning_hash.avg_score:
                learning_hash.optimal_parameters = result.recalibration_data.get("parameter_adjustments", {})
            
            # Track failure patterns
            if not result.success:
                failure_pattern = f"conflicts_{result.conflicts_encountered}_score_{result.score:.2f}"
                if failure_pattern not in learning_hash.failure_patterns:
                    learning_hash.failure_patterns.append(failure_pattern)
    
    def save_learning_database(self):
        """Save learning database to JSON."""
        data = {
            "learning_hashes": {
                key: {
                    "hash_id": lh.hash_id,
                    "scenario_type": lh.scenario_type.value,
                    "success_rate": lh.success_rate,
                    "avg_score": lh.avg_score,
                    "optimal_parameters": lh.optimal_parameters,
                    "failure_patterns": lh.failure_patterns,
                    "recalibration_count": lh.recalibration_count,
                    "last_updated": lh.last_updated
                }
                for key, lh in self.learning_hashes.items()
            },
            "test_results": [
                {
                    "test_id": tr.test_id,
                    "scenario_id": tr.scenario_id,
                    "success": tr.success,
                    "score": tr.score,
                    "time_elapsed": tr.time_elapsed,
                    "conflicts_encountered": tr.conflicts_encountered,
                    "distance_traveled": tr.distance_traveled,
                    "learning_hash": tr.learning_hash,
                    "recalibration_data": tr.recalibration_data,
                    "timestamp": tr.timestamp
                }
                for tr in self.test_results[-100:]  # Keep last 100 results
            ]
        }
        
        with open(self.learning_db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_learning_database(self):
        """Load learning database from JSON."""
        try:
            with open(self.learning_db_path, 'r') as f:
                data = json.load(f)
            
            for key, lh_data in data.get("learning_hashes", {}).items():
                self.learning_hashes[key] = LearningHash(
                    hash_id=lh_data["hash_id"],
                    scenario_type=ScenarioType(lh_data["scenario_type"]),
                    success_rate=lh_data["success_rate"],
                    avg_score=lh_data["avg_score"],
                    optimal_parameters=lh_data["optimal_parameters"],
                    failure_patterns=lh_data["failure_patterns"],
                    recalibration_count=lh_data["recalibration_count"],
                    last_updated=lh_data["last_updated"]
                )
        except FileNotFoundError:
            pass  # No existing database
    
    def get_optimal_parameters(self, scenario_type: ScenarioType,
                              difficulty: float) -> Dict[str, float]:
        """Get optimal parameters for scenario type and difficulty."""
        hash_key = f"{scenario_type.value}_{difficulty:.1f}"
        
        if hash_key in self.learning_hashes:
            return self.learning_hashes[hash_key].optimal_parameters
        
        return {}
    
    def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive test suite with all scenario types."""
        results = {}
        
        start = Coordinate(0.0, 0.0, 0.0, 0.0)
        end = Coordinate(100.0, 100.0, 0.0, 0.0)
        
        for scenario_type in ScenarioType:
            scenario = self.create_chaotic_scenario(
                scenario_type, start, end, difficulty=0.7
            )
            
            # Run test (synchronous wrapper for async)
            result = asyncio.run(self.run_virtual_test(scenario))
            
            results[scenario_type.value] = {
                "success": result.success,
                "score": result.score,
                "conflicts": result.conflicts_encountered,
                "time_elapsed": result.time_elapsed
            }
        
        return results
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of all test results."""
        if not self.test_results:
            return {"message": "No tests run yet"}
        
        successful = sum(1 for tr in self.test_results if tr.success)
        total = len(self.test_results)
        avg_score = sum(tr.score for tr in self.test_results) / total
        avg_conflicts = sum(tr.conflicts_encountered for tr in self.test_results) / total
        
        return {
            "total_tests": total,
            "successful_tests": successful,
            "success_rate": successful / total,
            "average_score": avg_score,
            "average_conflicts": avg_conflicts,
            "perfect_scores": sum(1 for tr in self.test_results if tr.score >= self.perfect_score_threshold),
            "learning_hashes_count": len(self.learning_hashes)
        }
