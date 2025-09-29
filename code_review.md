# Code Review and Refactoring Plan

## Executive Summary
The batjuice codebase is functional but requires cleanup and architectural improvements to achieve proper separation between scientific task logic and engineering infrastructure. This document provides a complete refactoring plan prioritized by impact and complexity.

## Part 1: Immediate Cleanup (30 minutes)

### 1.1 Delete Deprecated Code
**Files to remove:**
- `/task_logic/deprecated/` - Entire folder (3 files, ~500 lines)
  - `config_interface.py`
  - `simple_task_logic.py`
  - `task_logic_endpoint.py`
- `mock_arduino.txt` - Documentation file in root
- `Miniconda3-latest-Linux-x86_64.sh` - Installation script in root

### 1.2 Resolve Duplicate Implementations
**Choose and remove one:**
- Keep `gui/comprehensive_config_display.py`
- Delete `gui/config_display.py`
- Update imports in `gui/main_window.py`

### 1.3 Fix .gitignore
Add proper exclusions:
```gitignore
__pycache__/
*.pyc
.serena/
*.sh
```

### 1.4 Clean Up Unused Directories
- Remove `/cortex/` if not actively used
- Clean all `__pycache__` directories

## Part 2: Task Logic Architecture (2-3 hours)

### 2.1 Current Problems
- **Tight coupling**: Task logic directly imports settings, system_state, event_logger
- **Mixed responsibilities**: Business logic mixed with configuration, logging, state updates
- **Global state**: Uses singleton pattern with global `task_logic` variable
- **No clear boundary**: Scientists must understand system internals

### 2.2 Simplified Architecture Solution

#### The Core Principle
- **Scientists write**: "Should this bat get a reward?" (ONE function)
- **Engineers maintain**: Everything else (hardware, GUI, state, configuration)

#### The Minimal Interface

Create `task_logic_interface.py`:
```python
from typing import NamedTuple, Optional

class BatInfo(NamedTuple):
    """Information about a bat - provided by system"""
    id: str
    position: tuple[float, float, float]  # (x, y, z) in meters
    position_age: float  # seconds since position update
    is_active: bool  # can receive rewards
    time_since_last_reward: Optional[float]  # seconds, None if never
    last_reward_feeder_id: Optional[int]

class FeederInfo(NamedTuple):
    """Information about a feeder - provided by system"""
    id: int
    position: tuple[float, float, float]  # (x, y, z) in meters
    is_available: bool  # not owned by another bat

class TriggerEvent(NamedTuple):
    """The event that triggered evaluation"""
    type: str  # "beam_break", "proximity", "timer"
    feeder_id: int
    bat_id: str
    timestamp: float

# This is the ONLY function scientists implement
def decide_reward(bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
    """Scientists implement this single function"""
    pass
```

#### Scientist Utilities
Create `task_logic_utils.py`:
```python
import math

def calculate_distance(pos1, pos2) -> float:
    """Calculate 3D Euclidean distance"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    dz = pos1[2] - pos2[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)

def calculate_2d_distance(pos1, pos2) -> float:
    """Calculate 2D distance (ignoring z)"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return math.sqrt(dx*dx + dy*dy)
```

#### Integration Adapter
Create `task_logic_adapter.py`:
```python
class TaskLogicAdapter:
    """Bridges complex system with simple scientist logic"""
    
    def __init__(self, logic_module: str = "standard"):
        module = importlib.import_module(f"task_logics.{logic_module}")
        self.decide_reward = module.decide_reward
        self.config = self._load_config(logic_module)
    
    def should_deliver_reward(self, system_state, feeder_id, bat_id, event_type):
        """Convert system complexity to simple data structures"""
        # Extract and simplify data
        bat = BatInfo(...)  # Convert from system_state
        feeder = FeederInfo(...)  # Convert from system_state
        event = TriggerEvent(...)
        
        # Call scientist's pure function
        return self.decide_reward(bat, feeder, event, self.config)
```

### 2.3 Migration Steps

1. **Create new structure:**
   ```
   task_logic/
   ├── interface.py          # Simple data types
   ├── utils.py              # Helper functions
   ├── adapter.py            # System bridge
   └── logics/               # Scientist implementations
       ├── __init__.py
       └── standard.py       # Current logic moved here
   ```

