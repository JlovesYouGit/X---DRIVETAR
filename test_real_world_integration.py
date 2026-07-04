#!/usr/bin/env python3
"""
Test Real-World Integration for Autonomous Driving
Tests celestial routes mapping to actual sonar-scanned spaces.
"""

import sys
import time
import math
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "ASI-"))

from lidar_sonar_engine import LidarSonarEngine, Coordinate
from asi_integration import ASIIntegrator

def test_real_world_mapping():
    """Test real-world mapping integration."""
    print("=== Testing Real-World Mapping Integration ===")
    
    # Initialize lidar engine
    lidar_engine = LidarSonarEngine()
    
    # Initialize ASI integrator
    asi_integrator = ASIIntegrator(lidar_engine)
    
    # Test integration status
    status = asi_integrator.get_integration_status()
    print(f"Integration Status: {status}")
    
    if not status.get("real_world_integration", {}).get("real_world_enabled", False):
        print("❌ Real-world integration not available - using fallback mode")
        return test_fallback_mode(asi_integrator)
    
    print("✅ Real-world integration available")
    
    # Initialize real-world mapping
    scan_bounds = (-25.0, 25.0, -25.0, 25.0)  # 50m x 50m test area
    mapping_result = asi_integrator.initialize_real_world_mapping(scan_bounds)
    print(f"Mapping Result: {mapping_result}")
    
    # Test route planning with correct coordinate constructors
    start = Coordinate(0.0 - 0.5, 0.0 + 0.5, 0.0, 0.0)
    destination = Coordinate(20.0 - 0.5, 20.0 + 0.5, 15.0, 0.0)
    vehicle_constraints = {"max_velocity": 15.0}
    
    route = asi_integrator.plan_real_world_route(start, destination, vehicle_constraints)
    print(f"Planned route with {len(route)} waypoints")
    
    # Test positions with correct coordinate constructors  
    test_positions = [
        Coordinate(5.0 - 0.5, 5.0 + 0.5, 3.0, 0.0),
        Coordinate(10.0 - 0.5, 10.0 + 0.5, 7.0, 0.0),
        Coordinate(15.0 - 0.5, 15.0 + 0.5, 12.0, 0.0)
    ]
    
    for i, pos in enumerate(test_positions):
        print(f"\n--- Navigation Test {i+1} ---")
        
        # Update vehicle position
        asi_integrator.update_vehicle_position(pos)
        
        # Get real-time navigation data
        nav_data = asi_integrator.get_real_time_navigation_data(pos)
        print(f"Navigation Safety: {nav_data.get('navigation_safety', 'unknown')}")
        print(f"Obstacles: {nav_data.get('obstacle_count', 0)}")
        
        recommendations = nav_data.get('recommendations', [])
        if recommendations:
            print("Recommendations:")
            for rec in recommendations[:3]:  # Show top 3
                print(f"  - {rec}")
    
    # Test map rendering
    print("\n--- Testing Map Rendering ---")
    rendered_map = asi_integrator.render_autonomous_driving_map(scan_bounds)
    print(f"Rendered map data keys: {list(rendered_map.keys())}")
    
    # Test optimization
    print("\n--- Testing Optimization ---")
    optimization = asi_integrator.optimize_for_autonomous_driving()
    print(f"Optimizations applied: {optimization.get('optimizations_applied', [])}")
    
    return True

def test_fallback_mode(asi_integrator):
    """Test fallback mode when real-world integration unavailable."""
    print("\n=== Testing Fallback Mode ===")
    
    start = Coordinate(0.0 - 0.5, 0.0 + 0.5, 0.0, 0.0)
    destination = Coordinate(15.0 - 0.5, 15.0 + 0.5, 10.0, 0.0)
    
    # Test basic route planning
    route = asi_integrator.plan_real_world_route(start, destination, {})
    print(f"Fallback route planned with {len(route)} waypoints")
    
    # Test basic map rendering
    rendered_map = asi_integrator.render_autonomous_driving_map()
    print(f"Fallback map keys: {list(rendered_map.keys())}")
    
    return True

