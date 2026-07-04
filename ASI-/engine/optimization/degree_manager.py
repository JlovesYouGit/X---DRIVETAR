"""
Degree Manager — Light-ASI LLM Gateway
Manages degree function adjustments for pipeline optimization.
Controls how degree values are adjusted based on performance metrics.
"""

import math
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("light-asi.degree_manager")


class DegreeAdjustmentType(Enum):
    """Types of degree adjustments."""
    PRECISION_INCREASE = "precision_increase"
    COMPLEXITY_REDUCTION = "complexity_reduction"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    ERROR_MITIGATION = "error_mitigation"
    FREQUENCY_ALIGNMENT = "frequency_alignment"


@dataclass
class DegreeConfig:
    """Configuration for degree function management."""
    stage_name: str
    current_degree: float
    target_degree: float
    min_degree: float
    max_degree: float
    adjustment_rate: float  # How fast to adjust (0.0-1.0)
    precision_mode: bool = False
    last_adjustment: float = field(default_factory=time.time)


@dataclass
class DegreeAdjustment:
    """Record of a degree adjustment."""
    stage_name: str
    old_degree: float
    new_degree: float
    adjustment_type: DegreeAdjustmentType
    reason: str
    expected_impact: Dict[str, float]
    timestamp: float = field(default_factory=time.time)


