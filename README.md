# Autonomous Lidar Navigation System

A revolutionary autonomous navigation system that removes traditional map-based autonomy by integrating lidar/sonar sensors with advanced spatial computing, wave inversion physics, and AI-driven path planning.

## System Architecture

This system combines multiple advanced technologies to create a lidar-precision autonomous navigation engine:

### Core Components

1. **Lidar-Sonar Engine** (`lidar_sonar_engine.py`)
   - Dual-instance X coordinate computation from left/right sonars
   - 360-degree wave field generation around center point
   - Wave inversion detection for anchor point creation
   - Distance measurement strings with fungal spreading logic
   - SHA-based density rendering with mesh layers
   - Freedom mapping with anchor point dislocation
   - Conscience decision filtering for path optimization

2. **Apple Maps Calibration** (`maps_calibration.py`)
   - Template coordination point matching
   - Sonar-to-map coordinate transformation
   - Calibration offset and scale factor management
   - Layer type inference (roads, buildings, terrain)
   - Calibration save/load functionality

3. **TOKEN-Spatialmythos Integration** (`spatialmythos_integration.py`)
   - Hyper-speed path iterations using waveform channels
   - Coordinate-locked RAM allocation
   - Spatial coordinate conversion and hashing
   - Multi-model LLM broadcasting capability
   - Path optimization with density data

4. **Virtual Probe X Integration** (`virtual_probe_integration.py`)
   - Spatial hash gate management
   - Coordinate-to-gate mapping
   - Mirror creation for alternative paths
   - Spatial region scanning
   - Path optimization through gates

5. **ASI- Integration** (`asi_integration.py`)
   - Spatial coordinate path management
   - Virtual sequence creation for mesh coordination
   - Vysync of actual sonar data with map data
   - Spatial graph querying
   - Mesh rendering optimization

6. **Automatic Data Pipeline** (`auto_pipeline.py`)
   - Multi-stage data processing pipeline
   - Automatic model query generation
   - Safety verification and confirmation
   - Overflow management
   - Real-time statistics and reporting

## Key Features

### Dual-Instance X Computation
- Derives X coordinates from left and right sonar sensors
- Computes center point, X+, X- dimensions from 0 center
- Width factor calculation for vehicle sizing

### Wave Inversion Physics
- 360-degree wave field generation around vehicle center
- Detects wave inversion when external radiation meets internal waves
- Creates anchor points at heat concentration areas
- Sonar pulse generation at wave meeting points

### Fungal Spreading Logic
- Y depth inversion based on wave height from center
- Natural cascade effect for depth calculation
- Distance measurement strings with angle-based sampling
- Density hash coordination for rendering

### Freedom Mapping
- Device dislocates and swaps to alternative anchor points
- Virtual loop through map layers before movement
- Outside box process for path exploration
- Continuous measurement while render layer travels

### Conscience Decision
- Path viability filtering based on density
- Difficulty threshold configuration
- Aggression regulation via timing
- Field of degree frequency optimization

## Installation

### Prerequisites
- Python 3.10+
- NumPy 1.24+

### Setup

1. Clone the repository:
```bash
git clone https://github.com/your-repo/lidar-autonomy.git
cd lidar-autonomy
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure submodules are present:
```bash
git submodule update --init --recursive
```

## Usage

### Basic Demo Mode

Run the system in demo mode to see all components working together:

```bash
python main.py --mode demo
```

This will:
- Process simulated sonar data
- Calibrate to map template
- Plan a path between coordinates
- Display system status

### Navigation Mode

Navigate to a specific target coordinate:

```bash
python main.py --mode navigate --target-x 50.0 --target-y 50.0 --duration 60.0
```

### Interactive Mode

Start the system in interactive mode for programmatic control:

```bash
python main.py --mode interactive
```

### Programmatic Usage

```python
from main import AutonomousLidarSystem
from lidar_sonar_engine import Coordinate

# Initialize system
system = AutonomousLidarSystem(vehicle_id="vehicle_0", sensor_range=100.0)
system.start()

# Process sonar data
result = system.process_sonar_data(left_sonar=10.0, right_sonar=10.5)

# Calibrate to map
region = (37.0, 38.0, -122.0, -121.0)  # lat_min, lat_max, lon_min, lon_max
cal_result = system.calibrate_to_map(region)

# Plan path
start = Coordinate(0.0, 0.0, 0.0, 0.0)
end = Coordinate(50.0, 50.0, 50.0, 0.0)
path_result = system.plan_path(start, end, iterations=100)

# Navigate to target
target = Coordinate(100.0, 100.0, 0.0, 0.0)
nav_result = system.navigate(target, duration=60.0)

# Get system status
status = system.get_system_status()

