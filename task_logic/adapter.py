"""
Task Logic Adapter - Bridges complex system with simple scientist logic
"""
import importlib
import time
from typing import Tuple
from .interface import BatInfo, FeederInfo, TriggerEvent
from task_logic.system_state import SystemState


class TaskLogicAdapter:
    """Bridges complex system state with simple scientist interface"""
    
    def __init__(self, logic_module: str = "standard", config: dict = None):
        """
        Initialize adapter with specified logic module
        
        Args:
            logic_module: Name of logic module to load from task_logic.logics
            config: Task-specific configuration
        """
        self.logic_module_name = logic_module
        self.config = config or {}
        self._load_logic_module()
    
    def _load_logic_module(self):
        """Load the scientist's decision function"""
        try:
            module_path = f"task_logic.logics.{self.logic_module_name}"
            module = importlib.import_module(module_path)
            self.decide_reward = module.decide_reward
            print(f"Loaded task logic: {self.logic_module_name}")
        except ImportError as e:
            print(f"Failed to load task logic '{self.logic_module_name}': {e}")
            # Fallback to standard logic
            from task_logic.logics.standard import decide_reward
            self.decide_reward = decide_reward
            print("Using fallback standard logic")
    
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
            bat_info = BatInfo(
                id=triggering_bat_id,
                position=(bat_state.x, bat_state.y, bat_state.z),
                position_age=current_time - bat_state.position_timestamp,
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
                return True, f"Reward approved by {self.logic_module_name} logic"
            else:
                return False, f"Reward denied by {self.logic_module_name} logic"
                
        except Exception as e:
            return False, f"Error in task logic: {e}"
    
    def _calculate_time_since_last_reward(self, bat_state, current_time) -> float:
        """Calculate time since last reward"""
        if bat_state.last_reward_timestamp is None:
            return None
        return current_time - bat_state.last_reward_timestamp
    
    def reload_logic(self, logic_module: str = None, config: dict = None):
        """Reload logic module (useful for testing)"""
        if logic_module:
            self.logic_module_name = logic_module
        if config is not None:
            self.config = config
        
        # Clear module cache to force reload
        module_path = f"task_logic.logics.{self.logic_module_name}"
        if module_path in importlib.sys.modules:
            del importlib.sys.modules[module_path]
        
        self._load_logic_module()
    
    def get_config(self) -> dict:
        """Get current configuration"""
        return self.config.copy()
    
    def update_config(self, new_config: dict):
        """Update configuration"""
        self.config.update(new_config)