"""
Token Metrics Manager for Pipeline Optimization
Manages frequency based on token metrics and consumption rates to debug failure rates.
"""

import json
import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import hashlib


class TokenMetricType(Enum):
    """Types of token metrics."""
    CONSUMPTION = "consumption"
    GENERATION = "generation"
    PROCESSING = "processing"
    LATENCY = "latency"
    ERROR = "error"


@dataclass
class TokenMetric:
    """Single token metric measurement."""
    metric_id: str
    metric_type: TokenMetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsumptionRate:
    """Consumption rate for a time window."""
    window_id: str
    tokens_per_second: float
    tokens_per_minute: float
    peak_rate: float
    average_rate: float
    window_start: float
    window_end: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FrequencyConfig:
    """Frequency configuration for pipeline optimization."""
    pipeline_stage: str
    base_frequency: float  # Hz
    current_frequency: float  # Hz
    min_frequency: float
    max_frequency: float
    token_budget: float
    consumption_threshold: float
    adaptive: bool = True


class TokenMetricsManager:
    """
    Token metrics manager for pipeline optimization.
    Tracks token consumption, manages frequency based on metrics, and debugs failure rates.
    """
    
    def __init__(self, window_size: int = 60, max_history: int = 1000):
        self.window_size = window_size  # seconds
        self.max_history = max_history
        
        # Token metrics history
        self.metrics_history: deque = deque(maxlen=max_history)
        
        # Consumption rates
        self.consumption_rates: Dict[str, ConsumptionRate] = {}
        
        # Frequency configurations per pipeline stage
        self.frequency_configs: Dict[str, FrequencyConfig] = {}
        
        # Token budget tracking
        self.token_budget = 1000000  # 1M tokens
        self.tokens_consumed = 0
        self.tokens_remaining = self.token_budget
        
        # Failure rate tracking
        self.failure_events: List[Dict[str, Any]] = []
        self.failure_rate = 0.0
        
        # Optimization state
        self.optimization_active = False
        self.last_optimization_time = 0.0
        
        # Initialize frequency configs for pipeline stages
        self._initialize_frequency_configs()
    
    def _initialize_frequency_configs(self):
        """Initialize frequency configurations for pipeline stages."""
        stages = [
            ("ingestion", 100.0, 10.0, 500.0),
            ("processing", 50.0, 5.0, 200.0),
            ("querying", 20.0, 1.0, 100.0),
            ("verification", 30.0, 5.0, 100.0),
            ("output", 80.0, 10.0, 300.0)
        ]
        
        for stage, base_freq, min_freq, max_freq in stages:
            config = FrequencyConfig(
                pipeline_stage=stage,
                base_frequency=base_freq,
                current_frequency=base_freq,
                min_frequency=min_freq,
                max_frequency=max_freq,
                token_budget=self.token_budget / len(stages),
                consumption_threshold=0.8
            )
            self.frequency_configs[stage] = config
    
    def record_metric(self, metric_type: TokenMetricType, value: float,
                     metadata: Dict[str, Any] = None) -> str:
        """Record a token metric."""
        metric_id = f"metric_{int(time.time() * 1000000)}"
        
        metric = TokenMetric(
            metric_id=metric_id,
            metric_type=metric_type,
            value=value,
            metadata=metadata or {}
        )
        
        self.metrics_history.append(metric)
        
        # Update token consumption
        if metric_type == TokenMetricType.CONSUMPTION:
            self.tokens_consumed += value
            self.tokens_remaining = max(0, self.token_budget - self.tokens_consumed)
        
        # Track failures
        if metric_type == TokenMetricType.ERROR:
            self.failure_events.append({
                "metric_id": metric_id,
                "value": value,
                "timestamp": metric.timestamp,
                "metadata": metadata
            })
            self._update_failure_rate()
        
        return metric_id
    
    def calculate_consumption_rate(self, window_seconds: int = 60) -> ConsumptionRate:
        """Calculate consumption rate for time window."""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Filter metrics within window
        window_metrics = [
            m for m in self.metrics_history
            if m.timestamp >= window_start and m.metric_type == TokenMetricType.CONSUMPTION
        ]
        
        if not window_metrics:
            return ConsumptionRate(
                window_id=f"window_{int(current_time)}",
                tokens_per_second=0.0,
                tokens_per_minute=0.0,
                peak_rate=0.0,
                average_rate=0.0,
                window_start=window_start,
                window_end=current_time
            )
        
        # Calculate rates
        total_tokens = sum(m.value for m in window_metrics)
        tokens_per_second = total_tokens / window_seconds
        tokens_per_minute = tokens_per_second * 60
        
        # Calculate peak rate
        peak_rate = max(m.value for m in window_metrics) if window_metrics else 0.0
        
        # Calculate average rate
        average_rate = total_tokens / len(window_metrics) if window_metrics else 0.0
        
        rate = ConsumptionRate(
            window_id=f"window_{int(current_time)}",
            tokens_per_second=tokens_per_second,
            tokens_per_minute=tokens_per_minute,
            peak_rate=peak_rate,
            average_rate=average_rate,
            window_start=window_start,
            window_end=current_time
        )
        
        self.consumption_rates[rate.window_id] = rate
        
        return rate
    
    def optimize_frequency(self, stage: str, consumption_rate: float) -> float:
        """
        Optimize frequency based on consumption rate.
        Adjusts pipeline stage frequency to stay within token budget.
        """
        if stage not in self.frequency_configs:
            return 0.0
        
        config = self.frequency_configs[stage]
        
        if not config.adaptive:
            return config.current_frequency
        
        # Calculate utilization
        utilization = consumption_rate / config.token_budget
        
        # Adjust frequency based on utilization
        if utilization > config.consumption_threshold:
            # Reduce frequency to stay within budget
            reduction_factor = 1.0 - (utilization - config.consumption_threshold)
            new_frequency = max(
                config.min_frequency,
                config.current_frequency * reduction_factor
            )
        elif utilization < 0.5:
            # Increase frequency if underutilized
            increase_factor = 1.0 + (0.5 - utilization) * 0.5
            new_frequency = min(
                config.max_frequency,
                config.current_frequency * increase_factor
            )
        else:
            # Maintain current frequency
            new_frequency = config.current_frequency
        
        config.current_frequency = new_frequency
        self.last_optimization_time = time.time()
        
        return new_frequency
    
    def optimize_all_frequencies(self) -> Dict[str, float]:
        """Optimize frequencies for all pipeline stages."""
        consumption_rate = self.calculate_consumption_rate()
        
        optimized = {}
        for stage in self.frequency_configs:
            optimized[stage] = self.optimize_frequency(
                stage, consumption_rate.tokens_per_second
            )
        
        return optimized
    
    def _update_failure_rate(self):
        """Update failure rate based on recent events."""
        if not self.failure_events:
            self.failure_rate = 0.0
            return
        
        # Calculate failure rate over last 60 seconds
        current_time = time.time()
        recent_failures = [
            f for f in self.failure_events
            if current_time - f["timestamp"] < 60
        ]
        
        # Get total metrics in same window
        recent_metrics = [
            m for m in self.metrics_history
            if current_time - m.timestamp < 60
        ]
        
        if recent_metrics:
            self.failure_rate = len(recent_failures) / len(recent_metrics)
        else:
            self.failure_rate = 0.0
    
    def debug_failure_rate(self) -> Dict[str, Any]:
        """
        Debug failure rate with token analysis.
        Identifies patterns and correlations between token consumption and failures.
        """
        if self.failure_rate == 0.0:
            return {
                "failure_rate": 0.0,
                "message": "No failures detected"
            }
        
        # Analyze failure patterns
        failure_analysis = {
            "total_failures": len(self.failure_events),
            "current_failure_rate": self.failure_rate,
            "patterns": [],
            "recommendations": []
        }
        
        # Check for high consumption correlation
        high_consumption_failures = [
            f for f in self.failure_events
            if f.get("metadata", {}).get("consumption", 0) > 1000
        ]
        
        if high_consumption_failures:
            failure_analysis["patterns"].append({
                "pattern": "high_consumption_correlation",
                "count": len(high_consumption_failures),
                "description": "Failures correlate with high token consumption"
            })
            failure_analysis["recommendations"].append(
                "Reduce token consumption or increase token budget"
            )
        
        # Check for frequency-related failures
        frequency_failures = [
            f for f in self.failure_events
            if f.get("metadata", {}).get("frequency", 0) > 100
        ]
        
        if frequency_failures:
            failure_analysis["patterns"].append({
                "pattern": "high_frequency_correlation",
                "count": len(frequency_failures),
                "description": "Failures correlate with high processing frequency"
            })
            failure_analysis["recommendations"].append(
                "Reduce processing frequency to improve stability"
            )
        
        # Check for stage-specific failures
        stage_failures = {}
        for failure in self.failure_events:
            stage = failure.get("metadata", {}).get("stage", "unknown")
            stage_failures[stage] = stage_failures.get(stage, 0) + 1
        
        if stage_failures:
            worst_stage = max(stage_failures, key=stage_failures.get)
            failure_analysis["patterns"].append({
                "pattern": "stage_specific_failures",
                "worst_stage": worst_stage,
                "count": stage_failures[worst_stage]
            })
            failure_analysis["recommendations"].append(
                f"Investigate and optimize {worst_stage} stage"
            )
        
        return failure_analysis
    
    def get_token_budget_status(self) -> Dict[str, Any]:
        """Get current token budget status."""
        consumption_rate = self.calculate_consumption_rate()
        
        return {
            "token_budget": self.token_budget,
            "tokens_consumed": self.tokens_consumed,
            "tokens_remaining": self.tokens_remaining,
            "utilization": self.tokens_consumed / self.token_budget,
            "consumption_rate": {
                "tokens_per_second": consumption_rate.tokens_per_second,
                "tokens_per_minute": consumption_rate.tokens_per_minute,
                "peak_rate": consumption_rate.peak_rate,
                "average_rate": consumption_rate.average_rate
            },
            "estimated_time_remaining": (
                self.tokens_remaining / consumption_rate.tokens_per_second
                if consumption_rate.tokens_per_second > 0 else float('inf')
            )
        }
    
    def get_frequency_status(self) -> Dict[str, Any]:
        """Get current frequency status for all stages."""
        return {
            stage: {
                "current_frequency": config.current_frequency,
                "base_frequency": config.base_frequency,
                "min_frequency": config.min_frequency,
                "max_frequency": config.max_frequency,
                "adaptive": config.adaptive,
                "utilization": config.current_frequency / config.max_frequency
            }
            for stage, config in self.frequency_configs.items()
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        if not self.metrics_history:
            return {"message": "No metrics recorded yet"}
        
        # Group by type
        metrics_by_type = {}
        for metric in self.metrics_history:
            mtype = metric.metric_type.value
            if mtype not in metrics_by_type:
                metrics_by_type[mtype] = []
            metrics_by_type[mtype].append(metric.value)
        
        # Calculate statistics
        summary = {
            "total_metrics": len(self.metrics_history),
            "metrics_by_type": {},
            "time_range": {
                "start": min(m.timestamp for m in self.metrics_history),
                "end": max(m.timestamp for m in self.metrics_history)
            }
        }
        
        for mtype, values in metrics_by_type.items():
            summary["metrics_by_type"][mtype] = {
                "count": len(values),
                "total": sum(values),
                "average": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
        
        return summary
    
    def set_token_budget(self, budget: float):
        """Set token budget."""
        self.token_budget = budget
        self.tokens_remaining = max(0, budget - self.tokens_consumed)
        
        # Update frequency configs
        for config in self.frequency_configs.values():
            config.token_budget = budget / len(self.frequency_configs)
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics_history.clear()
        self.consumption_rates.clear()
        self.failure_events.clear()
        self.tokens_consumed = 0
        self.tokens_remaining = self.token_budget
        self.failure_rate = 0.0
    
    def enable_optimization(self):
        """Enable automatic frequency optimization."""
        self.optimization_active = True
    
    def disable_optimization(self):
        """Disable automatic frequency optimization."""
        self.optimization_active = False
    
    def save_metrics(self, filepath: str):
        """Save metrics to file."""
        data = {
            "token_budget": self.token_budget,
            "tokens_consumed": self.tokens_consumed,
            "failure_rate": self.failure_rate,
            "frequency_configs": {
                stage: {
                    "base_frequency": config.base_frequency,
                    "current_frequency": config.current_frequency,
                    "min_frequency": config.min_frequency,
                    "max_frequency": config.max_frequency,
                    "adaptive": config.adaptive
                }
                for stage, config in self.frequency_configs.items()
            },
            "metrics_history": [
                {
                    "metric_id": m.metric_id,
                    "metric_type": m.metric_type.value,
                    "value": m.value,
                    "timestamp": m.timestamp,
                    "metadata": m.metadata
                }
                for m in self.metrics_history
            ],
            "failure_events": self.failure_events
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_metrics(self, filepath: str):
        """Load metrics from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.token_budget = data.get("token_budget", 1000000)
            self.tokens_consumed = data.get("tokens_consumed", 0)
            self.tokens_remaining = max(0, self.token_budget - self.tokens_consumed)
            self.failure_rate = data.get("failure_rate", 0.0)
            
            # Load frequency configs
            for stage, config_data in data.get("frequency_configs", {}).items():
                if stage in self.frequency_configs:
                    config = self.frequency_configs[stage]
                    config.base_frequency = config_data["base_frequency"]
                    config.current_frequency = config_data["current_frequency"]
                    config.min_frequency = config_data["min_frequency"]
                    config.max_frequency = config_data["max_frequency"]
                    config.adaptive = config_data["adaptive"]
            
            # Load metrics history
            for metric_data in data.get("metrics_history", []):
                metric = TokenMetric(
                    metric_type=TokenMetricType(metric_data["metric_type"]),
                    value=metric_data["value"],
                    timestamp=metric_data["timestamp"],
                    metadata=metric_data.get("metadata", {})
                )
                metric.metric_id = metric_data["metric_id"]
                self.metrics_history.append(metric)
            
            # Load failure events
            self.failure_events = data.get("failure_events", [])
            
        except FileNotFoundError:
            pass  # No existing metrics file