2. **Move current logic** to `logics/standard.py` as simple function

3. **Update controller** to use adapter (minimal changes)

4. **Create examples** in `logics/examples/`

## Part 3: Code Quality Improvements (1-2 hours)

### 3.1 DRY Violations to Fix

#### Configuration Consolidation
**Problem**: Configuration scattered across 4+ files
**Solution**: 
- Create single `ConfigManager` class
- One source of truth: `config/user_config.json`
- Remove redundant default values

#### Error Handling Pattern
**Problem**: Repetitive try-catch blocks
**Solution**:
```python
# Create decorator
def safe_operation(default_return=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} error: {e}")
                return default_return
        return wrapper
    return decorator

# Usage
@safe_operation(default_return=False)
def check_beam_break(self, feeder_id):
    # implementation
```

#### State Management
**Problem**: Duplicate state tracking
**Solution**:
- Single `SystemState` instance
- Observer pattern for state changes
- Remove local state copies in GUI

### 3.2 Naming Convention Standardization
- Use `snake_case` consistently (not `camelCase`)
- Replace unclear abbreviations:
  - `pos` → `position`
  - `config` → `configuration`
  - `cb` → `callback`

## Part 4: Implementation Schedule

### Week 1: Cleanup and Preparation
**Day 1-2: Immediate Cleanup (2 hours)**
- Delete deprecated files
- Fix duplicate GUIs
- Update .gitignore
- Remove unused directories

**Day 3-5: Prepare Architecture (3 hours)**
- Create interface.py with simple types
- Create utils.py with helper functions
- Create adapter.py skeleton
- Set up logics/ directory structure

### Week 2: Core Refactoring
**Day 1-3: Implement Adapter (4 hours)**
- Build TaskLogicAdapter class
- Convert current logic to new format
- Update FeederController to use adapter
- Test with existing functionality

**Day 4-5: Testing and Documentation (3 hours)**
- Create unit tests for adapter
- Write SCIENTIST_GUIDE.md
- Create example logic implementations
- Update main README

### Week 3: Code Quality
**Day 1-2: Fix DRY Violations (3 hours)**
- Consolidate configuration management
- Implement error handling decorator
- Centralize state management

**Day 3-5: Final Polish (2 hours)**
- Standardize naming conventions
- Add type hints throughout
- Update all documentation
- Final testing

## Part 5: Success Metrics

### For Scientists
- Can write new logic in < 30 minutes
- Logic files < 50 lines
- No imports from core system
- Can test without running full system

### For Engineers  
- Clear separation of concerns
- No task logic in controller/GUI
- Single adapter file contains bridge complexity
- Easy to swap logic implementations

### For System
- All tests pass after refactoring
- No performance degradation
- Backwards compatible with existing configs
- Clean git history with atomic commits

## Part 6: Files Affected

### To Delete (Immediate)
- `/task_logic/deprecated/*` (3 files)
- `/gui/config_display.py`
- `mock_arduino.txt`
- `Miniconda3-latest-Linux-x86_64.sh`

### To Create (New Architecture)
- `/task_logic/interface.py`
- `/task_logic/utils.py`
- `/task_logic/adapter.py`
- `/task_logic/logics/standard.py`
- `/task_logic/logics/examples/*`
- `/docs/SCIENTIST_GUIDE.md`

### To Modify (Integration)
- `/controller/feeder_controller.py` (use adapter)
- `/gui/main_window.py` (remove duplicate import)
- `/task_logic/__init__.py` (export new interface)
- `/.gitignore` (add exclusions)

## Part 7: Risk Mitigation

### Backup Strategy
- Create feature branch before changes
- Commit after each major step
- Keep deprecated code in separate branch initially

### Testing Plan
1. Unit tests for new adapter
2. Integration tests with mock systems
3. Full system test with existing configs
4. Scientist acceptance testing

### Rollback Plan
- Git revert to previous commit if issues
- Keep old task_logic.py until new system proven
- Parallel run both systems if needed

## Part 8: Configuration System Refactoring

