# Clean Architecture Overview

## System Structure

The codebase is now organized with clear separation of concerns:

### 1. **Task Logic** (`task_logic/`)
- **Purpose**: All reward decision logic
- **Key Files**:
  - `system_state.py`: Complete system state tracking
  - `task_logic_endpoint.py`: Reward decision engine
  - `config_interface.py`: Configuration management
  - `test_task_logic.py`: Test suite

### 2. **Controller** (`controller/`)
- **Purpose**: Hardware control and state management
- **Key Files**:
  - `feeder_controller.py`: Main controller class
- **Responsibilities**:
  - Monitor beam breaks
  - Maintain system state
  - Delegate decisions to task logic
  - Execute hardware commands

### 3. **Hardware** (`hardware/`)
- **Purpose**: Low-level hardware communication
- **Key Files**:
  - `arduino_controller.py`: Real Arduino communication
  - `mock_arduino.py`: Simulation for testing

### 4. **Position Tracking** (`position_tracking/`)
- **Purpose**: Position data acquisition
- **Key Files**:
  - `cortex_tracker.py`: Cortex MotionAnalysis
  - `ciholas_tracker.py`: Ciholas UWB
  - `mock_tracker.py`: Playback of recorded experimental data

### 5. **GUI** (`gui/`)
- **Purpose**: User interface
- **Key Files**:
  - `main_window.py`: Main application window
  - `feeder_panel.py`: Feeder control and monitoring
  - `bat_panel.py`: Bat state display
  - `flight_display_3d.py`: 3D visualization

### 6. **Data Logging** (`data_logging/`)
- **Purpose**: Event and session logging
- **Key Files**:
  - `data_logger.py`: Session data logging
  - `event_logger.py`: System event logging

### 7. **Configuration** (`config/`)
- **Purpose**: System configuration management
- **Key Files**:
  - `settings.py`: Main configuration manager
  - `default_config.json`: Default system settings
  - `user_config.json`: User-specific settings
  - `task_logic_config.json`: Task logic parameters

### 8. **Utilities** (`utils/`)
- **Purpose**: Shared data structures and utilities
- **Key Files**:
  - `data_structures.py`: Position, RewardEvent, FeederConfig classes

## Control Flow

### Beam Break Processing
1. **Hardware Detection**: Arduino detects beam break
2. **Controller Processing**: `FeederController` receives beam break event
3. **State Update**: System state updated with beam break event
4. **Task Logic Query**: Controller calls `should_deliver_reward()`
5. **Decision Making**: Task logic evaluates all constraints
6. **Hardware Action**: Controller executes reward delivery if approved
7. **State Recording**: Reward event recorded in system state

### Position Updates
1. **Tracking System**: Cortex/Ciholas/Mock provides position data
2. **Controller Processing**: `FeederController.update_position()`
3. **State Update**: Bat position updated in system state
4. **GUI Update**: Position data sent to flight display

## Key Design Principles

### 1. **Separation of Concerns**
- **Task Logic**: Pure decision making, no hardware knowledge
- **Controller**: Hardware management, no decision logic
- **GUI**: Display only, no business logic

### 2. **Modularity**
- Task logic can be completely customized without touching hardware code
- Hardware can be swapped without affecting task logic
- GUI is independent of core system logic

### 3. **Clean Interfaces**
- `should_deliver_reward(system_state, feeder_id, bat_id) -> (bool, reason)`
- Single point of entry for all reward decisions
- Complete system state passed to task logic

### 4. **No Legacy Code**
- All old "feeder_logic" removed
- No "New" or "Old" naming conventions
- Clean, purposeful class and module names

### 5. **Comprehensive State Tracking**
- Complete event history maintained
- Every beam break and reward recorded with full context
- Rich debugging and analysis capabilities

## Customization Points

### Easy (Configuration File)
Edit `config/task_logic_config.json`:
```json
{
  "min_time_between_rewards": 1.0,
  "reward_probability": 0.75,
  "enable_collision_detection": true
}
```

### Medium (Runtime Parameters)
```python
from task_logic.task_logic_endpoint import update_task_parameters
update_task_parameters(min_time_between_rewards=2.0)
```

### Advanced (Custom Logic)
Modify `task_logic_endpoint.py`:
```python
def should_deliver_reward(self, system_state, feeder_id, bat_id):
    # Your custom experimental logic here
    # Full access to complete system state
    return True, "Custom condition met"
```

## Benefits of Clean Architecture

1. **Maintainability**: Clear responsibility boundaries
2. **Testability**: Each component can be tested independently  
3. **Extensibility**: Easy to add new features or tracking systems
4. **Debuggability**: Rich error reporting and state visibility
5. **Reusability**: Components can be used in different contexts
6. **Performance**: Optimized for real-time operation

## No More Legacy

- ❌ `feeder_logic/` directory
- ❌ `FeederManager` class  
- ❌ `NewFeederManager` class
- ❌ `reward_system.py`
- ❌ `position_processor.py`
- ❌ Complex legacy compatibility layers

## Current Clean Structure

- ✅ `controller/feeder_controller.py` - Hardware control
- ✅ `task_logic/task_logic_endpoint.py` - Decision logic
- ✅ `task_logic/system_state.py` - State management
- ✅ Clean separation of concerns
- ✅ Comprehensive error reporting
- ✅ Complete event history tracking