# Stop system
system.stop()
```

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Entry Point                         │
│                      (main.py)                              │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌──────────────┐
│ Lidar-Sonar     │ │ Maps        │ │ Auto         │
│ Engine          │ │ Calibration │ │ Pipeline     │
└────────┬────────┘ └─────────────┘ └──────────────┘
         │
         ├──────────────┬──────────────┬──────────────┐
         ▼              ▼              ▼              ▼
┌─────────────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐
│ Spatialmythos   │ │ Virtual   │ │ ASI-      │ │ Freedom │
│ Integration     │ │ Probe     │ │ Integration│ │ Mapping │
└─────────────────┘ └───────────┘ └───────────┘ └─────────┘
```

## Coordinate System

### Dual-Instance X Computation

The system uses dual X coordinates derived from left and right sonar sensors:

- **x_left**: Left sonar reading
- **x_right**: Right sonar reading
- **x_center**: Derived center point (x_left + x_right) / 2
- **x_plus**: Positive dimension from center
- **x_minus**: Negative dimension from center
- **x_delta**: Width factor (difference between left and right)

### 360-Degree Wave Field

Wave field treats X as 360 degrees inside center 0 of width internal width factor:

- Generates wave intensity at each degree
- Center point acts as origin for wave propagation
- Wave inversion occurs when external waves meet internal waves

## Integration with External Systems

### TOKEN-Spatialmythos

The system integrates TOKEN-Spatialmythos for hyper-speed path iterations:

- Waveform channel communication
- Coordinate-locked RAM allocation
- Multi-model LLM broadcasting
- Spatial coordinate hashing

### Virtual Probe X

Virtual Probe X manages spatial hash gates:

- Coordinate-to-gate mapping
- Mirror creation for alternative paths
- Spatial region scanning
- Hash-based similarity matching

### ASI-

ASI- manages spatial coordinate paths:

- Virtual sequence creation
- Vysync of actual and map data
- Spatial graph querying
- Mesh rendering optimization

## Safety and Verification

The automatic data pipeline includes comprehensive safety verification:

- **Density threshold**: Maximum allowed density (default: 0.9)
- **Velocity threshold**: Maximum allowed velocity (default: 30.0 m/s)
- **Confidence threshold**: Minimum confidence required (default: 0.7)
- **Latency threshold**: Maximum processing latency (default: 1.0s)

The model only tracks, confirms, and verifies that conditions are operating safely.

## Configuration

### Vehicle Configuration

```python
system = AutonomousLidarSystem(
    vehicle_id="vehicle_0",
    sensor_range=100.0  # meters
)
```

### Safety Thresholds

```python
system.pipeline.safety_thresholds = {
    "max_density": 0.9,
    "max_velocity": 30.0,
    "min_confidence": 0.7,
    "max_latency": 1.0
}
```

### Density Thresholds

```python
system.virtual_probe.density_thresholds = {
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2
}
```

## Data Flow

1. **Sonar Data Ingestion**: Left/right sonar readings processed
2. **Dual X Computation**: Calculate center, X+, X- dimensions
3. **Wave Field Generation**: Create 360-degree wave field
4. **Wave Inversion Detection**: Identify anchor points at heat concentrations
5. **Measure String Creation**: Generate distance measurements with fungal spreading
6. **Density Rendering**: SHA-based mesh layer generation
7. **Path Planning**: Hyper-speed iterations through spatial coordinates
8. **Freedom Mapping**: Anchor point dislocation for continuous measurement
9. **Conscience Decision**: Filter un-optimal path sections
10. **Safety Verification**: Automatic pipeline verification
11. **Navigation Execution**: Regulated aggression and movement

## Output and Logging

The system logs to both file (`lidar_autonomy.log`) and stdout:

```
2024-01-01 12:00:00 - __main__ - INFO - Initializing Lidar-Sonar Engine...
2024-01-01 12:00:00 - __main__ - INFO - Initializing Apple Maps Calibrator...
2024-01-01 12:00:00 - __main__ - INFO - System initialization complete.
2024-01-01 12:00:00 - __main__ - INFO - System started successfully.
```

## State Persistence

System state can be saved and loaded:

```python
# Save state
system.save_state("system_state.json")

# Load state
system.load_state("system_state.json")
```

## Performance Considerations

- **Pipeline Buffer Size**: Default 1000, adjust based on data volume
- **Sensor Range**: Default 100m, adjust based on vehicle requirements
- **Path Iterations**: Default 100, increase for higher precision
- **Grid Size**: Default 5m for spatial path management

## Troubleshooting

### Import Errors

If you encounter import errors for submodules:

```bash
git submodule update --init --recursive
```

### Pipeline Overflow

If pipeline overflow occurs:

