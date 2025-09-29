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

## Conclusion

This refactoring plan addresses the core issues while maintaining simplicity:

1. **Immediate wins**: Remove 500+ lines of dead code
2. **Architecture fix**: Clear scientist/engineer boundary with single-function interface  
3. **Code quality**: Fix DRY violations and standardize patterns
4. **Low risk**: Incremental changes with testing at each step

Total estimated time: 17 hours over 3 weeks (can be accelerated if needed)

The key insight is that scientists aren't software engineers - they need the simplest possible interface to express experimental logic. This plan achieves that through a minimal, clean abstraction that isolates all complexity in the engineering domain.