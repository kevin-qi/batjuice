# Scientist Guide to BatFeeder Task Logic

This guide explains how scientists can create custom reward logic and configure experiments without touching the core system code.

## Quick Start

### Running with Your Configuration

Each scientist should have their own configuration file:

```bash
# Copy a template
cp config/templates/proximity_study.json config/my_experiment.json

# Edit the configuration
# (modify experiment details, task logic, and parameters)

# Run with your config
python main.py --config config/my_experiment.json

# Validate configuration before running
python main.py --config config/my_experiment.json --validate
```

### Creating Custom Task Logic

1. **Copy an example**: Start with `task_logic/logics/examples/proximity_reward.py`
2. **Edit the function**: Modify the `decide_reward` function
3. **Test your logic**: Create a config file that uses your logic
4. **Run experiments**: Use `--config` to specify your configuration

## Writing Task Logic

Task logic is a single Python function that answers: "Should this bat get a reward?"

### The Basic Template

```python
def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Your reward logic goes here
    
    Args:
        bat: Information about the bat (position, ID, etc.)
        feeder: Information about the feeder (position, settings, etc.)
        event: What triggered this evaluation (beam break, timer, etc.)
        config: Your custom configuration from the config file
        
    Returns:
        bool: True if reward should be delivered, False otherwise
    """
    # Your logic here
    return True  # or False
```

### Available Information

#### About the Bat (`bat: BatInfo`)
- `bat.id` - Unique identifier (e.g., "bat_001")
- `bat.position` - Current position (x, y, z) in meters
- `bat.position_age` - How old the position data is (seconds)
- `bat.is_active` - Whether the bat can receive rewards
- `bat.time_since_last_reward` - Seconds since last reward (None if never)
- `bat.last_reward_feeder_id` - Which feeder gave the last reward

#### About the Feeder (`feeder: FeederInfo`)
- `feeder.id` - Feeder identifier (0, 1, 2, etc.)
- `feeder.position` - Feeder position (x, y, z) in meters
- `feeder.is_available` - Whether feeder is free (not owned by another bat)
- `feeder.activation_radius` - Normal activation distance in meters
- `feeder.duration_ms` - How long the motor runs
- `feeder.probability` - Base probability setting

#### About the Event (`event: TriggerEvent`)
- `event.type` - What triggered this ("beam_break", "proximity", "timer")
- `event.feeder_id` - Which feeder was involved
- `event.bat_id` - Which bat triggered it
- `event.timestamp` - When it happened

#### Your Configuration (`config: dict`)
This comes from your configuration file's `task_logic_config` section.

### Helper Functions

Import these from `task_logic.utils`:

```python
from task_logic.utils import calculate_distance, is_within_radius

# Calculate 3D distance between bat and feeder
distance = calculate_distance(bat.position, feeder.position)

# Check if bat is within a certain radius
if is_within_radius(bat.position, feeder.position, 1.5):
    # Bat is within 1.5 meters
```

## Example Task Logic

### Simple Proximity Logic

```python
def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """Reward if bat is close enough"""
    max_distance = config.get('max_distance', 1.0)
    
    if not bat.is_active:
        return False
    
    distance = calculate_distance(bat.position, feeder.position)
    return distance <= max_distance and feeder.is_available
```

### Time-Based Logic

```python
# Global state to track when bats arrived
_arrival_times = {}

def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """Reward after bat stays near feeder for specified time"""
    required_time = config.get('required_time', 2.0)
    max_distance = config.get('max_distance', 1.0)
    
    key = f"{bat.id}_{feeder.id}"
    
    # Check if bat is close enough
    distance = calculate_distance(bat.position, feeder.position)
    if distance > max_distance:
        # Too far - reset timer
        _arrival_times.pop(key, None)
        return False
    
    # Close enough - check timing
    if key not in _arrival_times:
        _arrival_times[key] = event.timestamp
        return False  # Just arrived
    
    time_waiting = event.timestamp - _arrival_times[key]
    if time_waiting >= required_time:
        _arrival_times.pop(key, None)  # Reset for next time
        return feeder.is_available
    
    return False  # Still waiting
```

### Probabilistic Logic

```python
import random

def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """Reward with certain probability"""
    probability = config.get('probability', 0.5)
    
    if not bat.is_active or not feeder.is_available:
        return False
    
    # Basic proximity check
    distance = calculate_distance(bat.position, feeder.position)
    if distance > feeder.activation_radius:
        return False
    
    # Apply probability
    return random.random() < probability
```

## Configuration Files

### Basic Structure

```json
{
  "experiment": {
    "name": "My Experiment",
    "scientist": "your_name", 
    "task_logic": "my_logic_file"
  },
  "task_logic_config": {
    "my_logic_file": {
      "parameter1": "value1",
      "parameter2": 123
    }
  }
}
```

### Key Sections

- **experiment**: Metadata about your study
- **task_logic_config**: Parameters for your logic function
- **feeders**: Feeder positions and settings
- **room**: Room boundaries
- **rtls_system**: Position tracking settings
- **gui**: Display preferences
- **logging**: Data saving settings

### Starting from Templates

Use the template files in `config/templates/`:

- `proximity_study.json` - Distance-based rewards
- `delayed_reward_study.json` - Time-based rewards  
- `control_baseline.json` - Random rewards

## Testing Your Logic

### 1. Validate Configuration
```bash
python main.py --config config/my_experiment.json --validate
```

### 2. Test with Mock Data
```bash
python main.py --config config/my_experiment.json --mock
```

### 3. Quick Logic Test
Create a simple test script:

```python
from task_logic.interface import BatInfo, FeederInfo, TriggerEvent
from task_logic.logics.my_logic import decide_reward

# Test data
bat = BatInfo("bat_001", (2.0, 1.0, 1.5), 0.1, True, None, None)
feeder = FeederInfo(0, (2.5, 1.2, 1.5), True, 1.0, 100, 1.0)
event = TriggerEvent("beam_break", 0, "bat_001", 1234567890)
config = {"max_distance": 1.0}

result = decide_reward(bat, feeder, event, config)
print(f"Should reward: {result}")
```

## Common Patterns

### Distance Thresholds
```python
distance = calculate_distance(bat.position, feeder.position)
if distance <= config.get('close_distance', 0.5):
    return True
elif distance <= config.get('far_distance', 1.5):
    return random.random() < 0.5  # 50% chance
else:
    return False
```

### Time Windows
```python
# Only reward during certain times
hour = datetime.now().hour
if config.get('start_hour', 9) <= hour <= config.get('end_hour', 17):
    # Normal logic during work hours
    return normal_reward_logic()
else:
    return False  # No rewards outside hours
```

### Multiple Criteria
```python
# All conditions must be met
checks = [
    bat.is_active,
    feeder.is_available,
    distance <= max_distance,
    bat.time_since_last_reward is None or bat.time_since_last_reward > min_interval
]
return all(checks)
```

## Getting Help

1. **Check the examples** in `task_logic/logics/examples/`
2. **Look at the templates** in `config/templates/`
3. **Use validation** with `--validate` flag
4. **Test in mock mode** with `--mock` flag

Remember: Your logic should be simple and focused. The system handles all the complexity of hardware, GUI, and data logging.