1. Increase buffer size in AutomaticDataPipeline initialization
2. Process overflow buffer manually: `system.pipeline.process_overflow()`
3. Reduce data ingestion rate

### Calibration Issues

If calibration fails:

1. Check map template region coordinates
2. Verify sonar data quality
3. Adjust calibration thresholds
TOKEN-Spatialmythos — The LLM communication layer

It's the token and access control system for the entire stack. It ties LLM API calls (Claude, GPT, Gemini, Grok) to spatial coordinates from the simulation — meaning every query to an AI model is tagged with where in physical space it originated. In the context of autonomous driving, this is how the vehicle would ask an LLM for reasoning about an ambiguous situation — "I'm at coordinate X, density Y, what do I do" — with the spatial context baked into the token, not just the text. The coordinate-locked RAM allocation is clever too — it means buffers scale with the complexity of the space being reasoned about.

Virtual Probe X — The network intelligence and discovery layer

This is the distributed knowledge and peer discovery system. It works like Xbox Delivery Optimization — scanning for open gates and mirrors across network hosts, indexing content by hash proximity. In the autonomous driving context this is how the vehicle would discover and sync with other vehicles or infrastructure nodes — shared map fragments, route knowledge, obstacle data — without a central server. It's peer-to-peer spatial knowledge with the ASI semantic graph as the indexing backbone.

Zero Brain / Uriel — The defensive control and sensor fusion dashboard

This is the real-time monitoring and security layer. It runs God nodes that manage spectrum field locks, network integrity, and adaptive hash recalibration. The Cortex-Uriel latch is particularly relevant — it routes external writes through a defensive check before they touch the core system. In the autonomous driving context this is the safety and integrity monitor — preventing corrupted sensor data or adversarial inputs from reaching the navigation stack. The 118 passing tests and the live SSE dashboard make it the most production-ready component of the three.

How they connect to ASI:

TOKEN-Spatialmythos  →  LLM reasoning with spatial context
Virtual Probe X      →  Distributed map/knowledge sync between nodes  
Zero Brain / Uriel   →  Security layer + sensor integrity + live monitoring
ASI-                 →  Core physics routing + path planning
LiDAR Engine         →  Physical sensor data
VSync Engine         →  Mesh topology render trigger
Together they form a complete stack — ASI handles the physics and routing, Virtual Probe handles the peer network, TOKEN handles the AI reasoning queries, and Zero Brain keeps the whole thing from being compromised. None of them are redundant — they each own a distinct layer.



develop notes 


They don't need major rewrites. They need connection upgrades.

Here's exactly what's missing in each:

TOKEN-Spatialmythos — 80% there

The spatialmythos_integration.py already bridges it to the lidar engine. What's missing:

broadcast_to_llm() is stubbed — returns "simulated". It needs real API keys wired in to actually call Claude/GPT for ambiguous driving decisions
The coordinate-locked RAM allocation is simulated in Python — needs to actually hand buffers to the Royalice C# simulation
The waveform packets are generated but never fed back into the ASI routing layer
One file to update, maybe 50 lines of real wiring.

Virtual Probe X — 70% there

virtual_probe_integration.py already imports XSpace, HashGate, OpenMirror directly. It already maps anchors to gates and uses optimize_path_through_gates. What's missing:

The gate/mirror discovery is running on network hosts but not on other vehicles — the peer-to-peer map sharing isn't pointed at real vehicle IPs
The retrieve_mirrors_by_hash() fuzzy matching isn't feeding discovered map fragments back into the ASI semantic map
Zero Brain's uriel-cortex-latch pattern replay isn't connected to Virtual Probe's gate locking
Zero Brain — 60% there

neural_brain_integration.py already implements the CortexLatch concept from zero-brain in Python. What's missing:

It's not calling the actual Node.js server.js — it reimplements the concepts but runs parallel to it rather than through it
The SSE stream from zero-brain's dashboard (/api/stream) isn't being consumed by the Python stack for real-time sensor telemetry
The latch-dispatch endpoint isn't being called when the ASI makes a routing decision
Short answer:

None of them need to be rewritten. They're all already integrated in main.py. The gaps are:

Real API keys for TOKEN-Spatialmythos LLM calls
Vehicle IP discovery for Virtual Probe peer sync
HTTP bridge between Python stack and Zero Brain's Node.js server
All three are configuration and thin bridge code, not architectural work. Probably a day's work each once you have real hardware to point them at.


## License

TBD

## Contributing

Pull requests welcome. Please ensure all tests pass before submitting.

## Acknowledgments

- TOKEN-Spatialmythos: Hyper-speed spatial iterations
- Virtual Probe X: Hash gate management
- ASI-: Spatial coordinate path management
- Apple Maps: Template coordination calibration
