# Experiment Configuration Guide

This folder contains paired configuration files for experiments:
- `.json` files: System configuration (feeders, room, hardware, etc.)
- `.py` files: Task logic code (reward decision algorithm)

## Using Your Experiments

The `--config` argument supports multiple path formats:

```bash
# Short format (relative to config/ directory, no extension needed)
python main.py --config Kevin/proximity_study

# Relative path with extension (relative to config/ directory)
python main.py --config Kevin/proximity_study.json

# Relative path from project root
python main.py --config config/Kevin/proximity_study.json

# Absolute path
python main.py --config /absolute/path/to/experiment.json

# Extensions (.json or .py) are optional - the system finds both files automatically
```

The system automatically loads both the `.json` and `.py` files (if paired file exists).

## Configuration File Structure

Your `task_logic.json` file should have the following structure:

### Experiment Section
Frequently modified metadata about your experiment:

```json
{
  "experiment": {
    "name": "my_experiment",
    "description": "Description of what this experiment tests",
    "data_directory": "data"
  }
}
```

**Fields:**
- `name`: Experiment identifier (used in filenames)
- `description`: Brief description of the experiment
- `data_directory`: Directory where data logs will be saved

### Feeders Section
Configuration for each feeder in the system:

```json
{
  "feeders": [
    {
      "id": 0,
      "position": [2.45, 1.3, 1.5],
      "activation_radius": 0.8,
      "reactivation_distance": 3.0,
      "duration_ms": 100,
      "speed": 255,
      "probability": 1.0,
      "description": "Feeder 0 - Left side"
    }
  ]
}
```

**Fields:**
- `id`: Unique feeder identifier (0, 1, 2, ...)
- `position`: [x, y, z] coordinates in meters
- `activation_radius`: Distance (m) from feeder where bat can trigger reward
- `reactivation_distance`: Distance (m) bat must travel away to become active again
- `duration_ms`: Feeder motor run duration in milliseconds
- `speed`: Motor speed (0-255)
- `probability`: Probability of reward delivery (0.0-1.0)
- `description`: Human-readable description

### RTLS System Section
Real-time location tracking system backend:

```json
{
  "rtls_system": {
    "backend": "ciholas"
  }
}
```

**Fields:**
- `backend`: Tracking system type ("cortex" or "ciholas")

### Room Section
Physical room boundaries (rarely modified):

```json
{
  "room": {
    "boundaries": {
      "x_min": -2.9,
      "x_max": 2.9,
      "y_min": -2.6,
      "y_max": 2.6,
      "z_min": 0.0,
      "z_max": 2.5
    },
    "units": "meters"
  }
}
```

**Fields:**
- `boundaries`: Min/max coordinates for room dimensions
- `units`: Measurement units (typically "meters")

### GUI Section
GUI display settings (rarely modified):

```json
{
  "gui": {
    "refresh_rate_hz": 10,
    "stationary_threshold": 0.5,
    "position_timeout_gui": 1.0
  }
}
```

**Fields:**
- `refresh_rate_hz`: GUI update frequency in Hz
- `stationary_threshold`: Speed threshold (m/s) below which bat is considered stationary
- `position_timeout_gui`: Timeout (s) for considering position data stale in GUI

### Arduino Section
Arduino communication settings (rarely modified):

```json
{
  "arduino": {
    "port": "COM3",
    "baudrate": 9600,
    "timeout": 1.0
  }
}
```

**Fields:**
- `port`: Serial port for Arduino connection
- `baudrate`: Serial communication baud rate
- `timeout`: Serial communication timeout in seconds

### Cortex Section
Cortex motion capture system settings (rarely modified):

```json
{
  "cortex": {
    "server_ip": "127.0.0.1",
    "server_port": 1001,
    "timeout": 5.0,
    "frame_rate": 120
  }
}
```

**Fields:**
- `server_ip`: Cortex server IP address
- `server_port`: Cortex server port
- `timeout`: Connection timeout in seconds
- `frame_rate`: Expected tracking frame rate in Hz

### Ciholas Section
Ciholas UWB tracking system settings (rarely modified):

```json
{
  "ciholas": {
    "multicast_group": "239.255.76.67",
    "local_port": 7667,
    "timeout": 20,
    "frame_rate": 100,
    "serial_numbers": [12345, 12346, 12347, 12348],
    "coordinate_units": "mm",
    "coordinate_scale": 10.0
  }
}
```

**Fields:**
- `multicast_group`: UDP multicast group address
- `local_port`: UDP port for receiving data
- `timeout`: Connection timeout in seconds
- `frame_rate`: Expected tracking frame rate in Hz
- `serial_numbers`: List of tag serial numbers to track
- `coordinate_units`: Units from Ciholas system ("mm")
- `coordinate_scale`: Scaling factor to convert to meters (divide by this value)

### Logging Section
Logging configuration (rarely modified):

```json
{
  "logging": {
    "log_level": "INFO"
  }
}
```

**Fields:**
- `log_level`: Logging verbosity ("DEBUG", "INFO", "WARNING", "ERROR")

## Task Logic Files

Your `task_logic.py` file must contain a `decide_reward()` function:

```python
def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Return True to deliver reward, False to withhold it.

    Args:
        bat: Information about the bat (position, active state, history)
        feeder: Information about the feeder (position, settings)
        event: The trigger event (beam break, proximity, etc.)
        config: Empty dict (all parameters now in feeder properties)

    Returns:
        bool: True to deliver reward, False otherwise
    """
    # Your logic here
    pass
```

### Available Properties

**BatInfo properties:**
- `bat_id`: Bat identifier
- `position`: Current [x, y, z] position
- `is_active`: Whether bat can receive rewards
- `last_reward_time`: Timestamp of last reward

**FeederInfo properties:**
- `feeder_id`: Feeder identifier
- `position`: Feeder [x, y, z] position
- `activation_radius`: Activation distance in meters
- `probability`: Reward probability (0.0-1.0)
- `is_available`: Whether feeder is available

**TriggerEvent properties:**
- `timestamp`: Event timestamp
- `event_type`: Type of trigger event

## Creating New Experiments

1. Copy an existing pair of files (e.g., `proximity_study.json` and `proximity_study.py`)
2. Rename both files to match your new experiment name
3. Edit the `.json` file:
   - Update `experiment` section with your name and description
   - Configure feeder positions and parameters
   - Adjust RTLS backend if needed
4. Edit the `.py` file to implement your reward logic in `decide_reward()`
5. Run with: `python main.py --config Your/experiment_name`

## Notes

- All configuration parameters come from the feeder properties in the JSON
- The `config` dict passed to `decide_reward()` is now empty
- Distance calculations always use 3D Euclidean distance
- Position data is timestamped and checked for staleness
- Data is logged immediately with timestamps from Arduino