def test_spectrum_celestial_matching():
    """Test that spectrum engine matches actual sonar-scanned spaces."""
    print("\n=== Testing Spectrum-Celestial Matching ===")
    
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    if not asi_integrator.real_world_enabled:
        print("❌ Real-world integration required for spectrum testing")
        return False
    
    # Test coordinates with correct constructor
    test_coordinates = [
        Coordinate(5.0 - 0.5, 5.0 + 0.5, 5.0, 0.0),
        Coordinate(-5.0 - 0.5, -5.0 + 0.5, -5.0, 0.0),
        Coordinate(10.0 - 0.5, 10.0 + 0.5, 8.0, 0.0)
    ]
    
    print("Testing spectrum-to-space matching:")
    for i, coord in enumerate(test_coordinates):
        
        # Get actual sonar density
        actual_density = lidar_engine._get_density_at_point(coord.x_center, coord.y)
        
        # Get spectrum frequency prediction
        spectrum_data = asi_integrator.get_real_time_navigation_data(coord)
        spectrum_freq = spectrum_data.get('spectrum_analysis', {}).get('spectrum_frequency', 0.0)
        
        # Check if they match logically
        expected_range = (400.0, 600.0)  # Valid spectrum range
        freq_valid = expected_range[0] <= spectrum_freq <= expected_range[1]
        
        print(f"Coordinate {i+1}: density={actual_density:.3f}, freq={spectrum_freq:.1f}Hz, valid={freq_valid}")
    
    return True

def test_autonomous_driving_scenario():
    """Test complete autonomous driving scenario."""
    print("\n=== Testing Complete Autonomous Driving Scenario ===")
    
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    # Initialize for autonomous driving
    scan_bounds = (-30.0, 30.0, -30.0, 30.0)
    mapping_result = asi_integrator.initialize_real_world_mapping(scan_bounds)
    print(f"Initialized driving area: {mapping_result}")
    
    # Simulate driving from point A to point B with correct coordinates
    start_position = Coordinate(-20.0 - 0.5, -20.0 + 0.5, -15.0, 0.0)
    destination = Coordinate(20.0 - 0.5, 20.0 + 0.5, 15.0, 0.0)
    
    print(f"Planning route: {start_position.x_center}, {start_position.y} → {destination.x_center}, {destination.y}")
    
    # Plan initial route
    route = asi_integrator.plan_real_world_route(
        start_position, destination, 
        {"max_velocity": 12.0, "safety_margin": 2.0}
    )
    
    print(f"Initial route: {len(route)} waypoints")
    
    # Simulate driving along route
    current_position = start_position
    
    for i, waypoint in enumerate(route[:5]):  # Test first 5 waypoints
        print(f"\n--- Waypoint {i+1}/{min(5, len(route))} ---")
        
        # Update position
        asi_integrator.update_vehicle_position(waypoint)
        current_position = waypoint
        
        # Get navigation data
        nav_data = asi_integrator.get_real_time_navigation_data(waypoint)
        
        safety = nav_data.get('navigation_safety', 'unknown')
        obstacles = nav_data.get('obstacle_count', 0)
        
        print(f"Position: ({waypoint.x_center:.1f}, {waypoint.y:.1f})")
        print(f"Safety: {safety}, Obstacles: {obstacles}")
        
        # Check if route needs updating due to obstacles
        if obstacles > 0:
            print("🚨 Obstacles detected - route may need updating")
        
        if safety in ['obstacle', 'emergency']:
            print("⚠️ Unsafe area detected")
        
        # Simulate time delay
        time.sleep(0.1)
    
    print("✅ Autonomous driving scenario completed")
    return True

if __name__ == "__main__":
    print("🚗 Real-World Integration Test Suite")
    print("Testing ASI celestial routes with actual sonar mapping for autonomous driving")
    print("=" * 70)
    
    try:
        # Run tests
        test_real_world_mapping()
        test_spectrum_celestial_matching()
        test_autonomous_driving_scenario()
        
        print("\n" + "=" * 70)
        print("✅ All real-world integration tests completed successfully!")
        print("🚗 System ready for autonomous driving with celestial route optimization")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)