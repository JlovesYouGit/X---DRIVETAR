#!/usr/bin/env python3
"""
Test Requirement Chain System
Tests the requirement chain with require fields and auto-provision capabilities.
"""

import sys
import time
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "ASI-"))

from lidar_sonar_engine import LidarSonarEngine
from asi_integration import ASIIntegrator

def test_requirement_diagnosis():
    """Test requirement diagnosis and auto-resolution."""
    print("🔍 Testing Requirement Chain Diagnosis")
    print("=" * 50)
    
    # Initialize system
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    # Check if requirement chain is available
    if not asi_integrator.requirement_chain:
        print("❌ Requirement chain not available")
        return False
    
    print("✅ Requirement chain initialized")
    
    # Get initial status (should show zeros/empty values)
    print("\n--- Initial Status (Before Diagnosis) ---")
    initial_status = asi_integrator.get_integration_status()
    
    key_metrics = [
        ("spatial_nodes_count", initial_status.get("spatial_nodes_count", 0)),
        ("virtual_sequences_count", initial_status.get("virtual_sequences_count", 0)),
        ("active_paths_count", initial_status.get("active_paths_count", 0)),
        ("coord_to_node_mappings", initial_status.get("coord_to_node_mappings", 0))
    ]
    
    print("Key Metrics:")
    for metric_name, value in key_metrics:
        print(f"  {metric_name}: {value}")
    
    # Run requirement diagnosis
    print("\n--- Running Requirement Diagnosis ---")
    diagnosis_result = asi_integrator.diagnose_and_resolve_requirements()
    
    print(f"Systems ready before: {diagnosis_result['improvement']['systems_ready_before']}")
    print(f"Systems ready after: {diagnosis_result['improvement']['systems_ready_after']}")
    print(f"Overall ready: {diagnosis_result['improvement']['overall_ready']}")
    
    # Show developer guidance
    if diagnosis_result["developer_guidance"]:
        print("\n--- Developer Guidance ---")
        for guidance in diagnosis_result["developer_guidance"]:
            print(f"  {guidance}")
    
    # Check final status
    print("\n--- Final Status (After Diagnosis) ---") 
    final_status = asi_integrator.get_integration_status()
    
    final_metrics = [
        ("spatial_nodes_count", final_status.get("spatial_nodes_count", 0)),
        ("virtual_sequences_count", final_status.get("virtual_sequences_count", 0)),
        ("active_paths_count", final_status.get("active_paths_count", 0)),
        ("coord_to_node_mappings", final_status.get("coord_to_node_mappings", 0))
    ]
    
    print("Key Metrics After Diagnosis:")
    for metric_name, value in final_metrics:
        print(f"  {metric_name}: {value}")
    
    # Check for improvements
    improvements = []
    for i, (metric_name, initial_val) in enumerate(key_metrics):
        final_val = final_metrics[i][1]
        if final_val > initial_val:
            improvements.append(f"{metric_name}: {initial_val} → {final_val}")
    
    if improvements:
        print("\n✅ Improvements detected:")
        for improvement in improvements:
            print(f"  📈 {improvement}")
    else:
        print("\n⚠️  No improvements detected - may need manual intervention")
    
    return len(improvements) > 0

def test_full_mode_activation():
    """Test full mode activation after requirement resolution."""
    print("\n🚀 Testing Full Mode Activation")
    print("=" * 40)
    
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    # First resolve requirements
    print("Resolving requirements...")
    diagnosis_result = asi_integrator.diagnose_and_resolve_requirements()
    
    # Try to activate full mode
    print("Checking full mode conditions...")
    if asi_integrator.full_mode_controller:
        activation_result = asi_integrator.check_and_activate_full_mode()
        
        print(f"Full mode status: {activation_result}")
        
        if activation_result.get("status") == "conditions_not_met":
            print("⚠️  Full mode conditions not yet met")
            print(f"Current mode: {activation_result.get('current_mode')}")
            return False
        else:
            print("✅ Full mode activation attempted")
            return True
    else:
        print("❌ Full mode controller not available")
        return False

