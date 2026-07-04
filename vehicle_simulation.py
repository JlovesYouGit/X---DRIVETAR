"""
Vehicle Simulation Layer for Desktop Testing
Simulates Tesla-like vehicle modules and position markers for autonomous driving testing.
"""

import time
import math
import random
import threading
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from lidar_sonar_engine import Coordinate

class VehicleState(Enum):
    PARKED = "parked"
    DRIVING = "driving"
    EMERGENCY_STOP = "emergency_stop"
    AUTOPILOT = "autopilot"
    MANUAL = "manual"

class SensorStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"

@dataclass
class VehiclePosition:
    """Tesla-like vehicle position with GPS and IMU data."""
    latitude: float
    longitude: float
    altitude: float
    coordinate: Coordinate  # Local coordinate system
    heading: float  # degrees
    speed: float    # m/s
    acceleration: float  # m/s²
    timestamp: float = field(default_factory=time.time)

@dataclass
class VehicleSensorData:
    """Vehicle sensor readings (simulated Tesla sensors)."""
    # Camera data
    front_camera_obstacles: List[Tuple[float, float, float]]  # (x, y, confidence)
    side_cameras_clear: bool
    rear_camera_clear: bool
    
    # Radar data
    front_radar_distance: float  # meters to nearest obstacle
    side_radar_clear: bool
    
    # Ultrasonic sensors
    parking_sensors: Dict[str, float]  # {position: distance}
    
    # Vehicle dynamics
    wheel_speeds: List[float]  # [FL, FR, RL, RR] in km/h
    steering_angle: float     # degrees
    brake_pressure: float    # 0.0-1.0
    throttle_position: float # 0.0-1.0
    
    timestamp: float = field(default_factory=time.time)

@dataclass  
class NavigationCommand:
    """Navigation command from autopilot system."""
    target_speed: float      # m/s
    target_steering: float   # degrees
    brake_command: float     # 0.0-1.0
    throttle_command: float  # 0.0-1.0
    emergency_stop: bool
    confidence: float        # 0.0-1.0
    timestamp: float = field(default_factory=time.time)