class DegreeManager:
    """
    Manages degree function adjustments for pipeline optimization.
    
    The degree function controls computational precision and complexity:
    - Higher degrees = more precision, higher computational cost
    - Lower degrees = faster processing, potentially less accuracy
    """
    
    def __init__(self):
        # Stage configurations
        self.stage_configs: Dict[str, DegreeConfig] = {}
        
        # Adjustment history
        self.adjustment_history: List[DegreeAdjustment] = []
        
        # Performance tracking
        self.performance_impact: Dict[str, Dict[str, float]] = {}
        
        # Initialize default configurations
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Initialize default degree configurations for common stages."""
        default_stages = [
            ("hash_pipeline", 1.0, 0.1, 2.0, 0.1),
            ("node_selection", 1.2, 0.2, 1.8, 0.15),
            ("resonance_tracking", 1.5, 0.5, 3.0, 0.2),
            ("semantic_query", 2.0, 0.8, 2.5, 0.1),
            ("cluster_management", 0.8, 0.3, 1.5, 0.12),
            ("world_ingestion", 1.1, 0.4, 2.2, 0.08)
        ]
        
        for stage_name, current, min_deg, max_deg, adj_rate in default_stages:
            self.stage_configs[stage_name] = DegreeConfig(
                stage_name=stage_name,
                current_degree=current,
                target_degree=current,
                min_degree=min_deg,
                max_degree=max_deg,
                adjustment_rate=adj_rate
            )
    
    def adjust_degree(self, stage_name: str, target_degree: float, 
                     reason: str, adjustment_type: DegreeAdjustmentType = DegreeAdjustmentType.PERFORMANCE_OPTIMIZATION) -> float:
        """
        Adjust degree for a pipeline stage.
        Returns the new degree value after adjustment.
        """
        # Get or create config
        if stage_name not in self.stage_configs:
            self._create_stage_config(stage_name, target_degree)
            
        config = self.stage_configs[stage_name]
        old_degree = config.current_degree
        
        # Validate target degree
        target_degree = max(config.min_degree, min(config.max_degree, target_degree))
        
        # Calculate gradual adjustment
        degree_diff = target_degree - config.current_degree
        adjustment_step = degree_diff * config.adjustment_rate
        
        # Apply adjustment
        new_degree = config.current_degree + adjustment_step
        new_degree = max(config.min_degree, min(config.max_degree, new_degree))
        
        # Update configuration
        config.current_degree = new_degree
        config.target_degree = target_degree
        config.last_adjustment = time.time()
        
        # Calculate expected impact
        expected_impact = self._calculate_expected_impact(stage_name, old_degree, new_degree, adjustment_type)
        
        # Record adjustment
        adjustment = DegreeAdjustment(
            stage_name=stage_name,
            old_degree=old_degree,
            new_degree=new_degree,
            adjustment_type=adjustment_type,
            reason=reason,
            expected_impact=expected_impact
        )
        
        self.adjustment_history.append(adjustment)
        
        # Keep history manageable
        if len(self.adjustment_history) > 1000:
            self.adjustment_history = self.adjustment_history[-1000:]
            
        logger.info(f"Adjusted degree for {stage_name}: {old_degree:.3f} → {new_degree:.3f} ({reason})")
        
        return new_degree
    
    def _create_stage_config(self, stage_name: str, initial_degree: float):
        """Create configuration for a new stage."""
        self.stage_configs[stage_name] = DegreeConfig(
            stage_name=stage_name,
            current_degree=initial_degree,
            target_degree=initial_degree,
            min_degree=0.1,
            max_degree=3.0,
            adjustment_rate=0.1
        )
    
    def _calculate_expected_impact(self, stage_name: str, old_degree: float, 
                                  new_degree: float, adjustment_type: DegreeAdjustmentType) -> Dict[str, float]:
        """Calculate expected performance impact of degree change."""
        
        degree_ratio = new_degree / old_degree if old_degree > 0 else 1.0
        
        # Base impact calculations
        expected_impact = {
            "computational_cost": degree_ratio ** 1.2,  # Cost increases faster than degree
            "precision": degree_ratio ** 0.8,           # Precision increases slower
            "latency": degree_ratio ** 1.1,             # Latency increases with degree
            "memory_usage": degree_ratio ** 0.9,        # Memory usage increases
            "accuracy": degree_ratio ** 0.6,            # Accuracy improvement diminishes
        }
        
        # Adjustment type specific impacts
        if adjustment_type == DegreeAdjustmentType.PRECISION_INCREASE:
            expected_impact["accuracy"] *= 1.3
            expected_impact["error_rate"] = 1.0 / (degree_ratio ** 0.7)
            
        elif adjustment_type == DegreeAdjustmentType.COMPLEXITY_REDUCTION:
            expected_impact["throughput"] = 1.0 / (degree_ratio ** 0.8)
            expected_impact["latency"] *= 0.9  # Better latency than base calculation
            
        elif adjustment_type == DegreeAdjustmentType.ERROR_MITIGATION:
            expected_impact["error_rate"] = 1.0 / (degree_ratio ** 1.2)
            expected_impact["stability"] = degree_ratio ** 0.5
            
        elif adjustment_type == DegreeAdjustmentType.FREQUENCY_ALIGNMENT:
            expected_impact["frequency_alignment"] = degree_ratio ** 0.4
            expected_impact["resonance_stability"] = degree_ratio ** 0.3
        
        return expected_impact
    
    def get_current_degree(self, stage_name: str) -> float:
        """Get current degree value for a stage."""
        if stage_name in self.stage_configs:
            return self.stage_configs[stage_name].current_degree
        return 1.0  # Default degree
    
    def get_degree_function_value(self, stage_name: str, input_value: float) -> float:
        """
        Calculate degree function output for given input.
        F(x) = x^degree for the stage.
        """
        degree = self.get_current_degree(stage_name)
        
        if input_value == 0:
            return 0.0
        elif input_value > 0:
            return input_value ** degree
        else:
            # Handle negative inputs
            return -(abs(input_value) ** degree)
    
    def optimize_degree_for_target(self, stage_name: str, target_metric: str, 
                                  target_value: float, current_value: float) -> float:
        """
        Optimize degree to achieve a target metric value.
        Returns recommended degree adjustment.
        """
        if stage_name not in self.stage_configs:
            return 1.0
            
        config = self.stage_configs[stage_name]
        current_degree = config.current_degree
        
        # Calculate required adjustment based on target metric
        if target_metric == "latency" and current_value > 0:
            # Lower degree reduces latency
            ratio = target_value / current_value
            if ratio < 1.0:  # Need to reduce latency
                degree_adjustment = ratio ** 0.9  # Gradual reduction
                new_degree = current_degree * degree_adjustment
            else:
                new_degree = current_degree
                
        elif target_metric == "throughput" and current_value > 0:
            # Lower degree can increase throughput
            ratio = target_value / current_value
            if ratio > 1.0:  # Need to increase throughput
                degree_adjustment = 1.0 / (ratio ** 0.8)
                new_degree = current_degree * degree_adjustment
            else:
                new_degree = current_degree
                
        elif target_metric == "accuracy" and current_value > 0:
            # Higher degree improves accuracy
            ratio = target_value / current_value
            if ratio > 1.0:  # Need to improve accuracy
                degree_adjustment = ratio ** 0.7
                new_degree = current_degree * degree_adjustment
            else:
                new_degree = current_degree
                
        else:
            new_degree = current_degree
            
        # Ensure within bounds
        new_degree = max(config.min_degree, min(config.max_degree, new_degree))
        
        return new_degree
    
    def get_degree_adjustment_history(self, stage_name: Optional[str] = None, 
                                     limit: int = 50) -> List[DegreeAdjustment]:
        """Get recent degree adjustment history."""
        history = self.adjustment_history
        
        if stage_name:
            history = [adj for adj in history if adj.stage_name == stage_name]
            
        return history[-limit:] if limit else history
    
    def analyze_degree_performance(self, stage_name: str) -> Dict[str, Any]:
        """Analyze performance impact of recent degree adjustments."""
        
        if stage_name not in self.stage_configs:
            return {"error": "Stage not found"}
            
        config = self.stage_configs[stage_name]
        recent_adjustments = [
            adj for adj in self.adjustment_history[-20:] 
            if adj.stage_name == stage_name
        ]
        
        analysis = {
            "stage_name": stage_name,
            "current_degree": config.current_degree,
            "target_degree": config.target_degree,
            "degree_range": (config.min_degree, config.max_degree),
            "recent_adjustments_count": len(recent_adjustments),
            "adjustment_trend": self._calculate_adjustment_trend(recent_adjustments),
            "stability_score": self._calculate_stability_score(recent_adjustments),
            "performance_correlation": self._analyze_performance_correlation(stage_name)
        }
        
        if recent_adjustments:
            analysis["last_adjustment"] = {
                "timestamp": recent_adjustments[-1].timestamp,
                "type": recent_adjustments[-1].adjustment_type.value,
                "reason": recent_adjustments[-1].reason,
                "degree_change": recent_adjustments[-1].new_degree - recent_adjustments[-1].old_degree
            }
            
        return analysis
    
    def _calculate_adjustment_trend(self, adjustments: List[DegreeAdjustment]) -> str:
        """Calculate trend in degree adjustments."""
        if len(adjustments) < 3:
            return "insufficient_data"
            
        degree_changes = [
            adj.new_degree - adj.old_degree 
            for adj in adjustments
        ]
        
        avg_change = sum(degree_changes) / len(degree_changes)
        
        if avg_change > 0.05:
            return "increasing"
        elif avg_change < -0.05:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_stability_score(self, adjustments: List[DegreeAdjustment]) -> float:
        """Calculate stability score based on adjustment frequency and magnitude."""
        if not adjustments:
            return 1.0
            
        # Calculate adjustment frequency
        if len(adjustments) > 1:
            time_span = adjustments[-1].timestamp - adjustments[0].timestamp
            frequency = len(adjustments) / max(time_span, 1.0)  # adjustments per second
        else:
            frequency = 0.0
            
        # Calculate adjustment magnitude variance
        degree_changes = [abs(adj.new_degree - adj.old_degree) for adj in adjustments]
        avg_change = sum(degree_changes) / len(degree_changes)
        variance = sum((change - avg_change) ** 2 for change in degree_changes) / len(degree_changes)
        
        # Stability decreases with high frequency and high variance
        stability = 1.0 / (1.0 + frequency * 10 + variance * 5)
        
        return max(0.0, min(1.0, stability))
    
    def _analyze_performance_correlation(self, stage_name: str) -> Dict[str, float]:
        """Analyze correlation between degree adjustments and performance."""
        
        # This would require performance data correlation
        # For now, return placeholder analysis
        return {
            "latency_correlation": -0.7,  # Higher degree typically increases latency
            "accuracy_correlation": 0.6,   # Higher degree typically improves accuracy
            "throughput_correlation": -0.5, # Higher degree typically reduces throughput
            "error_rate_correlation": -0.4  # Higher degree typically reduces errors
        }
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get current degree manager status."""
        return {
            "stages_managed": len(self.stage_configs),
            "total_adjustments": len(self.adjustment_history),
            "stage_configs": {
                name: {
                    "current_degree": config.current_degree,
                    "target_degree": config.target_degree,
                    "range": (config.min_degree, config.max_degree),
                    "last_adjustment": config.last_adjustment
                }
                for name, config in self.stage_configs.items()
            },
            "recent_activity": len([
                adj for adj in self.adjustment_history
                if time.time() - adj.timestamp < 300  # Last 5 minutes
            ])
        }