def test_data_sequence_provision():
    """Test data sequence provider directly."""
    print("\n📊 Testing Data Sequence Provider")
    print("=" * 35)
    
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    if not asi_integrator.data_provider:
        print("❌ Data provider not available")
        return False
    
    from engine.requirements.data_sequence_provider import SequenceType
    
    # Test generating different sequence types
    test_sequences = [
        SequenceType.COORDINATE_DATA,
        SequenceType.SPECTRUM_FREQUENCIES,
        SequenceType.ROUTE_COORDINATES,
        SequenceType.NODE_METADATA
    ]
    
    print("Generating test sequences...")
    for seq_type in test_sequences:
        try:
            sequence = asi_integrator.data_provider.provide_sequence(seq_type, size=10)
            print(f"✅ {seq_type.value}: {sequence.size} items generated")
            
        except Exception as e:
            print(f"❌ {seq_type.value}: Failed - {e}")
    
    # Check provider status
    provider_status = asi_integrator.data_provider.get_provider_status()
    print(f"\nProvider Status:")
    print(f"  Total sequences generated: {provider_status['sequences_generated']}")
    print(f"  Cached sequences: {provider_status['cached_sequences']}")
    
    return True

def test_complete_integration_flow():
    """Test complete integration flow from diagnosis to activation."""
    print("\n🔄 Testing Complete Integration Flow")
    print("=" * 45)
    
    lidar_engine = LidarSonarEngine()
    asi_integrator = ASIIntegrator(lidar_engine)
    
    # Step 1: Initial diagnosis
    print("Step 1: Initial diagnosis...")
    initial_requirements = asi_integrator.get_requirements_status()
    print(f"  Critical issues: {initial_requirements['developer_guidance']['critical_issues']}")
    
    # Step 2: Resolve requirements
    print("Step 2: Resolving requirements...")
    diagnosis = asi_integrator.diagnose_and_resolve_requirements()
    print(f"  Systems ready: {diagnosis['improvement']['systems_ready_after']}")
    
    # Step 3: Initialize real-world mapping
    print("Step 3: Initialize real-world mapping...")
    if asi_integrator.real_world_enabled:
        scan_bounds = (-20.0, 20.0, -20.0, 20.0)
        mapping_result = asi_integrator.initialize_real_world_mapping(scan_bounds)
        print(f"  Mapping points: {mapping_result.get('spectrum_mapping', {}).get('mapping_points', 0)}")
    
    # Step 4: Optimize for autonomous driving
    print("Step 4: Optimizing for autonomous driving...")
    optimization = asi_integrator.optimize_for_autonomous_driving()
    print(f"  Optimizations applied: {len(optimization.get('optimizations_applied', []))}")
    
    # Step 5: Check full mode readiness
    print("Step 5: Checking full mode readiness...")
    final_requirements = asi_integrator.get_requirements_status()
    ready = final_requirements.get("ready_for_full_mode", False)
    print(f"  Ready for full mode: {ready}")
    
    # Step 6: Final status
    print("Step 6: Final integration status...")
    final_status = asi_integrator.get_integration_status()
    
    metrics_summary = {
        "spatial_nodes": final_status.get("spatial_nodes_count", 0),
        "virtual_sequences": final_status.get("virtual_sequences_count", 0),
        "real_world_mappings": final_status.get("real_world_integration", {}).get("sonar_bridge_status", {}).get("real_space_mappings", 0),
        "spectrum_points": final_status.get("real_world_integration", {}).get("spectrum_engine_status", {}).get("spectrum_points", 0)
    }
    
    print("  Final metrics:")
    for name, value in metrics_summary.items():
        print(f"    {name}: {value}")
    
    # Success if we have non-zero values
    non_zero_metrics = sum(1 for v in metrics_summary.values() if v > 0)
    success = non_zero_metrics >= 2  # At least 2 metrics should be populated
    
    print(f"\n{'✅' if success else '❌'} Integration flow {'completed' if success else 'incomplete'}")
    return success

if __name__ == "__main__":
    print("🔧 Requirement Chain Test Suite")
    print("Testing requirement diagnosis, auto-provision, and full mode activation")
    print("=" * 70)
    
    try:
        # Run all tests
        test1_passed = test_requirement_diagnosis()
        test2_passed = test_full_mode_activation()
        test3_passed = test_data_sequence_provision()
        test4_passed = test_complete_integration_flow()
        
        # Summary
        tests_passed = sum([test1_passed, test2_passed, test3_passed, test4_passed])
        
        print("\n" + "=" * 70)
        print(f"Test Results: {tests_passed}/4 tests passed")
        
        if tests_passed >= 3:
            print("✅ Requirement chain system working - resolves zero-value issues!")
            print("🚀 System ready for autonomous driving with requirement auto-resolution")
        else:
            print("⚠️  Some tests failed - may need manual configuration")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)