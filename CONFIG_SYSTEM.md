# Configuration System

## Overview

The config system uses **paired files** for each experiment:
- `.json` - Complete configuration (hardware, feeders, task logic parameters, mock settings)
- `.py` - Task logic code (reward decision algorithm)

## Folder Structure

```
config/
├── Kevin/                          # User-specific folder
│   ├── proximity_study.json       # Experiment configuration
│   ├── proximity_study.py         # Task logic code
│   └── README.md                  # Documentation
├── mock_config.json               # Mock settings (testing only, not experiment-specific)
├── settings.py                    # Config loader
└── validator.py                   # Config validator

task_logic/                        # Core infrastructure (don't modify)
├── adapter.py                     # Loads user .py files
├── interface.py                   # Simple API for scientists
├── system_state.py                # State management
├── task_logic.py                  # Initialization
└── utils.py                       # Helper functions
```

## Usage

Run an experiment by specifying just the experiment name:

```bash
# Default (runs Kevin/proximity_study)
python main.py --mock-rtls --mock-arduino

# Explicit experiment
python main.py --config Kevin/proximity_study --mock-rtls --mock-arduino
```

The system automatically loads both `.json` and `.py` files.

## Creating New Experiments

### Option 1: New experiment for existing user

```bash
# Copy Kevin's proximity study
cp config/Kevin/proximity_study.json config/Kevin/my_experiment.json
cp config/Kevin/proximity_study.py config/Kevin/my_experiment.py

# Edit both files for your experiment
# Run with:
python main.py --config Kevin/my_experiment
```

### Option 2: New user folder

```bash
# Create folder for new user
mkdir config/Alice

# Copy example files
cp config/Kevin/proximity_study.* config/Alice/

# Edit for Alice's experiments
# Run with:
python main.py --config Alice/proximity_study
```

## Configuration File Structure

Each `.json` file contains:

1. **Experiment Info** - Name, scientist, date, description
2. **Hardware Config** - RTLS backend, Arduino port, room boundaries
3. **Feeder Config** - Positions, activation radius, reactivation distance
4. **Task Logic Config** - Custom parameters used by your `.py` logic
5. **GUI/Logging** - Display and data logging settings

**Note**: Mock settings are in `config/mock_config.json` (separate file for testing, not part of experiments)

## Task Logic Files

Your `.py` file must implement the `decide_reward()` function:

```python
from task_logic.interface import BatInfo, FeederInfo, TriggerEvent

def decide_reward(bat: BatInfo, feeder: FeederInfo,
                 event: TriggerEvent, config: dict) -> bool:
    """
    Decide whether to deliver a reward.

    Args:
        bat: Bat information (position, active state, history)
        feeder: Feeder information (position, settings)
        event: Trigger event (beam break details)
        config: Your parameters from task_logic_config in .json

    Returns:
        True to deliver reward, False to withhold
    """
    # Your decision logic here
    return True
```

See `config/Kevin/proximity_study.py` for a complete example.

## Benefits

- **Single file pair per experiment** - Everything needed in 2 files
- **User-specific folders** - Each scientist has their own space
- **Clean separation** - Core code in `task_logic/`, user code in `config/`
- **Simple to run** - Just specify the experiment name
- **Easy to share** - Copy a folder to share all experiments