### 8.1 Current Configuration Analysis

**Strengths:**
- Single source of truth in `config/user_config.json`
- Centralized Settings class with consistent interface
- Separate mock configuration for testing
- Modular config sections (RTLS, Arduino, feeders, GUI, logging)

**Critical Issues:**
- **No config file specification**: Cannot specify alternative config files via command line
- **Missing task logic config**: Task logic module not specified in configuration
- **Hardcoded defaults**: Scattered throughout codebase (COM3, 9600 baud, etc.)
- **No validation**: Minimal validation of configuration values
- **Poor error handling**: Complete failure if config files missing

### 8.2 Configuration Requirements

**Scientist Workflow Goal:**
```bash
# Each scientist runs with their own config
python main.py --config experiments/alice_proximity_study.json
python main.py --config experiments/bob_timing_study.json
python main.py --config experiments/control_baseline.json
```

**Configuration Must Include:**
- RTLS system selection and parameters
- Arduino hardware settings
- Feeder positions and behavior
- Room boundaries and coordinate system
- Task logic module specification
- GUI display preferences
- Data logging settings
- Mock mode settings

### 8.3 Improved Configuration Structure

#### Master Configuration Template
```json
{
  "experiment": {
    "name": "Alice Proximity Study",
    "scientist": "alice",
    "date": "2024-01-15",
    "task_logic": "proximity_reward",
    "description": "Testing proximity-based reward delivery"
  },
  "rtls_system": {
    "backend": "ciholas",
    "mock_mode": false
  },
  "ciholas": {
    "multicast_group": "239.255.76.67",
    "local_port": 7667,
    "frame_rate": 100,
    "serial_numbers": [12345, 12346, 12347]
  },
  "arduino": {
    "port": "COM3",
    "baudrate": 9600,
    "timeout": 2.0,
    "mock_mode": false
  },
  "room": {
    "boundaries": {
      "x_min": -2.9, "x_max": 2.9,
      "y_min": -2.6, "y_max": 2.6,
      "z_min": 0.0, "z_max": 2.5
    },
    "units": "meters"
  },
  "feeders": [
    {
      "id": 0,
      "position": [2.45, 1.3, 1.5],
      "activation_radius": 1.0,
      "reactivation_distance": 3.0,
      "duration_ms": 100,
      "speed": 255,
      "reward_probability": 1.0
    }
  ],
  "task_logic_config": {
    "proximity_reward": {
      "activation_radius": 1.0,
      "reward_probability": 1.0,
      "reactivation_time": 0.2
    }
  },
  "gui": {
    "update_rate_ms": 50,
    "window_title": "Alice Proximity Study",
    "show_3d_display": true
  },
  "logging": {
    "data_directory": "data",
    "session_prefix": "alice_proximity",
    "log_positions": true,
    "log_rewards": true,
    "log_events": true
  }
}
```

### 8.4 Configuration System Implementation

#### Enhanced Main Entry Point
```python
# main.py improvements
def main():
    parser = argparse.ArgumentParser(description='Bat Feeder Control System')
    parser.add_argument('--config', '-c', 
                       default='config/user_config.json',
                       help='Configuration file path')
    parser.add_argument('--mock', action='store_true',
                       help='Override config to run in full mock mode')
    parser.add_argument('--validate', action='store_true',
                       help='Validate configuration and exit')
    
    args = parser.parse_args()
    
    # Load and validate configuration
    try:
        settings = Settings(config_file=args.config)
        if args.validate:
            print("Configuration valid!")
            return
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        return 1
```

#### Enhanced Settings Class
```python
# config/settings.py improvements
class Settings:
    def __init__(self, config_file: str = 'config/user_config.json'):
        self.config_file = config_file
        self.config = self._load_and_validate_config()
        
    def _load_and_validate_config(self) -> dict:
        """Load configuration with validation and defaults"""
        if not os.path.exists(self.config_file):
            raise ConfigurationError(f"Config file not found: {self.config_file}")
        
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        
        # Validate required sections
        self._validate_config(config)
        
        # Apply defaults for missing values
        config = self._apply_defaults(config)
        
        return config
    
    def get_task_logic_module(self) -> str:
        """Get task logic module name"""
        return self.config.get('experiment', {}).get('task_logic', 'standard')
    
    def get_task_logic_config(self) -> dict:
        """Get configuration for the active task logic"""
        logic_name = self.get_task_logic_module()
        return self.config.get('task_logic_config', {}).get(logic_name, {})
```

