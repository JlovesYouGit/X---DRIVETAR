"""
Requirement Chain — Light-ASI LLM Gateway
Simple chain system with require fields to remind developers what each system needs.
Provides missing data sequences to activate pipeline architectures.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("light-asi.requirements")


class RequireField:
    """
    Simple require field that reminds developers what system components need.
    Unlike error gates, this provides helpful guidance and auto-provision.
    """
    
    def __init__(self, name: str, description: str, required_type: type, 
                 default_provider: Optional[Callable] = None, critical: bool = True):
        self.name = name
        self.description = description  
        self.required_type = required_type
        self.default_provider = default_provider
        self.critical = critical
        self.last_checked = 0.0
        self.provision_count = 0
        
    def check_requirement(self, current_value: Any) -> Dict[str, Any]:
        """Check if requirement is satisfied and provide guidance."""
        
        self.last_checked = time.time()
        
        result = {
            "satisfied": False,
            "current_value": current_value,
            "required_type": self.required_type.__name__,
            "description": self.description,
            "guidance": None,
            "auto_provision_available": self.default_provider is not None
        }
        
        # Check if value exists and matches type
        if current_value is None:
            result["guidance"] = f"REQUIRED: {self.name} is None. {self.description}"
            
        elif not isinstance(current_value, self.required_type):
            result["guidance"] = f"TYPE MISMATCH: {self.name} should be {self.required_type.__name__}, got {type(current_value).__name__}. {self.description}"
            
        elif self.required_type in [list, dict] and len(current_value) == 0:
            result["guidance"] = f"EMPTY COLLECTION: {self.name} is empty. {self.description}"
            
        elif self.required_type in [int, float] and current_value == 0:
            result["guidance"] = f"ZERO VALUE: {self.name} is zero. {self.description}"
            
        else:
            result["satisfied"] = True
            result["guidance"] = f"✅ {self.name} requirement satisfied"
        
        return result
    
    def auto_provision(self) -> Any:
        """Auto-provision default value if provider available."""
        
        if self.default_provider is None:
            return None
            
        try:
            self.provision_count += 1
            provided_value = self.default_provider()
            logger.info(f"Auto-provisioned {self.name}: {type(provided_value).__name__}")
            return provided_value
            
        except Exception as e:
            logger.error(f"Auto-provision failed for {self.name}: {e}")
            return None


@dataclass
class SystemRequirement:
    """Requirement definition for a system component."""
    system_name: str
    require_fields: List[RequireField]
    activation_callback: Optional[Callable] = None
    data_sequence_needs: List[str] = field(default_factory=list)
    architecture_dependencies: List[str] = field(default_factory=list)
    
    def check_all_requirements(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Check all requirements for this system."""
        
        results = {
            "system_name": self.system_name,
            "timestamp": time.time(),
            "requirements_satisfied": 0,
            "total_requirements": len(self.require_fields),
            "critical_failures": [],
            "guidance_messages": [],
            "auto_provisions_needed": [],
            "ready_for_activation": False
        }
        
        for require_field in self.require_fields:
            current_value = system_state.get(require_field.name)
            check_result = require_field.check_requirement(current_value)
            
            if check_result["satisfied"]:
                results["requirements_satisfied"] += 1
            else:
                if require_field.critical:
                    results["critical_failures"].append({
                        "field": require_field.name,
                        "guidance": check_result["guidance"]
                    })
                
                results["guidance_messages"].append(check_result["guidance"])
                
                if check_result["auto_provision_available"]:
                    results["auto_provisions_needed"].append(require_field.name)
        
        # System is ready if all requirements satisfied
        results["ready_for_activation"] = (results["requirements_satisfied"] == results["total_requirements"])
        
        return results