class VehicleSimulator:
    """
    Simulates Tesla-like vehicle systems for autonomous driving testing.
    Provides position markers, sensor data, and vehicle control signals.
    """
    
    def __init__(self, initial_position: Optional[Coordinate] = None):
        # Vehicle state
        self.vehicle_state = VehicleState.PARKED
        self.sensor_status = {
            "lidar": SensorStatus.ACTIVE,
            "cameras": SensorStatus.ACTIVE, 
            "radar": SensorStatus.ACTIVE,
            "gps": SensorStatus.ACTIVE,
            "imu": SensorStatus.ACTIVE
        }
        
        # Position tracking
        if initial_position:
            self.current_position = VehiclePosition(
                latitude=37.4419,  # Tesla HQ coordinates as reference
                longitude=-122.1430,
                altitude=10.0,
                coordinate=initial_position,
                heading=0.0,
                speed=0.0,
                acceleration=0.0
            )
        else:
            self.current_position = VehiclePosition(
                latitude=37.4419,
                longitude=-122.1430, 
                altitude=10.0,
                coordinate=Coordinate(-0.5, 0.5, 0.0, 0.0),
                heading=0.0,
                speed=0.0,
                acceleration=0.0
            )
        
        # Sensor simulation
        self.sensor_data = VehicleSensorData(
            front_camera_obstacles=[],
            side_cameras_clear=True,
            rear_camera_clear=True,
            front_radar_distance=50.0,
            side_radar_clear=True,
            parking_sensors={
                "front_left": 5.0, "front_right": 5.0,
                "rear_left": 5.0, "rear_right": 5.0
            },
            wheel_speeds=[0.0, 0.0, 0.0, 0.0],
            steering_angle=0.0,
            brake_pressure=0.0,
            throttle_position=0.0
        )
        
        # Navigation system
        self.current_command = NavigationCommand(
            target_speed=0.0,
            target_steering=0.0,
            brake_command=0.0,
            throttle_command=0.0,
            emergency_stop=False,
            confidence=1.0
        )
        
        # Simulation parameters
        self.simulation_running = False
        self.simulation_thread = None
        self.update_rate = 20  # Hz (50ms updates like Tesla)
        
        # Route following
        self.planned_route: List[Coordinate] = []
        self.current_waypoint_index = 0
        self.waypoint_tolerance = 2.0  # meters
        
    def start_simulation(self):
        """Start vehicle simulation (like powering on Tesla systems)."""
        if self.simulation_running:
            return
            
        self.simulation_running = True
        self.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.simulation_thread.start()
        print("🚗 Vehicle simulation started (Tesla-like systems online)")
        
    def stop_simulation(self):
        """Stop vehicle simulation."""
        self.simulation_running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=1.0)
        print("🛑 Vehicle simulation stopped")
        
    def set_autopilot_mode(self, enabled: bool):
        """Enable/disable autopilot mode."""
        if enabled:
            self.vehicle_state = VehicleState.AUTOPILOT
            print("🤖 Autopilot enabled")
        else:
            self.vehicle_state = VehicleState.MANUAL  
            print("👤 Manual driving mode")
            
    def load_route(self, waypoints: List[Coordinate]):
        """Load navigation route (like Tesla navigation system)."""
        self.planned_route = waypoints
        self.current_waypoint_index = 0
        print(f"📍 Route loaded: {len(waypoints)} waypoints")
        
    def get_position_marker(self) -> Dict[str, Any]:
        """
        Get current position marker (like Tesla's position reporting).
        Returns GPS + local coordinates for autonomous driving.
        """
        return {
            "gps": {
                "latitude": self.current_position.latitude,
                "longitude": self.current_position.longitude,
                "altitude": self.current_position.altitude,
                "accuracy": 0.5  # meters
            },
            "local_coordinate": self.current_position.coordinate,
            "heading": self.current_position.heading,
            "speed": self.current_position.speed,
            "acceleration": self.current_position.acceleration,
            "timestamp": self.current_position.timestamp,
            "coordinate_system": "local_lidar_frame"
        }
        
    def get_sensor_readings(self) -> Dict[str, Any]:
        """
        Get current sensor readings (simulates Tesla's sensor fusion).
        Returns data from cameras, radar, ultrasonic sensors.
        """
        return {
            "vision": {
                "front_camera_obstacles": self.sensor_data.front_camera_obstacles,
                "side_cameras_clear": self.sensor_data.side_cameras_clear,
                "rear_camera_clear": self.sensor_data.rear_camera_clear,
                "confidence": 0.95
            },
            "radar": {
                "front_distance": self.sensor_data.front_radar_distance,
                "side_clear": self.sensor_data.side_radar_clear,
                "detection_range": 200.0  # meters
            },
            "ultrasonic": {
                "parking_sensors": self.sensor_data.parking_sensors,
                "range": 8.0  # meters
            },
            "vehicle_dynamics": {
                "wheel_speeds": self.sensor_data.wheel_speeds,
                "steering_angle": self.sensor_data.steering_angle,
                "brake_pressure": self.sensor_data.brake_pressure,
                "throttle_position": self.sensor_data.throttle_position
            },
            "sensor_health": self.sensor_status,
            "timestamp": self.sensor_data.timestamp
        }
        
    def send_navigation_command(self, command: NavigationCommand):
        """Send navigation command to vehicle (like Tesla autopilot commands)."""
        self.current_command = command
        
        # Apply safety limits (like Tesla's safety systems)
        if command.emergency_stop:
            self.vehicle_state = VehicleState.EMERGENCY_STOP
            self.current_command.target_speed = 0.0
            self.current_command.brake_command = 1.0
            
        # Validate command ranges
        self.current_command.target_speed = max(0.0, min(30.0, command.target_speed))  # 30 m/s max
        self.current_command.target_steering = max(-45.0, min(45.0, command.target_steering))  # ±45° max
        
    def simulate_obstacle_detection(self, obstacle_coord: Coordinate) -> bool:
        """
        Simulate Tesla-like obstacle detection.
        Returns True if obstacle is detected by vehicle sensors.
        """
        vehicle_pos = self.current_position.coordinate
        
        # Calculate distance to obstacle
        distance = math.sqrt(
            (obstacle_coord.x_center - vehicle_pos.x_center)**2 +
            (obstacle_coord.y - vehicle_pos.y)**2
        )
        
        # Check if within sensor range
        if distance <= 50.0:  # Tesla's typical detection range
            # Add to camera obstacles with simulated confidence
            confidence = max(0.5, 1.0 - (distance / 50.0))
            
            # Relative position from vehicle
            rel_x = obstacle_coord.x_center - vehicle_pos.x_center  
            rel_y = obstacle_coord.y - vehicle_pos.y
            
            self.sensor_data.front_camera_obstacles.append((rel_x, rel_y, confidence))
            
            # Update radar distance if closer
            if distance < self.sensor_data.front_radar_distance:
                self.sensor_data.front_radar_distance = distance
                
            return True
            
        return False
        
    def get_vehicle_status(self) -> Dict[str, Any]:
        """Get comprehensive vehicle status (like Tesla's diagnostics)."""
        return {
            "state": self.vehicle_state.value,
            "position": self.get_position_marker(),
            "sensors": self.get_sensor_readings(),
            "navigation": {
                "current_command": {
                    "target_speed": self.current_command.target_speed,
                    "target_steering": self.current_command.target_steering,
                    "emergency_stop": self.current_command.emergency_stop,
                    "confidence": self.current_command.confidence
                },
                "route_progress": {
                    "total_waypoints": len(self.planned_route),
                    "current_waypoint": self.current_waypoint_index,
                    "distance_to_next": self._distance_to_next_waypoint()
                }
            },
            "simulation_active": self.simulation_running,
            "timestamp": time.time()
        }
        
    def _simulation_loop(self):
        """Main simulation loop (runs at Tesla-like update rates)."""
        dt = 1.0 / self.update_rate  # Time step
        
        while self.simulation_running:
            start_time = time.time()
            
            # Update vehicle physics
            self._update_vehicle_physics(dt)
            
            # Update sensors
            self._update_sensor_simulation()
            
            # Process autopilot if active
            if self.vehicle_state == VehicleState.AUTOPILOT:
                self._update_autopilot_navigation()
                
            # Update position
            self._update_position(dt)
            
            # Sleep to maintain update rate
            elapsed = time.time() - start_time
            sleep_time = max(0, dt - elapsed)
            time.sleep(sleep_time)
            
    def _update_vehicle_physics(self, dt: float):
        """Update vehicle physics simulation."""
        if self.vehicle_state == VehicleState.EMERGENCY_STOP:
            # Emergency braking
            deceleration = -8.0  # m/s² (Tesla emergency braking)
            self.current_position.speed = max(0.0, self.current_position.speed + deceleration * dt)
            self.current_position.acceleration = deceleration
            
        elif self.vehicle_state == VehicleState.AUTOPILOT:
            # Follow navigation commands
            target_speed = self.current_command.target_speed
            speed_diff = target_speed - self.current_position.speed
            
            # Simulate Tesla-like acceleration profile
            if speed_diff > 0:
                acceleration = min(3.0, speed_diff * 2.0)  # Gradual acceleration
            else:
                acceleration = max(-5.0, speed_diff * 2.0)  # Gentle braking
                
            self.current_position.speed += acceleration * dt
            self.current_position.speed = max(0.0, self.current_position.speed)
            self.current_position.acceleration = acceleration
            
            # Update heading based on steering command
            if self.current_position.speed > 0.1:  # Only turn when moving
                steering_rate = self.current_command.target_steering * 0.1  # degrees per second
                self.current_position.heading += steering_rate * dt
                self.current_position.heading = self.current_position.heading % 360.0
                
    def _update_sensor_simulation(self):
        """Update sensor data simulation."""
        # Simulate sensor noise and updates
        self.sensor_data.timestamp = time.time()
        
        # Update wheel speeds based on vehicle speed
        speed_kmh = self.current_position.speed * 3.6  # Convert m/s to km/h
        noise = random.uniform(-0.5, 0.5)  # Small noise like real sensors
        for i in range(4):
            self.sensor_data.wheel_speeds[i] = speed_kmh + noise
            
        # Update steering angle
        self.sensor_data.steering_angle = self.current_command.target_steering
        
        # Simulate parking sensor readings (random distances for now)
        for sensor in self.sensor_data.parking_sensors:
            base_distance = 5.0
            self.sensor_data.parking_sensors[sensor] = base_distance + random.uniform(-1.0, 1.0)
            
    def _update_autopilot_navigation(self):
        """Update autopilot navigation logic."""
        if not self.planned_route or self.current_waypoint_index >= len(self.planned_route):
            return
            
        # Get next waypoint
        target_waypoint = self.planned_route[self.current_waypoint_index]
        
        # Calculate distance and bearing to waypoint
        distance = self._distance_to_coordinate(target_waypoint)
        bearing = self._bearing_to_coordinate(target_waypoint)
        
        # Check if we've reached the waypoint
        if distance < self.waypoint_tolerance:
            self.current_waypoint_index += 1
            print(f"📍 Reached waypoint {self.current_waypoint_index}/{len(self.planned_route)}")
            
            if self.current_waypoint_index >= len(self.planned_route):
                print("🏁 Route completed")
                self.vehicle_state = VehicleState.PARKED
                return
                
        # Generate navigation command
        target_speed = min(15.0, distance * 2.0)  # Slow down as we approach
        steering_adjustment = self._calculate_steering_for_bearing(bearing)
        
        command = NavigationCommand(
            target_speed=target_speed,
            target_steering=steering_adjustment,
            brake_command=0.0,
            throttle_command=0.5 if target_speed > 0 else 0.0,
            emergency_stop=False,
            confidence=0.9
        )
        
        self.send_navigation_command(command)
        
    def _update_position(self, dt: float):
        """Update vehicle position based on current motion."""
        if self.current_position.speed > 0.1:
            # Calculate movement in local coordinates
            heading_rad = math.radians(self.current_position.heading)
            
            dx = self.current_position.speed * math.cos(heading_rad) * dt
            dy = self.current_position.speed * math.sin(heading_rad) * dt
            
            # Update coordinate
            new_x_center = self.current_position.coordinate.x_center + dx
            new_y = self.current_position.coordinate.y + dy
            
            self.current_position.coordinate = Coordinate(
                new_x_center - 0.5, new_x_center + 0.5, new_y, 0.0
            )
            
            # Simulate GPS update (simplified)
            self.current_position.latitude += dy * 0.000009  # Rough conversion
            self.current_position.longitude += dx * 0.000009
            
        self.current_position.timestamp = time.time()
        
    def _distance_to_coordinate(self, coord: Coordinate) -> float:
        """Calculate distance to a coordinate."""
        return math.sqrt(
            (coord.x_center - self.current_position.coordinate.x_center)**2 +
            (coord.y - self.current_position.coordinate.y)**2
        )
        
    def _distance_to_next_waypoint(self) -> float:
        """Get distance to next waypoint."""
        if not self.planned_route or self.current_waypoint_index >= len(self.planned_route):
            return 0.0
        return self._distance_to_coordinate(self.planned_route[self.current_waypoint_index])
        
    def _bearing_to_coordinate(self, coord: Coordinate) -> float:
        """Calculate bearing to a coordinate in degrees."""
        dx = coord.x_center - self.current_position.coordinate.x_center
        dy = coord.y - self.current_position.coordinate.y
        
        bearing = math.degrees(math.atan2(dy, dx))
        return (bearing - self.current_position.heading + 180) % 360 - 180  # Relative bearing
        
    def _calculate_steering_for_bearing(self, bearing: float) -> float:
        """Calculate steering angle needed for target bearing."""
        # Simple proportional control (like Tesla's path following)
        steering = bearing * 0.5  # Proportional gain
        return max(-30.0, min(30.0, steering))  # Limit to realistic steering angles


# Global vehicle simulator instance for testing
_vehicle_sim = None

def get_vehicle_simulator() -> VehicleSimulator:
    """Get global vehicle simulator instance."""
    global _vehicle_sim
    if _vehicle_sim is None:
        _vehicle_sim = VehicleSimulator()
    return _vehicle_sim

def create_test_vehicle(initial_pos: Optional[Coordinate] = None) -> VehicleSimulator:
    """Create a new vehicle simulator for testing."""
    return VehicleSimulator(initial_pos)