#### Configuration Validation
```python
# config/validator.py
class ConfigurationValidator:
    REQUIRED_SECTIONS = ['rtls_system', 'arduino', 'feeders', 'room']
    
    def validate(self, config: dict) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Check required sections
        for section in self.REQUIRED_SECTIONS:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Validate RTLS backend exists
        rtls_backend = config.get('rtls_system', {}).get('backend')
        if rtls_backend not in ['cortex', 'ciholas', 'mock']:
            errors.append(f"Invalid RTLS backend: {rtls_backend}")
        
        # Validate feeder positions are within room boundaries
        self._validate_feeder_positions(config, errors)
        
        # Validate task logic module exists
        self._validate_task_logic(config, errors)
        
        return errors
```

### 8.5 Scientist Configuration Examples

#### Proximity Study Configuration
```json
{
  "experiment": {
    "name": "Proximity Reward Study",
    "scientist": "alice",
    "task_logic": "proximity_reward"
  },
  "task_logic_config": {
    "proximity_reward": {
      "activation_radius": 0.8,
      "reward_probability": 1.0
    }
  }
}
```

#### Timing Study Configuration  
```json
{
  "experiment": {
    "name": "Timing Delay Study", 
    "scientist": "bob",
    "task_logic": "delayed_reward"
  },
  "task_logic_config": {
    "delayed_reward": {
      "delay_seconds": 2.0,
      "max_distance": 1.5
    }
  }
}
```

#### Control Baseline Configuration
```json
{
  "experiment": {
    "name": "Control Baseline",
    "scientist": "charlie", 
    "task_logic": "random_reward"
  },
  "task_logic_config": {
    "random_reward": {
      "probability": 0.3,
      "ignore_position": true
    }
  }
}
```

### 8.6 Implementation Steps

**Step 1: Enhanced Configuration Loading (1 hour)**
- Add `--config` argument to main.py
- Update Settings class to accept config file path
- Add basic validation

**Step 2: Configuration Validation (1 hour)**
- Create ConfigurationValidator class
- Add schema validation for all sections
- Implement helpful error messages

**Step 3: Task Logic Integration (30 minutes)**
- Add task_logic specification to config
- Update TaskLogicAdapter to load based on config
- Remove hardcoded task logic selection

**Step 4: Default Configuration Generator (30 minutes)**
- Create tool to generate template configurations
- Add `--generate-config` command line option
- Include all possible sections with documentation

**Step 5: Scientist Configuration Templates (30 minutes)**
- Create `configs/templates/` directory
- Add example configurations for common studies
- Document configuration options

### 8.7 Benefits

**For Scientists:**
- Each scientist has their own configuration file
- No need to modify code or GUI settings
- Task logic specified in config, not changed during runtime
- Easy to share and version control configurations
- Clear documentation of experimental parameters

**For Engineers:**
- Single configuration system to maintain
- Clear validation prevents runtime errors
- Easy to add new configurable parameters
- Backwards compatible with existing configs

**For System:**
- Fail fast with clear error messages
- No more scattered hardcoded values
- Consistent configuration interface
- Easy testing with different configurations

## Conclusion

This refactoring plan addresses the core issues while maintaining simplicity:

1. **Immediate wins**: Remove 500+ lines of dead code
2. **Architecture fix**: Clear scientist/engineer boundary with single-function interface  
3. **Configuration fix**: Single config file per scientist with task logic specification
4. **Code quality**: Fix DRY violations and standardize patterns
5. **Low risk**: Incremental changes with testing at each step

Total estimated time: 20.5 hours over 3 weeks (3.5 hours added for configuration improvements)

The key insight is that scientists aren't software engineers - they need the simplest possible interface to express experimental logic AND the simplest possible way to configure their experiments. This plan achieves both through minimal abstractions that isolate all complexity in the engineering domain.