"""
Auto Pipeline Optimizer — Light-ASI LLM Gateway
Manages frequency-based optimization, token metrics analysis, and auto-adjusts pipeline performance.
Resolves failure rates through intelligent frequency modulation and degree function calibration.
"""

import math
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import numpy as np

from engine.core.constants import TIMING_SLA_MS, RESONANCE_BASE
from engine.core.timing import enforce_sla
from .degree_manager import DegreeManager
from .frequency_controller import FrequencyController

logger = logging.getLogger("light-asi.optimization")


@dataclass
class PipelineMetrics:
    """Pipeline performance metrics for optimization."""
    stage_name: str
    throughput: float  # items/sec
    latency: float    # ms
    error_rate: float # 0.0-1.0
    token_consumption: float  # tokens/sec
    frequency: float  # Hz
    degree_value: float  # current degree setting
    timestamp: float = field(default_factory=time.time)


@dataclass 
class OptimizationTarget:
    """Optimization targets for pipeline stages."""
    min_throughput: float
    max_latency: float
    max_error_rate: float
    token_budget: float
    preferred_frequency: float
    degree_range: Tuple[float, float]  # (min, max)


class AutoPipelineOptimizer:
    """
    Auto-pipeline optimizer that manages frequency based on token metrics and consumption rates.
    Automatically adjusts degree functions and optimizes pipeline failure rates.
    """
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        
        # Metrics tracking
        self.metrics_history: deque = deque(maxlen=history_size)
        self.stage_metrics: Dict[str, List[PipelineMetrics]] = {}
        
        # Optimization components
        self.degree_manager = DegreeManager()
        self.frequency_controller = FrequencyController()
        
        # Optimization targets per stage
        self.optimization_targets: Dict[str, OptimizationTarget] = {
            "hash_pipeline": OptimizationTarget(
                min_throughput=100.0,    # operations/sec
                max_latency=150.0,       # ms (from TIMING_SLA_MS)
                max_error_rate=0.01,     # 1%
                token_budget=1000.0,     # tokens/sec
                preferred_frequency=50.0, # Hz
                degree_range=(0.1, 2.0)
            ),
            "node_selection": OptimizationTarget(
                min_throughput=200.0,
                max_latency=150.0,
                max_error_rate=0.005,
                token_budget=800.0,
                preferred_frequency=100.0,
                degree_range=(0.2, 1.5)
            ),
            "resonance_tracking": OptimizationTarget(
                min_throughput=50.0,
                max_latency=300.0,
                max_error_rate=0.02,
                token_budget=500.0,
                preferred_frequency=25.0,
                degree_range=(0.5, 3.0)
            ),
            "semantic_query": OptimizationTarget(
                min_throughput=20.0,
                max_latency=2500.0,
                max_error_rate=0.005,
                token_budget=2000.0,
                preferred_frequency=10.0,
                degree_range=(0.8, 2.5)
            )
        }
        
        # Auto-optimization state
        self.optimization_enabled = True
        self.last_optimization: float = 0.0
        self.optimization_interval = 5.0  # seconds
        
        # Failure analysis
        self.failure_patterns: Dict[str, Any] = {}
        self.consecutive_failures: Dict[str, int] = {}
        
        # Performance baselines
        self.baseline_metrics: Dict[str, PipelineMetrics] = {}
        self.performance_trend: Dict[str, str] = {}  # "improving", "degrading", "stable"
        
    @enforce_sla("optimization_cycle", raise_on_violation=False)
    def optimize_pipeline(self, current_metrics: Dict[str, PipelineMetrics]) -> Dict[str, Any]:
        """
        Main optimization cycle - analyzes metrics and auto-adjusts pipeline parameters.
        Returns optimization decisions and new parameter settings.
        """
        optimization_results = {
            "timestamp": time.time(),
            "optimizations": {},
            "degree_adjustments": {},
            "frequency_adjustments": {},
            "failure_mitigations": {},
            "performance_predictions": {}
        }
        
        # Update metrics tracking
        for stage_name, metrics in current_metrics.items():
            self._record_stage_metrics(stage_name, metrics)
            
        # Check if optimization is needed
        if not self._should_optimize():
            optimization_results["status"] = "skipped_interval"
            return optimization_results
            
        logger.info("Starting auto-pipeline optimization cycle...")
        
        # Analyze each pipeline stage
        for stage_name, metrics in current_metrics.items():
            stage_optimization = self._optimize_stage(stage_name, metrics)
            optimization_results["optimizations"][stage_name] = stage_optimization
            
            # Apply degree adjustments
            if stage_optimization["degree_adjustment"]:
                new_degree = self.degree_manager.adjust_degree(
                    stage_name, 
                    stage_optimization["degree_adjustment"]["target_degree"],
                    stage_optimization["degree_adjustment"]["adjustment_reason"]
                )
                optimization_results["degree_adjustments"][stage_name] = new_degree
                
            # Apply frequency adjustments  
            if stage_optimization["frequency_adjustment"]:
                new_frequency = self.frequency_controller.adjust_frequency(
                    stage_name,
                    stage_optimization["frequency_adjustment"]["target_frequency"],
                    stage_optimization["frequency_adjustment"]["adjustment_type"]
                )
                optimization_results["frequency_adjustments"][stage_name] = new_frequency
                
        # Analyze failure patterns
        failure_analysis = self._analyze_failure_patterns(current_metrics)
        optimization_results["failure_mitigations"] = failure_analysis
        
        # Predict performance trends
        performance_predictions = self._predict_performance_trends()
        optimization_results["performance_predictions"] = performance_predictions
        
        self.last_optimization = time.time()
        
        logger.info(f"Pipeline optimization completed: {len(optimization_results['optimizations'])} stages optimized")
        return optimization_results
    
    def _optimize_stage(self, stage_name: str, metrics: PipelineMetrics) -> Dict[str, Any]:
        """Optimize a specific pipeline stage based on its metrics."""
        
        target = self.optimization_targets.get(stage_name)
        if not target:
            return {"status": "no_target_defined"}
            
        optimization = {
            "stage": stage_name,
            "current_performance": self._evaluate_performance(metrics, target),
            "degree_adjustment": None,
            "frequency_adjustment": None,
            "token_optimization": None,
            "recommendations": []
        }
        
        # Check performance against targets
        performance = optimization["current_performance"]
        
        # Throughput optimization
        if performance["throughput_ratio"] < 0.8:  # Below 80% of target
            # Increase frequency to boost throughput
            freq_increase = min(1.5, 1.0 / performance["throughput_ratio"])
            new_frequency = metrics.frequency * freq_increase
            new_frequency = min(new_frequency, target.preferred_frequency * 2.0)
            
            optimization["frequency_adjustment"] = {
                "target_frequency": new_frequency,
                "adjustment_type": "throughput_boost",
                "reason": f"Throughput {performance['throughput_ratio']:.2f} below target"
            }
            
        # Latency optimization  
        if performance["latency_ratio"] > 1.2:  # 20% above target
            # Adjust degree to reduce computational complexity
            degree_reduction = 0.9
            current_degree = self.degree_manager.get_current_degree(stage_name)
            new_degree = max(target.degree_range[0], current_degree * degree_reduction)
            
            optimization["degree_adjustment"] = {
                "target_degree": new_degree, 
                "adjustment_reason": f"Latency {performance['latency_ratio']:.2f}x above target",
                "adjustment_type": "complexity_reduction"
            }
            
        # Error rate mitigation
        if performance["error_ratio"] > 1.0:  # Above acceptable error rate
            # Reduce frequency and increase degree precision
            freq_reduction = 0.8
            degree_increase = 1.1
            
            current_degree = self.degree_manager.get_current_degree(stage_name)
            new_degree = min(target.degree_range[1], current_degree * degree_increase)
            new_frequency = metrics.frequency * freq_reduction
            
            optimization["frequency_adjustment"] = {
                "target_frequency": new_frequency,
                "adjustment_type": "error_mitigation",
                "reason": f"Error rate {performance['error_ratio']:.2f}x above target"
            }
            
            optimization["degree_adjustment"] = {
                "target_degree": new_degree,
                "adjustment_reason": "Increase precision to reduce errors", 
                "adjustment_type": "precision_increase"
            }
            
        # Token consumption optimization
        if performance["token_ratio"] > 1.1:  # 10% above budget
            token_optimization = self._optimize_token_consumption(stage_name, metrics, target)
            optimization["token_optimization"] = token_optimization
            
            # May need frequency reduction
            if not optimization["frequency_adjustment"]:
                freq_reduction = 1.0 / performance["token_ratio"]
                new_frequency = metrics.frequency * freq_reduction
                
                optimization["frequency_adjustment"] = {
                    "target_frequency": new_frequency,
                    "adjustment_type": "token_conservation", 
                    "reason": f"Token consumption {performance['token_ratio']:.2f}x above budget"
                }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(stage_name, metrics, target, performance)
        optimization["recommendations"] = recommendations
        
        return optimization
    
    def _evaluate_performance(self, metrics: PipelineMetrics, target: OptimizationTarget) -> Dict[str, float]:
        """Evaluate current performance against targets."""
        return {
            "throughput_ratio": metrics.throughput / target.min_throughput,
            "latency_ratio": metrics.latency / target.max_latency,
            "error_ratio": metrics.error_rate / target.max_error_rate,
            "token_ratio": metrics.token_consumption / target.token_budget,
            "frequency_ratio": metrics.frequency / target.preferred_frequency
        }
    
    def _optimize_token_consumption(self, stage_name: str, metrics: PipelineMetrics, 
                                   target: OptimizationTarget) -> Dict[str, Any]:
        """Optimize token consumption for a stage."""
        
        current_consumption = metrics.token_consumption
        target_consumption = target.token_budget
        overuse_ratio = current_consumption / target_consumption
        
        optimization = {
            "current_consumption": current_consumption,
            "target_consumption": target_consumption,
            "overuse_ratio": overuse_ratio,
            "optimization_strategy": None
        }
        
        if overuse_ratio > 1.1:  # 10% over budget
            if overuse_ratio < 1.3:  # Mild overuse
                optimization["optimization_strategy"] = {
                    "type": "frequency_reduction",
                    "reduction_factor": 1.0 / overuse_ratio,
                    "expected_savings": current_consumption * (1.0 - 1.0/overuse_ratio)
                }
            else:  # Severe overuse
                optimization["optimization_strategy"] = {
                    "type": "combined_optimization",
                    "frequency_reduction": 0.7,
                    "degree_optimization": True,
                    "caching_enhancement": True,
                    "expected_savings": current_consumption * 0.4
                }
                
        return optimization
    
    def _analyze_failure_patterns(self, current_metrics: Dict[str, PipelineMetrics]) -> Dict[str, Any]:
        """Analyze failure patterns to identify root causes and mitigation strategies."""
        
        analysis = {
            "timestamp": time.time(),
            "patterns_detected": [],
            "mitigation_strategies": {},
            "failure_correlations": {}
        }
        
        # Check for high error rate correlations
        high_error_stages = [
            name for name, metrics in current_metrics.items() 
            if metrics.error_rate > 0.02  # 2% error rate
        ]
        
        if high_error_stages:
            analysis["patterns_detected"].append({
                "pattern": "high_error_rate_cluster",
                "affected_stages": high_error_stages,
                "severity": "medium" if len(high_error_stages) < 3 else "high"
            })
            
        # Check for latency spikes
        high_latency_stages = [
            name for name, metrics in current_metrics.items()
            if metrics.latency > self.optimization_targets.get(name, {}).get("max_latency", 1000) * 1.5
        ]
        
        if high_latency_stages:
            analysis["patterns_detected"].append({
                "pattern": "latency_spike_cluster", 
                "affected_stages": high_latency_stages,
                "severity": "high"
            })
            
        # Generate mitigation strategies
        for stage_name in set(high_error_stages + high_latency_stages):
            analysis["mitigation_strategies"][stage_name] = self._generate_failure_mitigation(
                stage_name, current_metrics[stage_name]
            )
            
        return analysis
    
    def _generate_failure_mitigation(self, stage_name: str, metrics: PipelineMetrics) -> Dict[str, Any]:
        """Generate specific failure mitigation strategy for a stage."""
        
        mitigation = {
            "stage": stage_name,
            "primary_issue": None,
            "mitigation_actions": [],
            "expected_improvement": {}
        }
        
        target = self.optimization_targets.get(stage_name)
        if not target:
            return mitigation
            
        # Identify primary issue
        if metrics.error_rate > target.max_error_rate:
            mitigation["primary_issue"] = "error_rate"
            mitigation["mitigation_actions"].extend([
                {
                    "action": "reduce_frequency",
                    "parameter": "frequency",
                    "adjustment": 0.8,
                    "reason": "Lower frequency reduces computational stress"
                },
                {
                    "action": "increase_degree_precision",
                    "parameter": "degree", 
                    "adjustment": 1.2,
                    "reason": "Higher precision reduces calculation errors"
                }
            ])
            
        if metrics.latency > target.max_latency:
            mitigation["primary_issue"] = "latency"
            mitigation["mitigation_actions"].extend([
                {
                    "action": "optimize_degree_function",
                    "parameter": "degree",
                    "adjustment": 0.9,
                    "reason": "Reduce computational complexity"
                },
                {
                    "action": "enable_caching",
                    "parameter": "cache_size",
                    "adjustment": 1000,
                    "reason": "Cache frequent calculations"
                }
            ])
            
        # Predict improvement
        mitigation["expected_improvement"] = {
            "error_rate_reduction": 0.3,
            "latency_reduction": 0.2,
            "throughput_increase": 0.15
        }
        
        return mitigation
    
    def _predict_performance_trends(self) -> Dict[str, Any]:
        """Predict performance trends based on historical data."""
        
        predictions = {
            "timestamp": time.time(),
            "trends": {},
            "forecasts": {},
            "recommendations": []
        }
        
        for stage_name, metrics_list in self.stage_metrics.items():
            if len(metrics_list) < 10:  # Need sufficient data
                continue
                
            # Analyze trends
            recent_metrics = metrics_list[-10:]
            trend_analysis = self._analyze_trend(recent_metrics)
            predictions["trends"][stage_name] = trend_analysis
            
            # Generate forecast
            forecast = self._generate_forecast(stage_name, recent_metrics)
            predictions["forecasts"][stage_name] = forecast
            
        return predictions
    
    def _analyze_trend(self, metrics_list: List[PipelineMetrics]) -> Dict[str, Any]:
        """Analyze performance trend from metrics history."""
        
        if len(metrics_list) < 3:
            return {"trend": "insufficient_data"}
            
        # Calculate moving averages
        latencies = [m.latency for m in metrics_list]
        throughputs = [m.throughput for m in metrics_list] 
        error_rates = [m.error_rate for m in metrics_list]
        
        # Simple linear trend analysis
        n = len(metrics_list)
        x = np.arange(n)
        
        latency_trend = np.polyfit(x, latencies, 1)[0]  # slope
        throughput_trend = np.polyfit(x, throughputs, 1)[0]
        error_trend = np.polyfit(x, error_rates, 1)[0]
        
        return {
            "latency_trend": "improving" if latency_trend < -0.1 else "degrading" if latency_trend > 0.1 else "stable",
            "throughput_trend": "improving" if throughput_trend > 0.1 else "degrading" if throughput_trend < -0.1 else "stable", 
            "error_trend": "improving" if error_trend < -0.001 else "degrading" if error_trend > 0.001 else "stable",
            "overall_trend": self._determine_overall_trend(latency_trend, throughput_trend, error_trend)
        }
    
    def _determine_overall_trend(self, latency_trend: float, throughput_trend: float, error_trend: float) -> str:
        """Determine overall performance trend."""
        
        score = 0
        
        # Latency: lower is better
        if latency_trend < -0.1:
            score += 1
        elif latency_trend > 0.1:
            score -= 1
            
        # Throughput: higher is better
        if throughput_trend > 0.1:
            score += 1
        elif throughput_trend < -0.1:
            score -= 1
            
        # Error rate: lower is better
        if error_trend < -0.001:
            score += 1
        elif error_trend > 0.001:
            score -= 1
            
        if score > 0:
            return "improving"
        elif score < 0:
            return "degrading"
        else:
            return "stable"
    
    def _generate_forecast(self, stage_name: str, recent_metrics: List[PipelineMetrics]) -> Dict[str, Any]:
        """Generate performance forecast for next optimization cycle."""
        
        if len(recent_metrics) < 5:
            return {"forecast": "insufficient_data"}
            
        # Simple linear extrapolation
        current = recent_metrics[-1]
        
        # Calculate rates of change
        latency_rate = (recent_metrics[-1].latency - recent_metrics[-5].latency) / 4
        throughput_rate = (recent_metrics[-1].throughput - recent_metrics[-5].throughput) / 4
        error_rate_change = (recent_metrics[-1].error_rate - recent_metrics[-5].error_rate) / 4
        
        # Project forward
        forecast_time = self.optimization_interval  # seconds
        
        return {
            "projected_latency": current.latency + latency_rate * forecast_time,
            "projected_throughput": current.throughput + throughput_rate * forecast_time,
            "projected_error_rate": max(0, current.error_rate + error_rate_change * forecast_time),
            "confidence": min(0.9, len(recent_metrics) / 10.0),  # Higher confidence with more data
            "forecast_horizon": forecast_time
        }
    
    def _generate_recommendations(self, stage_name: str, metrics: PipelineMetrics, 
                                 target: OptimizationTarget, performance: Dict[str, float]) -> List[str]:
        """Generate optimization recommendations."""
        
        recommendations = []
        
        if performance["throughput_ratio"] < 0.7:
            recommendations.append(f"Consider increasing frequency from {metrics.frequency:.1f}Hz to boost throughput")
            
        if performance["latency_ratio"] > 1.5:
            recommendations.append(f"Reduce degree complexity from {metrics.degree_value:.2f} to improve latency")
            
        if performance["error_ratio"] > 1.0:
            recommendations.append("Enable additional error checking and reduce processing frequency")
            
        if performance["token_ratio"] > 1.2:
            recommendations.append("Implement token consumption caching and optimize batch processing")
            
        if not recommendations:
            recommendations.append("Performance within acceptable parameters - maintain current settings")
            
        return recommendations
    
    def _should_optimize(self) -> bool:
        """Check if optimization cycle should run."""
        current_time = time.time()
        return (
            self.optimization_enabled and 
            (current_time - self.last_optimization) >= self.optimization_interval
        )
    
    def _record_stage_metrics(self, stage_name: str, metrics: PipelineMetrics):
        """Record metrics for a specific stage."""
        if stage_name not in self.stage_metrics:
            self.stage_metrics[stage_name] = []
            
        self.stage_metrics[stage_name].append(metrics)
        
        # Keep only recent metrics
        if len(self.stage_metrics[stage_name]) > 100:
            self.stage_metrics[stage_name] = self.stage_metrics[stage_name][-100:]
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status and metrics."""
        return {
            "optimization_enabled": self.optimization_enabled,
            "last_optimization": self.last_optimization,
            "next_optimization": self.last_optimization + self.optimization_interval,
            "stages_tracked": list(self.stage_metrics.keys()),
            "metrics_history_size": len(self.metrics_history),
            "optimization_targets": {
                name: {
                    "min_throughput": target.min_throughput,
                    "max_latency": target.max_latency,
                    "max_error_rate": target.max_error_rate,
                    "preferred_frequency": target.preferred_frequency
                }
                for name, target in self.optimization_targets.items()
            }
        }
    
    def set_optimization_enabled(self, enabled: bool):
        """Enable or disable auto-optimization."""
        self.optimization_enabled = enabled
        logger.info(f"Auto-optimization {'enabled' if enabled else 'disabled'}")
    
    def force_optimization_cycle(self, current_metrics: Dict[str, PipelineMetrics]) -> Dict[str, Any]:
        """Force an immediate optimization cycle regardless of interval."""
        self.last_optimization = 0.0  # Reset to force cycle
        return self.optimize_pipeline(current_metrics)