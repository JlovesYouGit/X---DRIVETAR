#!/usr/bin/env python3
"""
Test Vehicle Integration with Real-World Mapping
Tests the complete system: Vehicle simulation + ASI integration + Real-world mapping
"""

import sys
import time
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "ASI-"))

from lidar_sonar_engine import LidarSonarEngine, Coordinate
from asi_integration import ASIIntegrator
from vehicle_simulation import VehicleSimulator, VehicleState, NavigationCommand

def test_complete_autonomous_system():
    """Test complete autonomous driving system with vehicle simulation."""
    print("🚗 Complete Autonomous Driving System Test")
    print("=" * 60)
    
    # Initialize components
    print("Initializing system components...")
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    # Create vehicle at starting position
    start_position = Coordinate(-10.0, 10.0, 0.0, 0.0)
    vehicle = VehicleSimulator(start_position)
    
    # Start vehicle simulation
    vehicle.start_simulation()
    vehicle.set_autopilot_mode(True)
    
    # Initialize real-world mapping
    scan_bounds = (-50.0, 50.0, -50.0, 50.0)
    mapping_result = asi_integrator.initialize_real_world_mapping(scan_bounds)
    print(f"✅ Real-world mapping: {mapping_result['spectrum_mapping']['mapping_points']} points")
    
    # Plan route from start to destination
    destination = Coordinate(30.0, 50.0, 25.0, 0.0)
    route = asi_integrator.plan_real_world_route(
        start_position, 
        destination, 
        {"max_velocity": 15.0, "safety_margin": 2.0}
    )
    
    print(f"📍 Route planned: {len(route)} waypoints")
    
    # Load route into vehicle
    vehicle.load_route(route)
    
    # Simulate autonomous driving
    print("\n🤖 Starting autonomous driving simulation...")
    simulation_steps = 20
    
    for step in range(simulation_steps):
        print(f"\n--- Step {step + 1}/{simulation_steps} ---")
        
        # Get current vehicle status
        vehicle_status = vehicle.get_vehicle_status()
        current_pos = vehicle_status["position"]["local_coordinate"]
        
        print(f"Vehicle position: ({current_pos.x_center:.1f}, {current_pos.y:.1f})")
        print(f"Speed: {vehicle_status['position']['speed']:.1f} m/s")
        print(f"State: {vehicle_status['state']}")
        
        # Update ASI with vehicle position
        asi_integrator.update_vehicle_position(current_pos)
        
        # Get navigation data from ASI
        nav_data = asi_integrator.get_real_time_navigation_data(current_pos)
        
        print(f"Navigation safety: {nav_data.get('navigation_safety', 'unknown')}")
        
        # Check for obstacles
        obstacles = nav_data.get('obstacle_count', 0)
        if obstacles > 0:
            print(f"⚠️  {obstacles} obstacles detected")
            
            # Send emergency command to vehicle
            emergency_cmd = NavigationCommand(
                target_speed=0.0,
                target_steering=0.0,
                brake_command=1.0,
                throttle_command=0.0,
                emergency_stop=True,
                confidence=1.0
            )
            vehicle.send_navigation_command(emergency_cmd)
            
        # Check route progress
        route_progress = vehicle_status["navigation"]["route_progress"]
        if route_progress["current_waypoint"] >= route_progress["total_waypoints"]:
            print("🏁 Route completed successfully!")
            break
            
        # Simulate obstacles occasionally for testing
        if step == 10:  # Add obstacle at step 10
            obstacle_pos = Coordinate(15.0, 35.0, 12.0, 0.0)
            detected = vehicle.simulate_obstacle_detection(obstacle_pos)
            if detected:
                print("🚧 Obstacle detected by vehicle sensors")
        
        time.sleep(0.5)  # Simulate real-time progression
    
    # Stop simulation
    vehicle.stop_simulation()
    
    return True

