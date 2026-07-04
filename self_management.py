"""
Self-Management System for Parameter Coordination
Receives learning hashes from virtual test layer and coordinates parameters.
"""

import json
import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from virtual_test_layer import VirtualTestLayer, LearningHash, ScenarioType
from lidar_sonar_engine import LidarSonarEngine, VehicleControlLimits


class ManagementMode(Enum):
    """Self-management modes."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    ADAPTIVE = "adaptive"


@dataclass
class ParameterSet:
    """Set of vehicle parameters."""
    parameter_id: str
    max_velocity: float
    max_acceleration: float
    max_deceleration: float
    max_steering_angle: float
    reaction_time: float
    safety_margin: float
    mode: ManagementMode
    confidence: float = 1.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class CoordinationDecision:
    """Decision from self-management system."""
    decision_id: str
    scenario_type: str
    selected_parameters: ParameterSet
    reasoning: str
    expected_success_rate: float
    timestamp: float = field(default_factory=time.time)


class SelfManagementSystem:
    """
    Self-management system for parameter coordination.
    Receives learning hashes and coordinates parameters for optimal performance.
    """
    
    def __init__(self, virtual_test_layer: VirtualTestLayer,
                 lidar_engine: LidarSonarEngine):
        self.virtual_test_layer = virtual_test_layer
        self.lidar_engine = lidar_engine
        
        # Parameter sets
        self.parameter_sets: Dict[str, ParameterSet] = {}
        self.current_parameters: Optional[ParameterSet] = None
        
        # Coordination history
        self.coordination_history: List[CoordinationDecision] = []
        
        # Management mode
        self.current_mode = ManagementMode.ADAPTIVE
        
        # Initialize default parameter sets
        self._initialize_parameter_sets()
    
    def _initialize_parameter_sets(self):
        """Initialize default parameter sets for different modes."""
        self.parameter_sets["conservative"] = ParameterSet(
            parameter_id="conservative",
            max_velocity=25.0,  # ~56 mph
            max_acceleration=3.0,
            max_deceleration=6.0,
            max_steering_angle=30.0,
            reaction_time=0.8,
            safety_margin=3.0,
            mode=ManagementMode.CONSERVATIVE,
            confidence=0.95
        )
        
        self.parameter_sets["balanced"] = ParameterSet(
            parameter_id="balanced",
            max_velocity=35.0,  # ~78 mph
            max_acceleration=4.0,
            max_deceleration=7.0,
            max_steering_angle=35.0,
            reaction_time=0.5,
            safety_margin=2.0,
            mode=ManagementMode.BALANCED,
            confidence=0.85
        )
        
        self.parameter_sets["aggressive"] = ParameterSet(
            parameter_id="aggressive",
            max_velocity=44.7,  # ~100 mph
            max_acceleration=5.0,
            max_deceleration=8.0,
            max_steering_angle=35.0,
            reaction_time=0.3,
            safety_margin=1.0,
            mode=ManagementMode.AGGRESSIVE,
            confidence=0.70
        )
        
        # Set default
        self.current_parameters = self.parameter_sets["balanced"]
    
    async def coordinate_parameters(self, scenario_type: ScenarioType,
                                   difficulty: float = 0.5) -> CoordinationDecision:
        """
        Coordinate parameters based on learning hashes and scenario.
        """
        # Get optimal parameters from learning database
        optimal_params = self.virtual_test_layer.get_optimal_parameters(
            scenario_type, difficulty
        )
        
        # Select parameter set based on scenario and learning
        selected_params = self._select_parameter_set(
            scenario_type, difficulty, optimal_params
        )
        
        # Apply parameters to vehicle controller
        self._apply_parameters(selected_params)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            scenario_type, difficulty, optimal_params, selected_params
        )
        
        # Calculate expected success rate
        expected_success = self._calculate_expected_success(
            scenario_type, difficulty, selected_params
        )
        
        decision = CoordinationDecision(
            decision_id=f"decision_{int(time.time() * 1000)}",
            scenario_type=scenario_type.value,
            selected_parameters=selected_params,
            reasoning=reasoning,
            expected_success_rate=expected_success
        )
        
        self.coordination_history.append(decision)
        
        return decision
    
    def _select_parameter_set(self, scenario_type: ScenarioType,
                             difficulty: float,
                             optimal_params: Dict[str, float]) -> ParameterSet:
        """Select appropriate parameter set based on scenario and learning."""
        # If we have learned parameters, use them
        if optimal_params:
            # Create adaptive parameter set
            adaptive_params = ParameterSet(
                parameter_id=f"adaptive_{scenario_type.value}",
                max_velocity=optimal_params.get("max_velocity", 
                                              self.parameter_sets["balanced"].max_velocity),
                max_acceleration=optimal_params.get("max_acceleration",
                                                  self.parameter_sets["balanced"].max_acceleration),
                max_deceleration=optimal_params.get("max_deceleration",
                                                  self.parameter_sets["balanced"].max_deceleration),
                max_steering_angle=optimal_params.get("max_steering_angle",
                                                     self.parameter_sets["balanced"].max_steering_angle),
                reaction_time=0.5,
                safety_margin=2.0,
                mode=ManagementMode.ADAPTIVE,
                confidence=0.90
            )
            
            self.parameter_sets[adaptive_params.parameter_id] = adaptive_params
            return adaptive_params
        
        # Otherwise, select based on scenario type and difficulty
        if difficulty > 0.8:
            return self.parameter_sets["conservative"]
        elif difficulty < 0.3:
            return self.parameter_sets["aggressive"]
        else:
            return self.parameter_sets["balanced"]
    
    def _apply_parameters(self, params: ParameterSet):
        """Apply parameters to vehicle controller."""
        self.lidar_engine.controller.limits = VehicleControlLimits(
            max_velocity=params.max_velocity,
            max_acceleration=params.max_acceleration,
            max_deceleration=params.max_deceleration,
            max_steering_angle=params.max_steering_angle
        )
        
        self.current_parameters = params
    
    def _generate_reasoning(self, scenario_type: ScenarioType,
                          difficulty: float,
                          optimal_params: Dict[str, float],
                          selected_params: ParameterSet) -> str:
        """Generate reasoning for parameter selection."""
        reasoning_parts = []
        
        # Scenario type reasoning
        reasoning_parts.append(f"Scenario: {scenario_type.value}")
        
        # Difficulty reasoning
        reasoning_parts.append(f"Difficulty: {difficulty:.1f}")
        
        # Learning-based reasoning
        if optimal_params:
            reasoning_parts.append("Using learned optimal parameters")
        else:
            reasoning_parts.append("Using default parameters for mode")
        
        # Parameter set reasoning
        reasoning_parts.append(f"Mode: {selected_params.mode.value}")
        reasoning_parts.append(f"Max velocity: {selected_params.max_velocity:.1f} m/s")
        reasoning_parts.append(f"Confidence: {selected_params.confidence:.2f}")
        
        return " | ".join(reasoning_parts)
    
    def _calculate_expected_success(self, scenario_type: ScenarioType,
                                   difficulty: float,
                                   params: ParameterSet) -> float:
        """Calculate expected success rate."""
        # Base success rate from parameter confidence
        base_success = params.confidence
        
        # Adjust based on scenario difficulty
        difficulty_factor = 1.0 - (difficulty * 0.3)
        
        # Adjust based on scenario type
        scenario_factors = {
            ScenarioType.EXTREME_WEATHER: 0.7,
            ScenarioType.MULTI_OBSTACLE: 0.75,
            ScenarioType.SENSOR_FAILURE: 0.6,
            ScenarioType.EMERGENCY_VEHICLE: 0.8,
        }
        
        scenario_factor = scenario_factors.get(scenario_type, 1.0)
        
        expected_success = base_success * difficulty_factor * scenario_factor
        
        return max(0.0, min(1.0, expected_success))
    
    def get_coordination_summary(self) -> Dict[str, Any]:
        """Get summary of coordination decisions."""
        if not self.coordination_history:
            return {"message": "No coordination decisions made yet"}
        
        recent_decisions = self.coordination_history[-10:]
        
        return {
            "total_decisions": len(self.coordination_history),
            "current_mode": self.current_mode.value,
            "current_parameters": {
                "parameter_id": self.current_parameters.parameter_id,
                "mode": self.current_parameters.mode.value,
                "max_velocity": self.current_parameters.max_velocity,
                "confidence": self.current_parameters.confidence
            },
            "recent_decisions": [
                {
                    "scenario_type": d.scenario_type,
                    "mode": d.selected_parameters.mode.value,
                    "expected_success": d.expected_success_rate,
                    "reasoning": d.reasoning
                }
                for d in recent_decisions
            ],
            "parameter_sets_count": len(self.parameter_sets)
        }
    
    def set_management_mode(self, mode: ManagementMode):
        """Set management mode."""
        self.current_mode = mode
        
        if mode.value in self.parameter_sets:
            self._apply_parameters(self.parameter_sets[mode.value])
    
    async def continuous_coordination(self, scenario_types: List[ScenarioType],
                                    interval: float = 5.0):
        """Continuously coordinate parameters for multiple scenarios."""
        while True:
            for scenario_type in scenario_types:
                decision = await self.coordinate_parameters(scenario_type, 0.5)
                print(f"[Coordination] {decision.reasoning}")
            
            await asyncio.sleep(interval)
