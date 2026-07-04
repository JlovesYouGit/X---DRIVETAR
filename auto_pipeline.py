"""
Automatic Data Pipeline for Model Querying
Translates and queries automatically to manage overflow.
Model only keeps track, confirms, and verifies conditions are operating safely.
"""

import json
import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
import hashlib

try:
    from token_metrics_manager import TokenMetricsManager, TokenMetricType
except ImportError:
    TokenMetricsManager = None
    TokenMetricType = None


class PipelineStage(Enum):
    INGESTION = "ingestion"
    PROCESSING = "processing"
    QUERYING = "querying"
    VERIFICATION = "verification"
    OUTPUT = "output"


@dataclass
class PipelineData:
    """Data packet flowing through the pipeline."""
    data_id: str
    payload: Dict[str, Any]
    stage: PipelineStage = PipelineStage.INGESTION
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0


@dataclass
class SafetyCheck:
    """Safety verification result."""
    check_id: str
    passed: bool
    reason: str
    metrics: Dict[str, float]
    timestamp: float = field(default_factory=time.time)


class AutomaticDataPipeline:
    """
    Automatic data pipeline that translates and queries automatically.
    Manages overflow while model only tracks, confirms, and verifies safety.
    """
    
    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        
        # Pipeline queues
        self.ingestion_queue: Queue = Queue(maxsize=buffer_size)
        self.processing_queue: Queue = Queue(maxsize=buffer_size)
        self.querying_queue: Queue = Queue(maxsize=buffer_size)
        self.verification_queue: Queue = Queue(maxsize=buffer_size)
        self.output_queue: Queue = Queue(maxsize=buffer_size)
        
        # Pipeline state
        self.is_running = False
        self.pipeline_threads: List[threading.Thread] = []
        
        # Safety verification
        self.safety_checks: List[SafetyCheck] = []
        self.safety_thresholds = {
            "max_density": 0.9,
            "max_velocity": 30.0,  # m/s
            "min_confidence": 0.7,
            "max_latency": 1.0  # seconds
        }
        
        # Model tracking
        self.model_queries: Dict[str, Any] = {}
        self.model_confirmations: Dict[str, bool] = {}
        
        # Overflow management
        self.overflow_buffer: List[PipelineData] = []
        self.overflow_count = 0
        
        # Statistics
        self.stats = {
            "ingested": 0,
            "processed": 0,
            "queried": 0,
            "verified": 0,
            "output": 0,
            "failed": 0,
            "overflow_events": 0
        }
        
        # Token metrics manager
        self.token_metrics = TokenMetricsManager() if TokenMetricsManager else None
    
    def start(self):
        """Start the automatic pipeline."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start pipeline stage threads
        self.pipeline_threads = [
            threading.Thread(target=self._ingestion_stage, daemon=True),
            threading.Thread(target=self._processing_stage, daemon=True),
            threading.Thread(target=self._querying_stage, daemon=True),
            threading.Thread(target=self._verification_stage, daemon=True),
            threading.Thread(target=self._output_stage, daemon=True),
        ]
        
        for thread in self.pipeline_threads:
            thread.start()
    
    def stop(self):
        """Stop the automatic pipeline."""
        self.is_running = False
        
        for thread in self.pipeline_threads:
            thread.join(timeout=2.0)
        
        self.pipeline_threads.clear()
    
    def ingest(self, payload: Dict[str, Any]) -> str:
        """
        Ingest data into the pipeline.
        Automatically translates and prepares for processing.
        """
        data_id = self._generate_data_id(payload)
        
        data = PipelineData(
            data_id=data_id,
            payload=payload,
            stage=PipelineStage.INGESTION,
            metadata={"source": "external"}
        )
        
        # Try to add to queue, handle overflow
        try:
            self.ingestion_queue.put(data, block=False)
            self.stats["ingested"] += 1
        except:
            # Handle overflow
            self.overflow_buffer.append(data)
            self.overflow_count += 1
            self.stats["overflow_events"] += 1
        
        return data_id
    
    def _ingestion_stage(self):
        """Ingestion stage - translates incoming data."""
        stage_start = time.time()
        while self.is_running:
            try:
                data = self.ingestion_queue.get(timeout=0.1)
                
                # Record token consumption
                if self.token_metrics:
                    self.token_metrics.record_metric(
                        TokenMetricType.CONSUMPTION,
                        len(json.dumps(data.payload)),
                        {"stage": "ingestion"}
                    )
                
                # Translate data format
                translated = self._translate_data(data)
                data.payload = translated
                data.stage = PipelineStage.PROCESSING
                data.metadata["translated_at"] = time.time()
                
                self.processing_queue.put(data)
                self.stats["processed"] += 1
                
                # Record processing token
                if self.token_metrics:
                    stage_duration = time.time() - stage_start
                    self.token_metrics.record_metric(
                        TokenMetricType.PROCESSING,
                        stage_duration,
                        {"stage": "ingestion"}
                    )
                    stage_start = time.time()
                
            except Empty:
                continue
            except Exception as e:
                self.stats["failed"] += 1
                if self.token_metrics:
                    self.token_metrics.record_metric(
                        TokenMetricType.ERROR,
                        1.0,
                        {"stage": "ingestion", "error": str(e)}
                    )
    
    def _processing_stage(self):
        """Processing stage - processes and prepares for querying."""
        while self.is_running:
            try:
                data = self.processing_queue.get(timeout=0.1)
                
                # Process data
                processed = self._process_data(data)
                data.payload = processed
                data.stage = PipelineStage.QUERYING
                data.metadata["processed_at"] = time.time()
                
                self.querying_queue.put(data)
                self.stats["processed"] += 1
                
            except Empty:
                continue
            except Exception as e:
                self.stats["failed"] += 1
    
    def _querying_stage(self):
        """Querying stage - automatic model querying."""
        while self.is_running:
            try:
                data = self.querying_queue.get(timeout=0.1)
                
                # Automatic query generation
                query = self._generate_query(data)
                
                # Track query
                self.model_queries[data.data_id] = {
                    "query": query,
                    "timestamp": time.time(),
                    "status": "pending"
                }
                
                data.payload["query"] = query
                data.stage = PipelineStage.VERIFICATION
                data.metadata["queried_at"] = time.time()
                
                self.verification_queue.put(data)
                self.stats["queried"] += 1
                
            except Empty:
                continue
            except Exception as e:
                self.stats["failed"] += 1
    
    def _verification_stage(self):
        """Verification stage - safety verification."""
        while self.is_running:
            try:
                data = self.verification_queue.get(timeout=0.1)
                
                # Safety verification
                safety_check = self._verify_safety(data)
                self.safety_checks.append(safety_check)
                
                data.payload["safety_check"] = {
                    "passed": safety_check.passed,
                    "reason": safety_check.reason,
                    "metrics": safety_check.metrics
                }
                
                # Model confirmation
                self.model_confirmations[data.data_id] = safety_check.passed
                
                data.stage = PipelineStage.OUTPUT
                data.metadata["verified_at"] = time.time()
                
                self.output_queue.put(data)
                self.stats["verified"] += 1
                
            except Empty:
                continue
            except Exception as e:
                self.stats["failed"] += 1
    
    def _output_stage(self):
        """Output stage - final output delivery."""
        while self.is_running:
            try:
                data = self.output_queue.get(timeout=0.1)
                
                # Deliver output
                self._deliver_output(data)
                
                self.stats["output"] += 1
                
                # Update model query status
                if data.data_id in self.model_queries:
                    self.model_queries[data.data_id]["status"] = "completed"
                
            except Empty:
                continue
            except Exception as e:
                self.stats["failed"] += 1
    
    def _translate_data(self, data: PipelineData) -> Dict[str, Any]:
        """Translate data to internal format."""
        payload = data.payload
        
        # Extract relevant fields
        translated = {
            "coordinates": payload.get("coordinates", {}),
            "density": payload.get("density", 0.0),
            "velocity": payload.get("velocity", 0.0),
            "timestamp": payload.get("timestamp", time.time()),
            "source": payload.get("source", "unknown")
        }
        
        return translated
    
    def _process_data(self, data: PipelineData) -> Dict[str, Any]:
        """Process data for querying."""
        payload = data.payload
        
        # Add computed fields
        processed = payload.copy()
        processed["computed"] = {
            "magnitude": self._compute_magnitude(payload.get("coordinates", {})),
            "risk_score": self._compute_risk_score(payload),
            "priority": self._compute_priority(payload)
        }
        
        return processed
    
    def _generate_query(self, data: PipelineData) -> str:
        """
        Generate automatic query for model.
        System automatically prompts the model with parameters.
        """
        payload = data.payload
        
        # Build query from data
        query_parts = [
            f"Analyze spatial data at coordinates {payload.get('coordinates', {})}",
            f"Current density: {payload.get('density', 0.0):.2f}",
            f"Velocity: {payload.get('velocity', 0.0):.2f} m/s",
            f"Risk score: {payload.get('computed', {}).get('risk_score', 0.0):.2f}"
        ]
        
        query = " | ".join(query_parts)
        
        return query
    
    def _verify_safety(self, data: PipelineData) -> SafetyCheck:
        """
        Verify safety conditions.
        Model only confirms and verifies conditions are operating safely.
        """
        payload = data.payload
        check_id = f"check_{hash(str(payload)) % 100000}"
        
        # Check safety thresholds
        density = payload.get("density", 0.0)
        velocity = payload.get("velocity", 0.0)
        confidence = payload.get("computed", {}).get("priority", 0.0)
        
        checks_passed = []
        checks_failed = []
        
        if density < self.safety_thresholds["max_density"]:
            checks_passed.append("density")
        else:
            checks_failed.append("density")
        
        if velocity < self.safety_thresholds["max_velocity"]:
            checks_passed.append("velocity")
        else:
            checks_failed.append("velocity")
        
        if confidence > self.safety_thresholds["min_confidence"]:
            checks_passed.append("confidence")
        else:
            checks_failed.append("confidence")
        
        passed = len(checks_failed) == 0
        reason = f"Passed: {checks_passed}, Failed: {checks_failed}"
        
        metrics = {
            "density": density,
            "velocity": velocity,
            "confidence": confidence,
            "passed_checks": len(checks_passed),
            "failed_checks": len(checks_failed)
        }
        
        return SafetyCheck(
            check_id=check_id,
            passed=passed,
            reason=reason,
            metrics=metrics
        )
    
    def _deliver_output(self, data: PipelineData):
        """Deliver output to downstream systems."""
        # In production, this would send to external systems
        # For now, just log
        pass
    
    def _compute_magnitude(self, coordinates: Dict) -> float:
        """Compute magnitude from coordinates."""
        x = coordinates.get("x", 0.0)
        y = coordinates.get("y", 0.0)
        z = coordinates.get("z", 0.0)
        return (x**2 + y**2 + z**2)**0.5
    
    def _compute_risk_score(self, payload: Dict) -> float:
        """Compute risk score from payload."""
        density = payload.get("density", 0.0)
        velocity = payload.get("velocity", 0.0)
        
        # Simple risk calculation
        risk = (density * 0.6) + (velocity / 30.0 * 0.4)
        return min(1.0, risk)
    
    def _compute_priority(self, payload: Dict) -> float:
        """Compute priority for processing."""
        risk = self._compute_risk_score(payload)
        return 1.0 - risk  # Higher risk = lower priority
    
    def _generate_data_id(self, payload: Dict) -> str:
        """Generate unique data ID."""
        raw = json.dumps(payload, sort_keys=True) + str(time.time())
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "is_running": self.is_running,
            "queue_sizes": {
                "ingestion": self.ingestion_queue.qsize(),
                "processing": self.processing_queue.qsize(),
                "querying": self.querying_queue.qsize(),
                "verification": self.verification_queue.qsize(),
                "output": self.output_queue.qsize()
            },
            "buffer_size": self.buffer_size,
            "overflow_count": self.overflow_count,
            "overflow_buffer_size": len(self.overflow_buffer),
            "safety_checks_count": len(self.safety_checks),
            "model_queries_count": len(self.model_queries),
            "model_confirmations_count": len(self.model_confirmations),
            "stats": self.stats.copy(),
            "safety_thresholds": self.safety_thresholds
        }
    
    def get_safety_report(self) -> Dict[str, Any]:
        """Get safety verification report."""
        if not self.safety_checks:
            return {"message": "No safety checks performed yet"}
        
        passed = sum(1 for check in self.safety_checks if check.passed)
        failed = len(self.safety_checks) - passed
        
        return {
            "total_checks": len(self.safety_checks),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(self.safety_checks) if self.safety_checks else 0.0,
            "recent_checks": [
                {
                    "check_id": check.check_id,
                    "passed": check.passed,
                    "reason": check.reason,
                    "timestamp": check.timestamp
                }
                for check in self.safety_checks[-10:]
            ]
        }
    
    def process_overflow(self):
        """Process overflow buffer when capacity available."""
        if not self.overflow_buffer:
            return
        
        processed = 0
        while self.overflow_buffer and processed < 10:
            data = self.overflow_buffer.pop(0)
            try:
                self.ingestion_queue.put(data, block=False)
                processed += 1
            except:
                # Still full, put back
                self.overflow_buffer.insert(0, data)
                break
        
        return processed
