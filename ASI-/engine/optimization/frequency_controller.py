"""
Frequency Controller — Light-ASI LLM Gateway
Controls pipeline stage frequencies based on token metrics and performance.
Optimizes frequency to balance throughput, latency, and resource consumption.
"""

import time
import math
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("light-asi.frequency_controller")


class FrequencyAdjustmentType(Enum):
    """Types of frequency adjustments."""
    THROUGHPUT_BOOST = "throughput_boost"
    LATENCY_OPTIMIZATION = "latency_optimization"
    ERROR_MITIGATION = "error_mitigation"
    TOKEN_CONSERVATION = "token_conservation"
    LOAD_BALANCING = "load_balancing"


@dataclass
class FrequencyConfig:
    """Frequency configuration for a pipeline stage."""
    stage_name: str
    current_frequency: float  # Hz
    target_frequency: float   # Hz
    min_frequency: float
    max_frequency: float
    adjustment_step: float    # Hz per adjustment
    adaptive: bool = True
    last_adjustment: float = field(default_factory=time.time)


@dataclass  
class FrequencyAdjustment:
    """Record of a frequency adjustment."""
    stage_name: str
    old_frequency: float
    new_frequency: float
    adjustment_type: FrequencyAdjustmentType
    reason: str
    expected_impact: Dict[str, float]
    timestamp: float = field(default_factory=time.time)


