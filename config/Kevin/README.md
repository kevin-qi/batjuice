# Kevin's Experiment Configurations

This folder contains paired configuration files for experiments:
- `.json` files: System configuration (feeders, room, hardware, etc.)
- `.py` files: Task logic code (reward decision algorithm)

## Using Your Experiments

Run an experiment by specifying just the name (without extension):

```bash
python main.py --config Kevin/proximity_study
```

The system automatically loads both `proximity_study.json` and `proximity_study.py`.

## Creating New Experiments

1. Copy an existing pair of files (e.g., `proximity_study.json` and `proximity_study.py`)
2. Rename both files to match your new experiment name
3. Edit the `.json` file to configure:
   - Experiment metadata (name, scientist, date)
   - Feeder positions and parameters
   - Task logic configuration parameters (in `task_logic_config` section)
4. Edit the `.py` file to implement your reward logic in the `decide_reward()` function

## Task Logic Files

Your `.py` file must contain a `decide_reward()` function:

```python
def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """
    Return True to deliver reward, False to withhold it.

    Args:
        bat: Information about the bat (position, active state, history)
        feeder: Information about the feeder (position, settings)
        event: The trigger event (beam break, proximity, etc.)
        config: Your custom parameters from task_logic_config in .json

    Returns:
        bool: True to deliver reward, False otherwise
    """
    # Your logic here
    pass
```

See `proximity_study.py` for a complete example.