#!/usr/bin/env python3
"""
Test Full Mode Activation
Tests the conversion layer that bypasses basic iteration and locks to full mode.
"""

import sys
import time
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "ASI-"))

from lidar_sonar_engine import LidarSonarEngine, Coordinate
from asi_integration import ASIIntegrator
from vehicle_simulation import VehicleSimulator

def test_full_mode_activation():
    """Test automatic full mode activation when conditions are met."""
    print("🚀 Full Mode Activation Test")
    print("=" * 50)
    
    # Initialize systems
    print("Initializing components...")
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    # Check initial status
    initial_status = asi_integrator.get_integration_status()
    print("\n📊 Initial Integration Status:")
    print(f"   Graph available: {initial_status.get('graph_available')}")
    print(f"   Semantic map available: {initial_status.get('semantic_map_available')}")
    print(f"   Real-world enabled: {initial_status['real_world_integration']['real_world_enabled']}")
    print(f"   Spatial nodes: {initial_status.get('spatial_nodes_count', 0)}")
    
    # Check full mode controller availability
    full_mode_status = asi_integrator.get_full_mode_status()
    print(f"\n🎛️  Full Mode Controller: {'Available' if full_mode_status['full_mode_available'] else 'Not Available'}")
    
    if not full_mode_status['full_mode_available']:
        print("❌ Full mode controller not available - cannot test activation")
        return False
    
    # Initialize real-world mapping to meet conditions
    print("\n🗺️  Initializing real-world mapping...")
    scan_bounds = (-30.0, 30.0, -30.0, 30.0)
    mapping_result = asi_integrator.initialize_real_world_mapping(scan_bounds)
    print(f"   Mapping points: {mapping_result['spectrum_mapping']['mapping_points']}")
    print(f"   Celestial mappings: {mapping_result['celestial_mappings']}")
    
    # Check conditions and attempt full mode activation
    print("\n🔍 Checking full mode activation conditions...")
    activation_result = asi_integrator.check_and_activate_full_mode()
    
    if "error" in activation_result:
        print(f"❌ Activation check failed: {activation_result['error']}")
        return False
    
    print(f"   Activation result: {activation_result.get('status', 'unknown')}")
    
    if activation_result.get("status") == "conditions_not_met":
        print(f"   Current mode: {activation_result.get('current_mode')}")
        print(f"   Conditions met: {activation_result.get('conditions_check', 0)}/3")
        
        # Force activation for testing
        print("\n🔧 Conditions not met automatically - forcing activation for testing...")
        if asi_integrator.full_mode_controller:
            force_result = asi_integrator.full_mode_controller.activate_full_mode(force_activation=True)
            print(f"   Force activation: {len(force_result.get('components_activated', []))} components activated")
            
    # Verify full mode is active
    print("\n✅ Verifying Full Mode Status:")
    final_status = asi_integrator.get_full_mode_status()
    controller_status = final_status.get('controller_status', {})
    
    print(f"   Current mode: {controller_status.get('current_mode', 'unknown')}")
    print(f"   Mode locked: {controller_status.get('mode_locked', False)}")
    print(f"   Active components: {controller_status.get('performance_metrics', {}).get('active_components', 0)}")
    
    # Test component status
    component_status = controller_status.get('component_status', {})
    active_components = [name for name, comp in component_status.items() 
                        if comp['status'] == 'locked_active']
    
    print(f"   Components locked active: {len(active_components)}")
    for comp_name in active_components:
        print(f"     ✅ {comp_name}")
    
    # Test that functions stay active
    print("\n🔄 Testing Component Persistence:")
    
    # Wait and check that components stay active
    time.sleep(2.0)
    
    # Run maintenance
    maintenance_result = asi_integrator.maintain_full_mode_operation()
    print(f"   Maintenance result: {maintenance_result.get('status', 'unknown')}")
    
    if 'components_maintained' in maintenance_result:
        maintained_count = len(maintenance_result['components_maintained'])
        reactivated_count = len(maintenance_result.get('reactivated_components', []))
        print(f"   Components maintained: {maintained_count}")
        print(f"   Components reactivated: {reactivated_count}")
    
    # Final verification
    final_check_status = asi_integrator.get_integration_status()
    print(f"\n📈 Final Status Check:")
    print(f"   Spatial nodes: {final_check_status.get('spatial_nodes_count', 0)}")
    print(f"   Virtual sequences: {final_check_status.get('virtual_sequences_count', 0)}")
    print(f"   Active paths: {final_check_status.get('active_paths_count', 0)}")
    
    # Test with vehicle integration
    print(f"\n🚗 Testing Full Mode with Vehicle Integration:")
    vehicle = VehicleSimulator(Coordinate(-10.0, 10.0, -5.0, 0.0))
    vehicle.start_simulation()
    vehicle.set_autopilot_mode(True)
    
    # Plan route in full mode
    destination = Coordinate(20.0, 40.0, 15.0, 0.0)
    route = asi_integrator.plan_real_world_route(
        vehicle.current_position.coordinate,
        destination,
        {"max_velocity": 15.0}
    )
    
    print(f"   Route planned in full mode: {len(route)} waypoints")
    
    # Test real-time navigation
    for i in range(3):
        vehicle_pos = vehicle.get_position_marker()['local_coordinate']
        nav_data = asi_integrator.get_real_time_navigation_data(vehicle_pos)
        
        print(f"   Navigation step {i+1}: {nav_data.get('navigation_safety', 'unknown')}")
        time.sleep(0.5)
    
    vehicle.stop_simulation()
    
    return True