class FrequencyController:
    """
    Controls pipeline stage frequencies for optimal performance.
    Manages frequency adjustments based on performance metrics and token consumption.
    """
    
    def __init__(self):
        # Stage frequency configurations
        self.stage_configs: Dict[str, FrequencyConfig] = {}
        
        # Adjustment history
        self.adjustment_history: List[FrequencyAdjustment] = []
        
        # Performance tracking
        self.frequency_performance: Dict[str, List[Dict[str, float]]] = {}
        
        # Initialize default configurations
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Initialize default frequency configurations."""
        default_configs = [
            # (stage_name, current_hz, min_hz, max_hz, step_hz)
            ("hash_pipeline", 50.0, 5.0, 200.0, 5.0),
            ("node_selection", 100.0, 10.0, 300.0, 10.0),
            ("resonance_tracking", 25.0, 2.0, 100.0, 2.0),
            ("semantic_query", 10.0, 1.0, 50.0, 1.0),
            ("cluster_management", 20.0, 2.0, 80.0, 2.0),
            ("world_ingestion", 5.0, 0.5, 20.0, 0.5),
            ("backup_operations", 1.0, 0.1, 10.0, 0.1),
            ("verification", 30.0, 3.0, 120.0, 3.0)
        ]
        
        for stage_name, freq, min_freq, max_freq, step in default_configs:
            self.stage_configs[stage_name] = FrequencyConfig(
                stage_name=stage_name,
                current_frequency=freq,
                target_frequency=freq,
                min_frequency=min_freq,
                max_frequency=max_freq,
                adjustment_step=step
            )
    
    def adjust_frequency(self, stage_name: str, target_frequency: float,
                        adjustment_type: FrequencyAdjustmentType,
                        reason: str = "") -> float:
        """
        Adjust frequency for a pipeline stage.
        Returns the new frequency value after adjustment.
        """
        # Get or create config
        if stage_name not in self.stage_configs:
            self._create_stage_config(stage_name, target_frequency)
            
        config = self.stage_configs[stage_name]
        old_frequency = config.current_frequency
        
        # Validate target frequency
        target_frequency = max(config.min_frequency, 
                             min(config.max_frequency, target_frequency))
        
        # Calculate gradual adjustment
        if config.adaptive:
            freq_diff = target_frequency - config.current_frequency
            adjustment_step = min(abs(freq_diff), config.adjustment_step)
            
            if freq_diff > 0:
                new_frequency = config.current_frequency + adjustment_step
            elif freq_diff < 0:
                new_frequency = config.current_frequency - adjustment_step
            else:
                new_frequency = config.current_frequency
        else:
            new_frequency = target_frequency
            
        # Ensure within bounds
        new_frequency = max(config.min_frequency, 
                           min(config.max_frequency, new_frequency))
        
        # Update configuration
        config.current_frequency = new_frequency
        config.target_frequency = target_frequency
        config.last_adjustment = time.time()
        
        # Calculate expected impact
        expected_impact = self._calculate_expected_impact(
            stage_name, old_frequency, new_frequency, adjustment_type
        )
        
        # Record adjustment
        adjustment = FrequencyAdjustment(
            stage_name=stage_name,
            old_frequency=old_frequency,
            new_frequency=new_frequency,
            adjustment_type=adjustment_type,
            reason=reason or f"{adjustment_type.value} optimization",
            expected_impact=expected_impact
        )
        
        self.adjustment_history.append(adjustment)
        
        # Keep history manageable
        if len(self.adjustment_history) > 1000:
            self.adjustment_history = self.adjustment_history[-1000:]
            
        logger.info(f"Adjusted frequency for {stage_name}: "
                   f"{old_frequency:.1f}Hz → {new_frequency:.1f}Hz ({adjustment_type.value})")
        
        return new_frequency
    
    def _create_stage_config(self, stage_name: str, initial_frequency: float):
        """Create configuration for a new stage."""
        self.stage_configs[stage_name] = FrequencyConfig(
            stage_name=stage_name,
            current_frequency=initial_frequency,
            target_frequency=initial_frequency,
            min_frequency=0.1,
            max_frequency=500.0,
            adjustment_step=max(1.0, initial_frequency * 0.1)
        )
    
    def _calculate_expected_impact(self, stage_name: str, old_frequency: float,
                                  new_frequency: float, adjustment_type: FrequencyAdjustmentType) -> Dict[str, float]:
        """Calculate expected performance impact of frequency change."""
        
        frequency_ratio = new_frequency / old_frequency if old_frequency > 0 else 1.0
        
        # Base impact calculations
        expected_impact = {
            "throughput": frequency_ratio,           # Linear relationship
            "latency": 1.0 / frequency_ratio,        # Inverse relationship
            "cpu_usage": frequency_ratio ** 0.8,     # Sublinear increase
            "memory_usage": frequency_ratio ** 0.6,  # Even more sublinear
            "token_consumption": frequency_ratio ** 1.1,  # Slightly superlinear
        }
        
        # Adjustment type specific impacts
        if adjustment_type == FrequencyAdjustmentType.THROUGHPUT_BOOST:
            expected_impact["throughput"] *= 1.2  # Better than linear improvement
            expected_impact["queue_backlog"] = 1.0 / frequency_ratio
            
        elif adjustment_type == FrequencyAdjustmentType.LATENCY_OPTIMIZATION:
            expected_impact["latency"] *= 0.8  # Better latency than base calculation
            expected_impact["response_time"] = 1.0 / (frequency_ratio ** 1.2)
            
        elif adjustment_type == FrequencyAdjustmentType.ERROR_MITIGATION:
            expected_impact["error_rate"] = 1.0 / (frequency_ratio ** 0.5)
            expected_impact["stability"] = frequency_ratio ** 0.3
            
        elif adjustment_type == FrequencyAdjustmentType.TOKEN_CONSERVATION:
            expected_impact["token_consumption"] *= 0.9  # Better than base calculation
            expected_impact["cost_efficiency"] = 1.0 / (frequency_ratio ** 0.8)
            
        elif adjustment_type == FrequencyAdjustmentType.LOAD_BALANCING:
            expected_impact["load_distribution"] = frequency_ratio ** 0.4
            expected_impact["system_balance"] = frequency_ratio ** 0.3
        
        return expected_impact
    
    def optimize_frequency_for_throughput(self, stage_name: str, target_throughput: float,
                                         current_throughput: float) -> float:
        """Optimize frequency to achieve target throughput."""
        
        if stage_name not in self.stage_configs or current_throughput <= 0:
            return self.get_current_frequency(stage_name)
            
        config = self.stage_configs[stage_name]
        current_frequency = config.current_frequency
        
        # Calculate required frequency adjustment
        throughput_ratio = target_throughput / current_throughput
        
        # Frequency adjustment with safety margins
        if throughput_ratio > 1.1:  # Need significant increase
            frequency_multiplier = min(2.0, throughput_ratio * 0.9)  # Conservative
            new_frequency = current_frequency * frequency_multiplier
        elif throughput_ratio < 0.9:  # Can reduce frequency
            frequency_multiplier = max(0.5, throughput_ratio * 1.1)  # Conservative
            new_frequency = current_frequency * frequency_multiplier
        else:
            new_frequency = current_frequency  # Within acceptable range
            
        # Ensure within bounds
        new_frequency = max(config.min_frequency, 
                           min(config.max_frequency, new_frequency))
        
        return new_frequency
    
    def optimize_frequency_for_latency(self, stage_name: str, target_latency: float,
                                      current_latency: float) -> float:
        """Optimize frequency to achieve target latency."""
        
        if stage_name not in self.stage_configs or current_latency <= 0:
            return self.get_current_frequency(stage_name)
            
        config = self.stage_configs[stage_name]
        current_frequency = config.current_frequency
        
        # Calculate required frequency adjustment for latency
        latency_ratio = current_latency / target_latency
        
        if latency_ratio > 1.1:  # Latency too high, increase frequency
            frequency_multiplier = min(2.0, latency_ratio * 0.8)
            new_frequency = current_frequency * frequency_multiplier
        elif latency_ratio < 0.8:  # Latency good, can reduce frequency
            frequency_multiplier = max(0.6, 1.0 / latency_ratio * 0.8)
            new_frequency = current_frequency * frequency_multiplier
        else:
            new_frequency = current_frequency
            
        # Ensure within bounds
        new_frequency = max(config.min_frequency,
                           min(config.max_frequency, new_frequency))
        
        return new_frequency