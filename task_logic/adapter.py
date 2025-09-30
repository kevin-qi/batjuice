"""
Task Logic Adapter - Bridges complex system with simple scientist logic
"""
import importlib
import importlib.util
import sys
import time
from typing import Tuple, Optional
from .interface import BatInfo, FeederInfo, TriggerEvent
from task_logic.system_state import SystemState


class TaskLogicAdapter:
    """Bridges complex system state with simple scientist interface"""

    def __init__(self, logic_path: Optional[str] = None, config: dict = None):
        """
        Initialize adapter with specified logic file

        Args:
            logic_path: Path to .py file containing decide_reward function (e.g., "config/Kevin/proximity_study.py")
                       If None, uses default logic
            config: Task-specific configuration from task_logic_config section
        """
        self.logic_path = logic_path
        self.config = config or {}
        self._load_logic_module()

    def _load_logic_module(self):
        """Load the scientist's decision function from file path"""
        if self.logic_path:
            try:
                # Load module from file path
                spec = importlib.util.spec_from_file_location("user_task_logic", self.logic_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules["user_task_logic"] = module
                    spec.loader.exec_module(module)
                    self.decide_reward = module.decide_reward
                    print(f"Loaded task logic from: {self.logic_path}")
                    return
                else:
                    print(f"Failed to load task logic from '{self.logic_path}': invalid spec")
            except Exception as e:
                print(f"Failed to load task logic from '{self.logic_path}': {e}")

        # Fallback: use default always-approve logic
        print("Using default task logic (always approve)")
        self.decide_reward = self._default_logic

    def _default_logic(self, bat: BatInfo, feeder: FeederInfo, event: TriggerEvent, config: dict) -> bool:
        """Default fallback logic - approve all rewards for active bats"""
        return bat.is_active and feeder.is_available
    
    def should_deliver_reward(self, system_state: SystemState, feeder_id: int, 
                            triggering_bat_id: str) -> Tuple[bool, str]:
        """
        Convert system complexity to simple data structures and call scientist logic
        
        Args:
            system_state: Complete system state
            feeder_id: ID of feeder with beam break
            triggering_bat_id: ID of triggering bat
            
        Returns:
            tuple: (should_deliver: bool, reason: str)
        """
        current_time = time.time()
        
        # Validate inputs
        if feeder_id not in system_state.feeders:
            return False, f"Unknown feeder ID: {feeder_id}"
        
        if triggering_bat_id not in system_state.bats:
            return False, f"Unknown bat ID: {triggering_bat_id}"
        
        feeder_state = system_state.feeders[feeder_id]
        bat_state = system_state.bats[triggering_bat_id]
        
        # Check basic system requirements
        if not feeder_state.active:
            return False, f"Feeder {feeder_id} is inactive"
        
        if not bat_state.active:
            return False, f"Bat {triggering_bat_id} is inactive"
        
        # Convert system state to simple data structures
        try:
            # Extract position from last_position tuple (x, y, z, timestamp)
            position = (0.0, 0.0, 0.0)
            position_age = float('inf')
            if bat_state.last_position and len(bat_state.last_position) >= 4:
                position = bat_state.last_position[:3]
                position_age = current_time - bat_state.last_position[3]

            bat_info = BatInfo(
                id=triggering_bat_id,
                position=position,
                position_age=position_age,
                is_active=bat_state.activation_state == "ACTIVE",
                time_since_last_reward=self._calculate_time_since_last_reward(bat_state, current_time),
                last_reward_feeder_id=bat_state.last_reward_feeder_id
            )
            
            feeder_info = FeederInfo(
                id=feeder_id,
                position=(feeder_state.x_position, feeder_state.y_position, feeder_state.z_position),
                is_available=feeder_state.owner_bat_id is None,
                activation_radius=feeder_state.activation_radius,
                duration_ms=feeder_state.duration_ms,
                probability=feeder_state.probability
            )
            
            trigger_event = TriggerEvent(
                type="beam_break",  # Currently only beam breaks trigger this
                feeder_id=feeder_id,
                bat_id=triggering_bat_id,
                timestamp=current_time
            )
            
            # Call scientist's decision function
            should_reward = self.decide_reward(bat_info, feeder_info, trigger_event, self.config)
            
            if should_reward:
                logic_name = self.logic_path if self.logic_path else "default"
                return True, f"Reward approved by task logic"
            else:
                logic_name = self.logic_path if self.logic_path else "default"
                return False, f"Reward denied by task logic"
                
        except Exception as e:
            return False, f"Error in task logic: {e}"
    
    def _calculate_time_since_last_reward(self, bat_state, current_time) -> float:
        """Calculate time since last reward"""
        if bat_state.last_reward_timestamp is None:
            return None
        return current_time - bat_state.last_reward_timestamp
    
    def reload_logic(self, logic_path: str = None, config: dict = None):
        """Reload logic module from file path (useful for testing)"""
        if logic_path:
            self.logic_path = logic_path
        if config is not None:
            self.config = config

        # Clear user_task_logic module from cache to force reload
        if "user_task_logic" in sys.modules:
            del sys.modules["user_task_logic"]

        self._load_logic_module()
    
    def get_config(self) -> dict:
        """Get current configuration"""
        return self.config.copy()
    
    def update_config(self, new_config: dict):
        """Update configuration"""
        self.config.update(new_config)