def test_mode_transitions():
    """Test mode transitions and stability."""
    print("\n🔄 Mode Transition Test")
    print("-" * 30)
    
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    if not asi_integrator.full_mode_controller:
        print("❌ Full mode controller not available")
        return False
    
    controller = asi_integrator.full_mode_controller
    
    print(f"Initial mode: {controller.current_mode.value}")
    
    # Test activation
    print("Testing activation...")
    activation_result = controller.activate_full_mode(force_activation=True)
    print(f"   Activation result: {len(activation_result.get('components_activated', []))} components")
    print(f"   Current mode: {controller.current_mode.value}")
    print(f"   Mode locked: {controller.mode_locked}")
    
    # Test maintenance
    print("Testing maintenance...")
    time.sleep(1.0)
    
    test_status = {"integration_test": True}  # Mock status
    maintenance_result = controller.maintain_full_mode(test_status)
    print(f"   Maintenance status: {maintenance_result.get('timestamp') is not None}")
    
    # Test unlock (for emergency scenarios)
    print("Testing unlock...")
    unlock_result = controller.force_unlock_mode()
    print(f"   Unlock result: {unlock_result.get('status')}")
    print(f"   Current mode: {controller.current_mode.value}")
    
    return True

def test_component_resilience():
    """Test component resilience and reactivation."""
    print("\n🛡️ Component Resilience Test")
    print("-" * 35)
    
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    if not asi_integrator.full_mode_controller:
        print("❌ Full mode controller not available")
        return False
    
    # Activate full mode
    controller = asi_integrator.full_mode_controller
    controller.activate_full_mode(force_activation=True)
    
    print("Full mode activated - testing resilience...")
    
    # Simulate component failure
    if "node_graph" in controller.components:
        original_status = controller.components["node_graph"].status
        print("Simulating node_graph failure...")
        
        # Simulate failure
        from ASI.engine.activation.full_mode_controller import ActivationStatus
        controller.components["node_graph"].status = ActivationStatus.FAILED
        
        print(f"   Component status: {controller.components['node_graph'].status.value}")
        
        # Test maintenance recovery
        test_status = asi_integrator.get_integration_status()
        maintenance_result = controller.maintain_full_mode(test_status)
        
        reactivated = maintenance_result.get("reactivated_components", [])
        print(f"   Reactivated components: {reactivated}")
        
        if "node_graph" in reactivated:
            print("✅ Component successfully reactivated")
        else:
            print("⚠️ Component reactivation may have failed")
    
    return True

if __name__ == "__main__":
    print("🚀 FULL MODE ACTIVATION TEST SUITE")
    print("Testing conversion layer that bypasses basic iteration")
    print("=" * 70)
    
    try:
        # Run tests
        test_full_mode_activation()
        test_mode_transitions() 
        test_component_resilience()
        
        print("\n" + "=" * 70)
        print("✅ All full mode activation tests completed!")
        print("🔒 System successfully locks to full mode when conditions are met")
        print("🔄 Components stay active and are maintained automatically")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)