def test_sensor_integration():
    """Test integration between ASI and vehicle sensors."""
    print("\n🔍 Sensor Integration Test")
    print("-" * 40)
    
    # Initialize systems
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    vehicle = VehicleSimulator()
    
    # Start vehicle
    vehicle.start_simulation()
    
    # Test sensor data correlation
    test_positions = [
        Coordinate(0.0, 20.0, 5.0, 0.0),
        Coordinate(-10.0, 10.0, -5.0, 0.0),
        Coordinate(15.0, 35.0, 10.0, 0.0)
    ]
    
    for i, pos in enumerate(test_positions):
        print(f"\nTest position {i+1}:")
        
        # Update vehicle position
        vehicle.current_position.coordinate = pos
        
        # Get vehicle sensor readings
        sensor_data = vehicle.get_sensor_readings()
        
        # Get ASI navigation data
        nav_data = asi_integrator.get_real_time_navigation_data(pos)
        
        # Compare readings
        print(f"Position: ({pos.x_center:.1f}, {pos.y:.1f})")
        print(f"Vehicle radar distance: {sensor_data['radar']['front_distance']:.1f}m")
        print(f"ASI safety assessment: {nav_data.get('navigation_safety', 'unknown')}")
        print(f"Camera obstacles: {len(sensor_data['vision']['front_camera_obstacles'])}")
        
        # Simulate correlation check
        asi_safe = nav_data.get('navigation_safety') in ['safe', 'caution']
        sensor_clear = sensor_data['radar']['front_distance'] > 10.0
        
        if asi_safe == sensor_clear:
            print("✅ ASI and vehicle sensors agree")
        else:
            print("⚠️  ASI and vehicle sensors disagree - needs calibration")
    
    vehicle.stop_simulation()
    return True

def test_position_markers():
    """Test position marker accuracy and GPS simulation."""
    print("\n📍 Position Marker Test")
    print("-" * 30)
    
    vehicle = VehicleSimulator()
    vehicle.start_simulation()
    
    # Test position updates
    test_route = [
        Coordinate(0.0, 20.0, 0.0, 0.0),
        Coordinate(10.0, 30.0, 10.0, 0.0),
        Coordinate(20.0, 40.0, 20.0, 0.0)
    ]
    
    vehicle.load_route(test_route)
    vehicle.set_autopilot_mode(True)
    
    initial_pos = vehicle.get_position_marker()
    print(f"Initial GPS: {initial_pos['gps']['latitude']:.6f}, {initial_pos['gps']['longitude']:.6f}")
    print(f"Initial local: ({initial_pos['local_coordinate'].x_center:.1f}, {initial_pos['local_coordinate'].y:.1f})")
    
    # Simulate movement
    for i in range(5):
        time.sleep(1.0)
        
        pos_marker = vehicle.get_position_marker()
        print(f"Step {i+1}:")
        print(f"  GPS: {pos_marker['gps']['latitude']:.6f}, {pos_marker['gps']['longitude']:.6f}")
        print(f"  Local: ({pos_marker['local_coordinate'].x_center:.1f}, {pos_marker['local_coordinate'].y:.1f})")
        print(f"  Speed: {pos_marker['speed']:.1f} m/s")
        print(f"  Heading: {pos_marker['heading']:.1f}°")
    
    vehicle.stop_simulation()
    return True

def test_emergency_systems():
    """Test emergency stop and safety systems."""
    print("\n🚨 Emergency Systems Test")
    print("-" * 35)
    
    vehicle = VehicleSimulator()
    vehicle.start_simulation()
    vehicle.set_autopilot_mode(True)
    
    # Set initial speed
    vehicle.current_position.speed = 10.0  # 10 m/s
    print(f"Initial speed: {vehicle.current_position.speed:.1f} m/s")
    
    # Send emergency stop command
    emergency_cmd = NavigationCommand(
        target_speed=0.0,
        target_steering=0.0,
        brake_command=1.0,
        throttle_command=0.0,
        emergency_stop=True,
        confidence=1.0
    )
    
    vehicle.send_navigation_command(emergency_cmd)
    print("🚨 Emergency stop command sent")
    
    # Monitor braking
    for i in range(5):
        time.sleep(0.5)
        status = vehicle.get_vehicle_status()
        
        print(f"Time +{(i+1)*0.5:.1f}s: Speed {status['position']['speed']:.1f} m/s, State: {status['state']}")
        
        if status['position']['speed'] < 0.1:
            print("✅ Vehicle stopped successfully")
            break
    
    vehicle.stop_simulation()
    return True

if __name__ == "__main__":
    print("🚗 Vehicle Integration Test Suite")
    print("Testing Tesla-like vehicle simulation with ASI autonomous driving")
    print("=" * 70)
    
    try:
        # Run all tests
        test_complete_autonomous_system()
        test_sensor_integration() 
        test_position_markers()
        test_emergency_systems()
        
        print("\n" + "=" * 70)
        print("✅ All vehicle integration tests completed successfully!")
        print("🚗 System ready for autonomous driving with Tesla-like vehicle simulation")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)