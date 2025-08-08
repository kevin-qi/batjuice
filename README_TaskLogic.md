# Modular Task Logic System

## Architecture

### 1. System State (`task_logic/system_state.py`)

The core data structure that maintains the complete state of the recording system:

- **SystemBat**: Enhanced bat tracking with complete history
  - `bat_id`: Unique bat identifier
  - `tag_id`: Hardware identifier (SN for Ciholas, markerset name for Cortex)
  - `active`: Whether the bat is actively tracked
  - `last_position`: Most recent position (x, y, z, timestamp)
  - `beam_break_history`: Complete history of beam break events
  - `reward_history`: Complete history of reward deliveries

- **SystemFeeder**: Enhanced feeder tracking with complete history
  - `feeder_id`: Unique feeder identifier
  - `name`: Human-readable feeder name
  - `active`: Whether the feeder is active
  - `position`: Physical position (x, y, z)
  - `activation_distance`: Detection range in cm
  - `duration_ms`: Motor activation duration
  - `motor_speed`: Motor speed (0-255)
  - `beam_break_history`: History of which bats triggered beam breaks
  - `reward_delivery_history`: History of reward deliveries

- **SystemState**: Complete system state
  - `bats`: Dictionary of all bats in the system
  - `feeders`: Dictionary of all feeders in the system
  - `session_start_time`: When the current session started
  - `session_id`: Unique session identifier

### 2. Task Logic Endpoint (`task_logic/task_logic_endpoint.py`)

The modular decision engine that determines whether to deliver rewards:

#### Main Function
```python
def should_deliver_reward(system_state: SystemState, feeder_id: int, 
                         triggering_bat_id: str) -> tuple:
    """
    Returns: (should_deliver: bool, reason: str)
    """
```

#### Configurable Parameters
- `min_time_between_rewards`: Minimum time between rewards (seconds)
- `max_distance_for_reward`: Maximum distance for collision detection (meters)
- `min_distance_from_last_feeder`: Minimum distance from last feeder (meters)
- `reward_probability`: Probability of reward delivery (0.0-1.0)
- `position_timeout`: Max age of position data (seconds)
- `enable_collision_detection`: Enable/disable collision detection
- `enable_distance_constraints`: Enable/disable distance constraints
- `enable_time_constraints`: Enable/disable time constraints

### 3. Feeder Controller (`controller/feeder_controller.py`)

The controller that:
- Maintains system state in real-time
- Delegates reward decisions to the task logic endpoint
- Handles hardware communication

### 4. Configuration Management (`task_logic/config_interface.py`)

Utilities for loading and saving task logic configurations:
- Automatic loading of configuration on startup
- JSON-based configuration files
- Runtime parameter updates

## Usage

### Basic Setup

The new system is automatically initialized when the main application starts. The task logic configuration is loaded from `config/task_logic_config.json`.

### Customizing Task Logic

#### Option 1: Modify Configuration File

Edit `config/task_logic_config.json`:

```json
{
  "min_time_between_rewards": 1.0,
  "max_distance_for_reward": 0.2,
  "min_distance_from_last_feeder": 0.8,
  "reward_probability": 0.75,
  "position_timeout": 0.3,
  "enable_collision_detection": true,
  "enable_distance_constraints": true,
  "enable_time_constraints": false
}
```

#### Option 2: Runtime Parameter Updates

```python
from task_logic.task_logic_endpoint import update_task_parameters

# Update specific parameters
update_task_parameters(
    min_time_between_rewards=2.0,
    reward_probability=0.5
)
```

#### Option 3: Custom Task Logic

For complex experimental paradigms, modify the `should_deliver_reward` method in `task_logic/task_logic_endpoint.py`:

```python
def should_deliver_reward(self, system_state: SystemState, feeder_id: int, 
                        triggering_bat_id: str) -> tuple:
    """Custom task logic implementation"""
    
    # Your custom logic here
    # Access complete system state:
    # - system_state.bats[bat_id] for bat information
    # - system_state.feeders[feeder_id] for feeder information
    # - Complete event histories available
    
    if your_custom_condition:
        return True, "Custom condition met"
    else:
        return False, "Custom condition not met"
```
## Event History Structure

### Beam Break Events
```python
BeamBreakEvent:
    timestamp: float
    bat_id: str
    feeder_id: int
    event_name: "beam_break"
    distance_to_feeder: float
    bat_position: (x, y, z) or None
```

### Reward Delivery Events
```python
RewardDeliveryEvent:
    timestamp: float
    bat_id: str
    feeder_id: int
    event_name: "reward_delivery"
    manual: bool
    duration_ms: int
    motor_speed: int
```

## Examples

### Example 1: Simple Time-Based Rewards
```python
# Only time constraint, deliver reward if 1 second has passed
update_task_parameters(
    min_time_between_rewards=1.0,
    enable_collision_detection=False,
    enable_distance_constraints=False,
    reward_probability=1.0
)
```

### Example 2: Probability-Based Training
```python
# 50% chance of reward with collision detection
update_task_parameters(
    reward_probability=0.5,
    enable_collision_detection=True,
    max_distance_for_reward=0.2
)
```

### Example 3: Spatial Constraints
```python
# Must move at least 1 meter from last feeder
update_task_parameters(
    min_distance_from_last_feeder=1.0,
    enable_distance_constraints=True
)
```