class RequirementChain:
    """
    Simple chain system that checks requirements and provides missing data sequences.
    Reminds developers what each system needs instead of just throwing errors.
    """
    
    def __init__(self):
        self.system_requirements: Dict[str, SystemRequirement] = {}
        self.chain_state: Dict[str, Any] = {}
        self.auto_provision_enabled = True
        self.last_chain_check = 0.0
        
        # Initialize core system requirements
        self._initialize_core_requirements()
    
    def _initialize_core_requirements(self):
        """Initialize requirements for core ASI systems."""
        
        # Node Graph Requirements
        node_graph_fields = [
            RequireField(
                "nodes_count", 
                "Node graph needs at least 10 nodes for basic operation. Creates spatial routing structure.",
                int,
                default_provider=lambda: 50,  # Auto-provision 50 nodes
                critical=True
            ),
            RequireField(
                "node_map_size",
                "Node map dictionary for O(log N) routing. Must contain node ID mappings.",
                int,
                default_provider=lambda: 50,
                critical=True
            ),
            RequireField(
                "router_initialized",
                "ConsistentHashRouter must be initialized for node selection and routing.",
                bool,
                default_provider=lambda: True,
                critical=True
            )
        ]
        
        self.register_system_requirement(SystemRequirement(
            system_name="node_graph",
            require_fields=node_graph_fields,
            data_sequence_needs=["hash_sequences", "node_metadata", "routing_table"],
            architecture_dependencies=["semantic_map"]
        ))
        
        # Spatial Nodes Requirements  
        spatial_nodes_fields = [
            RequireField(
                "spatial_nodes_count",
                "Spatial nodes for coordinate mapping. Need minimum nodes for path planning.",
                int,
                default_provider=self._provide_default_spatial_nodes,
                critical=True
            ),
            RequireField(
                "coord_to_node_mappings",
                "Coordinate-to-node mapping dictionary for spatial lookup and navigation.",
                int,
                default_provider=lambda: 25,
                critical=True
            )
        ]
        
        self.register_system_requirement(SystemRequirement(
            system_name="spatial_nodes",
            require_fields=spatial_nodes_fields,
            data_sequence_needs=["coordinate_data", "density_mappings"],
            architecture_dependencies=["node_graph"]
        ))
        
        # Real-World Integration Requirements
        real_world_fields = [
            RequireField(
                "real_space_mappings",
                "Real-space mappings from sonar to spectrum frequencies. Bridge physical to celestial.",
                int,
                default_provider=self._provide_real_space_mappings,
                critical=True
            ),
            RequireField(
                "spectrum_points",
                "Spectrum engine mapping points for frequency-to-coordinate correlation.",
                int,
                default_provider=self._provide_spectrum_points,
                critical=True
            ),
            RequireField(
                "active_routes",
                "Active route count for autonomous navigation. Routes must be available for path planning.",
                int,
                default_provider=lambda: 3,  # Auto-provision 3 sample routes
                critical=False
            )
        ]
        
        self.register_system_requirement(SystemRequirement(
            system_name="real_world_integration", 
            require_fields=real_world_fields,
            data_sequence_needs=["sonar_scan_data", "spectrum_frequencies", "route_coordinates"],
            architecture_dependencies=["spatial_nodes", "sonar_bridge"]
        ))
        
        # Virtual Sequences Requirements
        virtual_sequences_fields = [
            RequireField(
                "virtual_sequences_count",
                "Virtual sequences for mesh layer coordination. Provides path alternatives and route optimization.",
                int,
                default_provider=self._provide_virtual_sequences,
                critical=False
            )
        ]
        
        self.register_system_requirement(SystemRequirement(
            system_name="virtual_sequences",
            require_fields=virtual_sequences_fields,
            data_sequence_needs=["path_coordinates", "sequence_metadata"],
            architecture_dependencies=["spatial_nodes"]
        ))
    
    def register_system_requirement(self, requirement: SystemRequirement):
        """Register a system requirement in the chain."""
        self.system_requirements[requirement.system_name] = requirement
        logger.info(f"Registered requirement: {requirement.system_name} ({len(requirement.require_fields)} fields)")
    
    def check_chain_requirements(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check all system requirements in the chain.
        Provides guidance for missing requirements and auto-provisions where possible.
        """
        
        self.last_chain_check = time.time()
        self.chain_state.update(current_state)
        
        chain_results = {
            "timestamp": time.time(),
            "systems_checked": len(self.system_requirements),
            "systems_ready": 0,
            "critical_failures": [],
            "auto_provisions_applied": [],
            "system_results": {},
            "overall_ready": False,
            "next_steps": []
        }
        
        # Check each system
        for system_name, requirement in self.system_requirements.items():
            
            # Extract system-specific state
            system_state = self._extract_system_state(system_name, current_state)
            
            # Check system requirements
            system_result = requirement.check_all_requirements(system_state)
            chain_results["system_results"][system_name] = system_result
            
            if system_result["ready_for_activation"]:
                chain_results["systems_ready"] += 1
            else:
                # Collect critical failures
                chain_results["critical_failures"].extend(system_result["critical_failures"])
                
                # Apply auto-provisions if enabled
                if self.auto_provision_enabled and system_result["auto_provisions_needed"]:
                    provisions_applied = self._apply_auto_provisions(requirement, system_result["auto_provisions_needed"])
                    chain_results["auto_provisions_applied"].extend(provisions_applied)
        
        # Overall readiness check
        chain_results["overall_ready"] = (chain_results["systems_ready"] == chain_results["systems_checked"])
        
        # Generate next steps guidance
        chain_results["next_steps"] = self._generate_next_steps(chain_results)
        
        return chain_results
    
    def _extract_system_state(self, system_name: str, full_state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant state for a specific system."""
        
        # Map global state keys to system-specific keys
        system_mappings = {
            "node_graph": {
                "nodes_count": full_state.get("graph_available", False) and 50 or 0,  # Assume 50 if available
                "node_map_size": 0,  # Will be auto-provisioned
                "router_initialized": full_state.get("graph_available", False)
            },
            "spatial_nodes": {
                "spatial_nodes_count": full_state.get("spatial_nodes_count", 0),
                "coord_to_node_mappings": full_state.get("coord_to_node_mappings", 0)
            },
            "real_world_integration": {
                "real_space_mappings": full_state.get("real_world_integration", {}).get("sonar_bridge_status", {}).get("real_space_mappings", 0),
                "spectrum_points": full_state.get("real_world_integration", {}).get("spectrum_engine_status", {}).get("spectrum_points", 0),
                "active_routes": full_state.get("active_paths_count", 0)
            },
            "virtual_sequences": {
                "virtual_sequences_count": full_state.get("virtual_sequences_count", 0)
            }
        }
        
        return system_mappings.get(system_name, {})
    
    def _apply_auto_provisions(self, requirement: SystemRequirement, needed_fields: List[str]) -> List[Dict[str, Any]]:
        """Apply auto-provisions for needed fields."""
        
        provisions_applied = []
        
        for field_name in needed_fields:
            # Find the require field
            require_field = next((f for f in requirement.require_fields if f.name == field_name), None)
            
            if require_field and require_field.default_provider:
                try:
                    provided_value = require_field.auto_provision()
                    
                    if provided_value is not None:
                        # Store in chain state
                        self.chain_state[field_name] = provided_value
                        
                        provisions_applied.append({
                            "system": requirement.system_name,
                            "field": field_name,
                            "provided_value": provided_value,
                            "value_type": type(provided_value).__name__
                        })
                        
                        logger.info(f"Auto-provisioned {requirement.system_name}.{field_name}: {provided_value}")
                        
                except Exception as e:
                    logger.error(f"Auto-provision failed for {requirement.system_name}.{field_name}: {e}")
        
        return provisions_applied
    
    def _generate_next_steps(self, chain_results: Dict[str, Any]) -> List[str]:
        """Generate helpful next steps for developers."""
        
        next_steps = []
        
        if chain_results["overall_ready"]:
            next_steps.append("✅ All system requirements satisfied - ready for full mode activation")
            return next_steps
        
        # Analyze failures and provide specific guidance
        for failure in chain_results["critical_failures"]:
            system_name = None
            # Find which system this failure belongs to
            for sys_name, sys_result in chain_results["system_results"].items():
                if failure in sys_result.get("critical_failures", []):
                    system_name = sys_name
                    break
            
            if system_name:
                requirement = self.system_requirements.get(system_name)
                if requirement:
                    next_steps.append(f"🔧 {system_name}: {failure['guidance']}")
                    
                    # Add data sequence guidance
                    if requirement.data_sequence_needs:
                        next_steps.append(f"   📊 Needs data sequences: {', '.join(requirement.data_sequence_needs)}")
        
        # Add auto-provision summary
        if chain_results["auto_provisions_applied"]:
            next_steps.append(f"🤖 Auto-provisioned {len(chain_results['auto_provisions_applied'])} missing requirements")
        
        return next_steps
    
    # Default providers for common requirements
    
    def _provide_default_spatial_nodes(self) -> int:
        """Provide default spatial nodes count."""
        return 25  # Minimum for basic autonomous navigation
    
    def _provide_real_space_mappings(self) -> int:
        """Provide default real space mappings.""" 
        return 10  # Minimum mappings for basic operation
    
    def _provide_spectrum_points(self) -> int:
        """Provide default spectrum points."""
        return 50  # Basic spectrum-to-space mapping
    
    def _provide_virtual_sequences(self) -> int:
        """Provide default virtual sequences."""
        return 5  # Basic route alternatives
    
    def get_requirement_status(self) -> Dict[str, Any]:
        """Get current requirement chain status."""
        
        return {
            "systems_registered": len(self.system_requirements),
            "auto_provision_enabled": self.auto_provision_enabled,
            "last_chain_check": self.last_chain_check,
            "chain_state_size": len(self.chain_state),
            "systems": {
                name: {
                    "require_fields_count": len(req.require_fields),
                    "data_sequence_needs": req.data_sequence_needs,
                    "architecture_dependencies": req.architecture_dependencies
                }
                for name, req in self.system_requirements.items()
            }
        }
    
    def force_provision_all(self) -> Dict[str, Any]:
        """Force provision all missing requirements (for testing/debugging)."""
        
        logger.info("🚀 Force provisioning all missing requirements")
        
        provision_results = {
            "timestamp": time.time(),
            "provisions_attempted": 0,
            "provisions_successful": 0,
            "provisions_failed": [],
            "provisioned_values": {}
        }
        
        for system_name, requirement in self.system_requirements.items():
            for require_field in requirement.require_fields:
                if require_field.default_provider:
                    
                    provision_results["provisions_attempted"] += 1
                    
                    try:
                        provided_value = require_field.auto_provision()
                        
                        if provided_value is not None:
                            self.chain_state[require_field.name] = provided_value
                            provision_results["provisioned_values"][require_field.name] = provided_value
                            provision_results["provisions_successful"] += 1
                            
                    except Exception as e:
                        provision_results["provisions_failed"].append({
                            "system": system_name,
                            "field": require_field.name,
                            "error": str(e)
                        })
        
        logger.info(f"Force provision complete: {provision_results['provisions_successful']}/{provision_results['provisions_attempted']} successful")
        
        return provision_results