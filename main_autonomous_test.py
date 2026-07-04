#!/usr/bin/env python3
"""
Main Autonomous Driving Test
Complete integration test: ASI + Real-World Mapping + Vehicle Simulation
"""

import sys
import time
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "ASI-"))

from main import AutonomousLidarSystem
from vehicle_simulation import VehicleSimulator, NavigationCommand
from lidar_sonar_engine import Coordinate

def main():
    """Main autonomous driving test combining all systems."""
    print("🚗 AUTONOMOUS DRIVING SYSTEM - COMPLETE INTEGRATION TEST")
    print("=" * 70)
    print("Testing: LiDAR Engine + ASI Integration + Real-World Mapping + Vehicle Simulation")
    print()
    
    try:
        # Initialize complete autonomous system
        print("🔧 Initializing Autonomous LiDAR System...")
        autonomous_system = AutonomousLidarSystem()
        
        # Initialize vehicle simulator  
        print("🚗 Starting Vehicle Simulation (Tesla-like systems)...")
        start_position = Coordinate(-25.0, 25.0, -20.0, 0.0)
        vehicle = VehicleSimulator(start_position)
        vehicle.start_simulation()
        vehicle.set_autopilot_mode(True)
        
        print("✅ System initialization complete\n")
        
        # Start the autonomous system
        print("🚀 Starting autonomous navigation system...")
        autonomous_system.start()
        
        # Define mission parameters
        destination = Coordinate(25.0, 75.0, 30.0, 0.0)
        print(f"🎯 Mission: Navigate from ({start_position.x_center:.1f}, {start_position.y:.1f}) to ({destination.x_center:.1f}, {destination.y:.1f})")
        
        # Plan route using ASI integration
        route = autonomous_system.asi_integrator.plan_real_world_route(
            start_position,
            destination,
            {"max_velocity": 15.0, "safety_margin": 2.5}
        )
        
        print(f"📍 Route planned: {len(route)} waypoints")
        
        # Load route into vehicle
        vehicle.load_route(route)
        
        # Mission execution
        print("\n🤖 AUTONOMOUS MISSION EXECUTION")
        print("-" * 45)
        
        mission_step = 0
        max_mission_steps = 30
        
        while mission_step < max_mission_steps:
            mission_step += 1
            print(f"\n--- Mission Step {mission_step} ---")
            
            # Get current vehicle status
            vehicle_status = vehicle.get_vehicle_status()
            current_pos = vehicle_status["position"]["local_coordinate"]
            
            print(f"Vehicle: ({current_pos.x_center:.1f}, {current_pos.y:.1f}) @ {vehicle_status['position']['speed']:.1f}m/s")
            
            # Update ASI with real-time position
            autonomous_system.asi_integrator.update_vehicle_position(current_pos)
            
            # Get real-time navigation analysis
            nav_analysis = autonomous_system.asi_integrator.get_real_time_navigation_data(current_pos)
            
            # Report navigation status
            safety = nav_analysis.get('navigation_safety', 'unknown')
            obstacles = nav_analysis.get('obstacle_count', 0)
            
            print(f"Navigation: {safety} | Obstacles: {obstacles}")
            
            # Handle safety conditions
            if safety == 'emergency':
                print("🚨 EMERGENCY STOP - Critical obstacle detected!")
                vehicle.send_navigation_command(NavigationCommand(
                    target_speed=0.0, target_steering=0.0, brake_command=1.0,
                    throttle_command=0.0, emergency_stop=True, confidence=1.0
                ))
                break
                
            elif safety == 'obstacle' and obstacles > 0:
                print("⚠️  Obstacle avoidance - reducing speed")
                
            # Check mission progress
            route_progress = vehicle_status["navigation"]["route_progress"]
            progress_pct = (route_progress["current_waypoint"] / route_progress["total_waypoints"] * 100) if route_progress["total_waypoints"] > 0 else 0
            
            print(f"Progress: {progress_pct:.1f}% ({route_progress['current_waypoint']}/{route_progress['total_waypoints']} waypoints)")
            
            # Check if mission completed
            if route_progress["current_waypoint"] >= route_progress["total_waypoints"]:
                print("🏁 MISSION COMPLETED SUCCESSFULLY!")
                break
                
            # Add some test scenarios
            if mission_step == 10:
                print("🧪 Test Scenario: Simulating temporary obstacle...")
                test_obstacle = Coordinate(10.0, 60.0, 15.0, 0.0)
                vehicle.simulate_obstacle_detection(test_obstacle)
                
            if mission_step == 20:
                print("🧪 Test Scenario: Checking route optimization...")
                # Force route update
                updated_route = autonomous_system.asi_integrator.plan_real_world_route(
                    current_pos, destination, {"max_velocity": 12.0}
                )
                vehicle.load_route(updated_route[1:])  # Skip current position
                
            time.sleep(1.0)  # Real-time simulation
        
        # Mission complete
        print(f"\n🎯 Mission Summary:")
        final_status = vehicle.get_vehicle_status()
        final_pos = final_status["position"]["local_coordinate"]
        
        # Calculate mission statistics
        distance_traveled = ((final_pos.x_center - start_position.x_center)**2 + 
                           (final_pos.y - start_position.y)**2)**0.5
        
        print(f"   Final Position: ({final_pos.x_center:.1f}, {final_pos.y:.1f})")
        print(f"   Distance Traveled: {distance_traveled:.1f} meters")
        print(f"   Mission Steps: {mission_step}")
        print(f"   Vehicle State: {final_status['state']}")
        
        # Calculate distance to target
        distance_to_target = ((destination.x_center - final_pos.x_center)**2 + 
                            (destination.y - final_pos.y)**2)**0.5
        
        if distance_to_target < 5.0:  # Within 5 meters
            print("✅ MISSION SUCCESS - Target reached!")
        else:
            print(f"⚠️  Mission stopped {distance_to_target:.1f}m from target")
            
    except Exception as e:
        print(f"\n❌ System error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Shutdown systems
        print("\n🛑 Shutting down systems...")
        try:
            vehicle.stop_simulation()
            autonomous_system.stop()
        except:
            pass
        print("✅ Systems shutdown complete")

if __name__ == "__main__":
    main()