"""
Unified Main Entry Point for Autonomous Lidar Navigation System
Integrates all components: lidar/sonar engine, maps calibration, spatialmythos,
virtual-probe_X, ASI-, and automatic data pipeline.
"""

import sys
import json
import time
import argparse
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Import all system components
from lidar_sonar_engine import LidarSonarEngine, Coordinate, VehicleControlInput
from maps_calibration import AppleMapsCalibrator, MapLayerType
from spatialmythos_integration import SpatialmythosIntegrator
from virtual_probe_integration import VirtualProbeIntegrator
from asi_integration import ASIIntegrator
from auto_pipeline import AutomaticDataPipeline, PipelineStage
from virtual_test_layer import VirtualTestLayer, ScenarioType
from self_management import SelfManagementSystem, ManagementMode
from neural_brain_integration import NeuralBrainEngine, NeuralPathType


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lidar_autonomy.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class AutonomousLidarSystem:
    """
    Main autonomous lidar navigation system.
    Integrates all components for complete autonomous navigation.
    """
    
    def __init__(self, vehicle_id: str = "vehicle_0", sensor_range: float = 100.0):
        self.vehicle_id = vehicle_id
        self.sensor_range = sensor_range
        
        # Initialize core components
        logger.info("Initializing Lidar-Sonar Engine...")
        self.lidar_engine = LidarSonarEngine(vehicle_id, sensor_range)
        
        logger.info("Initializing Apple Maps Calibrator...")
        self.maps_calibrator = AppleMapsCalibrator()
        
        logger.info("Initializing Spatialmythos Integrator...")
        self.spatialmythos = SpatialmythosIntegrator(self.lidar_engine)
        
        logger.info("Initializing Virtual Probe Integrator...")
        self.virtual_probe = VirtualProbeIntegrator(self.lidar_engine)
        
        logger.info("Initializing ASI Integrator...")
        self.asi_integrator = ASIIntegrator(self.lidar_engine)
        
        # Initialize real-world mapping for autonomous driving
        scan_bounds = (-50.0, 50.0, -50.0, 50.0)  # 100m x 100m scan area
        mapping_result = self.asi_integrator.initialize_real_world_mapping(scan_bounds)
        logger.info(f"Real-world mapping initialized: {mapping_result}")
        
        # Optimize for autonomous driving performance
        optimization_result = self.asi_integrator.optimize_for_autonomous_driving()
        logger.info(f"Autonomous driving optimizations: {optimization_result}")
        
        logger.info("Initializing Automatic Data Pipeline...")
        self.pipeline = AutomaticDataPipeline(buffer_size=1000)
        
        logger.info("Initializing Virtual Test Layer...")
        self.virtual_test_layer = VirtualTestLayer(self.lidar_engine)
        
        logger.info("Initializing Self-Management System...")
        self.self_management = SelfManagementSystem(self.virtual_test_layer, self.lidar_engine)
        
        logger.info("Initializing Neural Brain Engine...")
        self.neural_brain = NeuralBrainEngine(self.lidar_engine)
        
        # System state
        self.is_running = False
        self.navigation_active = False
        
        logger.info("System initialization complete.")
    
    def start(self):
        """Start the autonomous navigation system."""
        logger.info("Starting autonomous lidar system...")
        
        # Start automatic pipeline
        self.pipeline.start()
        
        self.is_running = True
        logger.info("System started successfully.")
    
    def stop(self):
        """Stop the autonomous navigation system."""
        logger.info("Stopping autonomous lidar system...")
        
        # Stop automatic pipeline
        self.pipeline.stop()
        
        self.is_running = False
        self.navigation_active = False
        logger.info("System stopped.")
    
    def process_sonar_data(self, left_sonar: float, right_sonar: float, 
                          external_wave: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Process sonar data through the complete pipeline.
        """
        logger.info(f"Processing sonar data: left={left_sonar:.2f}, right={right_sonar:.2f}")
        
        # Compute dual-instance X coordinates
        coord = self.lidar_engine.compute_dual_x(left_sonar, right_sonar)
        
        # Generate wave field
        wave_field = self.lidar_engine.generate_wave_field(coord)
        
        # Detect wave inversion and create anchor points
        if external_wave:
            anchors = self.lidar_engine.detect_wave_inversion(external_wave)
            
            # Create measure strings for each anchor
            for anchor in anchors:
                self.lidar_engine.create_measure_strings(anchor)
            
            # Map anchors to spatial gates
            self.virtual_probe.map_anchors_to_gates(self.lidar_engine.anchors)
        
        # Update vehicle position
        self.lidar_engine.update_vehicle_position(coord)
        
        # Ingest data into pipeline
        pipeline_data = {
            "coordinates": {
                "x": coord.x_center,
                "y": coord.y,
                "z": coord.z
            },
            "density": self.lidar_engine._get_density_at_point(coord.x_center, coord.y),
            "velocity": 0.0,
            "timestamp": time.time(),
            "source": "sonar"
        }
        
        data_id = self.pipeline.ingest(pipeline_data)
        
        return {
            "coordinate": {
                "x_center": coord.x_center,
                "x_plus": coord.x_plus,
                "x_minus": coord.x_minus,
                "y": coord.y,
                "z": coord.z
            },
            "anchors_detected": len(self.lidar_engine.anchors),
            "measure_strings": len(self.lidar_engine.measure_strings),
            "pipeline_data_id": data_id
        }
    
    def calibrate_to_map(self, region: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """
        Calibrate sonar data to Apple Maps template.
        Region: (lat_min, lat_max, lon_min, lon_max)
        """
        logger.info(f"Calibrating to map region: {region}")
        
        # Fetch map template
        map_template = self.maps_calibrator.fetch_map_template(region)
        
        # Collect sonar coordinates
        sonar_coords = []
        for coord in self.lidar_engine.trajectory[-10:]:  # Last 10 points
            sonar_coords.append((coord.x_center, coord.y, coord.z))
        
        # Calibrate
        calibrated_points = self.maps_calibrator.calibrate_sonar_to_map(
            sonar_coords, map_template
        )
        
        return {
            "region": region,
            "calibrated_points": len(calibrated_points),
            "avg_confidence": (
                sum(p.confidence for p in calibrated_points) / len(calibrated_points)
                if calibrated_points else 0.0
            ),
            "calibration_offset": self.maps_calibrator.calibration_offset
        }
    
    def plan_path(self, start: Coordinate, end: Coordinate, 
                  iterations: int = 100) -> Dict[str, Any]:
        """
        Plan optimal path using all integrated systems.
        """
        logger.info(f"Planning path from {start.x_center:.2f} to {end.x_center:.2f}")
        
        # Use Spatialmythos for hyper-speed iterations
        path_iteration = self.spatialmythos.hyper_speed_path_iteration(
            start, end, iterations
        )
        
        # Optimize path with density data
        optimized_path = self.spatialmythos.optimize_path_with_density(
            path_iteration.path_coordinates
        )
        
        # Use virtual probe to route through gates
        gate_path = self.virtual_probe.optimize_path_through_gates(start, end)
        
        # Create virtual sequence in ASI
        virtual_sequence = self.asi_integrator.create_virtual_sequence(
            optimized_path, start, end
        )
        
        # Conscience decision on path
        path_viable = self.lidar_engine.conscience_decision(optimized_path)
        
        return {
            "path_iteration_id": path_iteration.iteration_id,
            "path_score": path_iteration.score,
            "computation_time": path_iteration.computation_time,
            "optimized_path_length": len(optimized_path),
            "gate_path_length": len(gate_path),
            "virtual_sequence_id": virtual_sequence.sequence_id,
            "virtual_sequence_score": virtual_sequence.score,
            "path_viable": path_viable
        }
    
    def navigate(self, target: Coordinate, duration: float = 60.0) -> Dict[str, Any]:
        """
        Execute autonomous navigation to target.
        """
        logger.info(f"Starting navigation to target: {target.x_center:.2f}, {target.y:.2f}")
        
        start_time = time.time()
        self.navigation_active = True
        
        # Get current position
        current = self.lidar_engine.vehicle_state.center_coordinate
        
        # Plan path
        path_plan = self.plan_path(current, target)
        
        if not path_plan["path_viable"]:
            logger.warning("Path not viable, aborting navigation")
            return {"status": "aborted", "reason": "path_not_viable"}
        
        # Navigation loop
        navigation_steps = 0
        while self.navigation_active and (time.time() - start_time) < duration:
            # Simulate sonar data processing
            left_sonar = current.x_left + 0.1
            right_sonar = current.x_right + 0.1
            
            # Process data
            result = self.process_sonar_data(left_sonar, right_sonar)
            
            # Regulate aggression (speed)
            current_speed = 10.0  # m/s
            regulated_speed = self.lidar_engine.regulate_aggression(current_speed)
            
            # Freedom mapping - swap anchor points
            if self.lidar_engine.anchors:
                current_anchor = list(self.lidar_engine.anchors.keys())[0]
                next_anchor = self.lidar_engine.freedom_mapping(current_anchor)
                if next_anchor:
                    logger.info(f"Freedom mapping: {current_anchor} -> {next_anchor}")
            
            # Check if reached target
            distance = ((target.x_center - current.x_center)**2 + 
                       (target.y - current.y)**2)**0.5
            if distance < 2.0:  # Within 2 meters
                logger.info("Target reached!")
                break
            
            # Update position (simulate movement)
            current = Coordinate(
                current.x_left + regulated_speed * 0.1,
                current.x_right + regulated_speed * 0.1,
                current.y + regulated_speed * 0.1,
                current.z
            )
            
            navigation_steps += 1
            time.sleep(0.1)  # 100ms loop
        
        self.navigation_active = False
        
        return {
            "status": "completed" if distance < 2.0 else "timeout",
            "navigation_steps": navigation_steps,
            "final_distance": distance,
            "path_plan": path_plan
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "vehicle_id": self.vehicle_id,
            "is_running": self.is_running,
            "navigation_active": self.navigation_active,
            "lidar_engine": self.lidar_engine.get_state(),
            "maps_calibration": self.maps_calibrator.get_calibration_status(),
            "spatialmythos": self.spatialmythos.get_spatial_status(),
            "virtual_probe": self.virtual_probe.get_integration_status(),
            "asi_integration": self.asi_integrator.get_spatial_status(),
            "pipeline": self.pipeline.get_pipeline_status(),
            "safety_report": self.pipeline.get_safety_report(),
            "virtual_test_layer": self.virtual_test_layer.get_test_summary(),
            "self_management": self.self_management.get_coordination_summary(),
            "neural_brain": self.neural_brain.get_brain_status()
        }
    
    def run_virtual_test(self, scenario_type: str, difficulty: float = 0.7) -> Dict[str, Any]:
        """Run virtual test for specific scenario."""
        import asyncio
        
        try:
            scenario_enum = ScenarioType(scenario_type)
        except ValueError:
            return {"error": f"Invalid scenario type: {scenario_type}"}
        
        start = Coordinate(0.0, 0.0, 0.0, 0.0)
        end = Coordinate(100.0, 100.0, 0.0, 0.0)
        
        scenario = self.virtual_test_layer.create_chaotic_scenario(
            scenario_enum, start, end, difficulty
        )
        
        result = asyncio.run(self.virtual_test_layer.run_virtual_test(scenario))
        
        return {
            "scenario_type": scenario_type,
            "difficulty": difficulty,
            "success": result.success,
            "score": result.score,
            "conflicts": result.conflicts_encountered,
            "time_elapsed": result.time_elapsed,
            "learning_hash": result.learning_hash,
            "recalibration": result.recalibration_data
        }
    
    def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive test suite with all scenarios."""
        results = self.virtual_test_layer.run_comprehensive_test_suite()
        return results
    
    def coordinate_parameters(self, scenario_type: str, difficulty: float = 0.5) -> Dict[str, Any]:
        """Coordinate parameters using self-management system."""
        import asyncio
        
        try:
            scenario_enum = ScenarioType(scenario_type)
        except ValueError:
            return {"error": f"Invalid scenario type: {scenario_type}"}
        
        decision = asyncio.run(self.self_management.coordinate_parameters(
            scenario_enum, difficulty
        ))
        
        return {
            "scenario_type": scenario_type,
            "selected_mode": decision.selected_parameters.mode.value,
            "max_velocity": decision.selected_parameters.max_velocity,
            "expected_success": decision.expected_success_rate,
            "reasoning": decision.reasoning
        }
    
    def set_management_mode(self, mode: str) -> Dict[str, Any]:
        """Set self-management mode."""
        try:
            mode_enum = ManagementMode(mode)
            self.self_management.set_management_mode(mode_enum)
            return {"status": "success", "mode": mode}
        except ValueError:
            return {"error": f"Invalid mode: {mode}"}
    
    def get_smart_decision(self, sensor_data: Dict[str, float], 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Get smart decision from neural brain."""
        control_input = self.neural_brain.get_smart_decision(sensor_data, context)
        
        return {
            "throttle": control_input.throttle,
            "brake": control_input.brake,
            "steering": control_input.steering,
            "gear": control_input.gear
        }
    
    def record_driver_experience(self, driver_id: str, scenario_type: str,
                               control_inputs: List[VehicleControlInput],
                               outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Record driver experience for learning."""
        experience = self.neural_brain.record_driver_experience(
            driver_id, scenario_type, control_inputs, outcomes
        )
        
        # Save weights after learning
        self.neural_brain.save_neural_weights()
        
        return {
            "experience_id": experience.experience_id,
            "success_rate": experience.success_rate,
            "comfort_score": experience.comfort_score,
            "compliance_score": experience.compliance_score
        }
    
    def minimize_failure_rate(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze historical data to minimize failure rate."""
        analysis = self.neural_brain.minimize_failure_rate(historical_data)
        
        # Save weights after adjustment
        self.neural_brain.save_neural_weights()
        
        return analysis
    
    def ensure_compliance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure compliance with humans, pedestrians, and abnormal conditions."""
        return self.neural_brain.ensure_compliance(context)
    
    def save_neural_weights(self):
        """Save neural weights to file."""
        self.neural_brain.save_neural_weights()
        return {"status": "success", "file": self.neural_brain.weight_file_path}
    
    def load_neural_weights(self):
        """Load neural weights from file."""
        self.neural_brain.load_neural_weights()
        return {"status": "success", "file": self.neural_brain.weight_file_path}
    
    def get_spatial_data(self) -> Dict[str, Any]:
        """Get spatial data from neural brain."""
        return self.neural_brain.get_spatial_data()
    
    def create_coordination_save_point(self, spatial_context: Dict[str, Any],
                                      control_input: VehicleControlInput,
                                      success_outcome: bool) -> Dict[str, Any]:
        """Create save point for coordination actuation logic."""
        save_point = self.neural_brain.create_coordination_save_point(
            spatial_context, control_input, success_outcome
        )
        return {
            "save_id": save_point.save_id,
            "timestamp": save_point.timestamp,
            "success_outcome": save_point.success_outcome
        }
    
    def restore_from_save_point(self, save_id: str) -> Dict[str, Any]:
        """Restore coordination state from save point."""
        save_point = self.neural_brain.restore_from_save_point(save_id)
        if save_point:
            return {
                "status": "success",
                "save_id": save_point.save_id,
                "restored": True
            }
        return {"status": "error", "message": "Save point not found"}
    
    def set_ai_availability(self, available: bool) -> Dict[str, Any]:
        """Set AI availability for fallback mode."""
        self.neural_brain.set_ai_availability(available)
        return {"status": "success", "ai_available": available}
    
    def save_state(self, filepath: str):
        """Save system state to file."""
        state = {
            "vehicle_id": self.vehicle_id,
            "sensor_range": self.sensor_range,
            "lidar_state": self.lidar_engine.get_state(),
            "maps_calibration": self.maps_calibrator.get_calibration_status(),
            "timestamp": time.time()
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"System state saved to {filepath}")
    
    def load_state(self, filepath: str):
        """Load system state from file."""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        self.vehicle_id = state["vehicle_id"]
        self.sensor_range = state["sensor_range"]
        
        # Load maps calibration
        if "calibration_cache" in state.get("maps_calibration", {}):
            self.maps_calibrator.load_calibration(filepath.replace(".json", "_calibration.json"))
        
        logger.info(f"System state loaded from {filepath}")


def main():
    """Main entry point with CLI interface."""
    parser = argparse.ArgumentParser(
        description="Autonomous Lidar Navigation System"
    )
    parser.add_argument(
        "--vehicle-id", 
        default="vehicle_0",
        help="Vehicle identifier"
    )
    parser.add_argument(
        "--sensor-range",
        type=float,
        default=100.0,
        help="Sensor range in meters"
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "demo", "navigate", "test", "comprehensive-test"],
        default="interactive",
        help="Operation mode"
    )
    parser.add_argument(
        "--target-x",
        type=float,
        help="Target X coordinate for navigation"
    )
    parser.add_argument(
        "--target-y",
        type=float,
        help="Target Y coordinate for navigation"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="Navigation duration in seconds"
    )
    parser.add_argument(
        "--scenario-type",
        help="Scenario type for virtual test (e.g., traffic_jam, sudden_obstacle)"
    )
    parser.add_argument(
        "--difficulty",
        type=float,
        default=0.7,
        help="Test difficulty (0.0 to 1.0)"
    )
    parser.add_argument(
        "--management-mode",
        choices=["conservative", "balanced", "aggressive", "adaptive"],
        default="adaptive",
        help="Self-management mode"
    )
    
    args = parser.parse_args()
    
    # Initialize system
    system = AutonomousLidarSystem(args.vehicle_id, args.sensor_range)
    
    # Start system
    system.start()
    
    try:
        # Set management mode
        system.set_management_mode(args.management_mode)
        
        if args.mode == "demo":
            # Run demo
            logger.info("Running demo mode...")
            
            # Simulate sonar data
            for i in range(10):
                left = 10.0 + i * 0.5
                right = 10.0 + i * 0.5
                result = system.process_sonar_data(left, right)
                logger.info(f"Step {i}: {result}")
                time.sleep(0.5)
            
            # Calibrate to map
            region = (37.0, 38.0, -122.0, -121.0)
            cal_result = system.calibrate_to_map(region)
            logger.info(f"Calibration: {cal_result}")
            
            # Plan path
            start = Coordinate(0.0, 0.0, 0.0, 0.0)
            end = Coordinate(50.0, 50.0, 50.0, 0.0)
            path_result = system.plan_path(start, end)
            logger.info(f"Path planning: {path_result}")
            
        elif args.mode == "navigate":
            # Navigate to target
            if args.target_x is None or args.target_y is None:
                logger.error("Target coordinates required for navigation mode")
                return
            
            target = Coordinate(args.target_x, args.target_x, args.target_y, 0.0)
            nav_result = system.navigate(target, args.duration)
            logger.info(f"Navigation result: {nav_result}")
            
        elif args.mode == "test":
            # Run single virtual test
            if not args.scenario_type:
                logger.error("Scenario type required for test mode")
                return
            
            logger.info(f"Running virtual test: {args.scenario_type}")
            test_result = system.run_virtual_test(args.scenario_type, args.difficulty)
            logger.info(f"Test result: {json.dumps(test_result, indent=2)}")
            
            # Coordinate parameters based on test result
            coord_result = system.coordinate_parameters(args.scenario_type, args.difficulty)
            logger.info(f"Parameter coordination: {json.dumps(coord_result, indent=2)}")
            
        elif args.mode == "comprehensive-test":
            # Run comprehensive test suite
            logger.info("Running comprehensive test suite...")
            results = system.run_comprehensive_test_suite()
            logger.info(f"Test suite results: {json.dumps(results, indent=2)}")
            
            # Print summary
            summary = system.virtual_test_layer.get_test_summary()
            logger.info(f"Test summary: {json.dumps(summary, indent=2)}")
            
        else:
            # Interactive mode
            logger.info("Interactive mode - system ready")
            logger.info("Use the programmatic API for advanced operations")
            
            # Print status
            status = system.get_system_status()
            logger.info(f"System status: {json.dumps(status, indent=2)}")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    
    finally:
        # Stop system
        system.stop()
        
        # Save state
        system.save_state("system_state.json")
        
        logger.info("System shutdown complete")


if __name__ == "__main__":
    main()
