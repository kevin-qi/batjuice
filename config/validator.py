"""
Configuration Validation System
"""
import os
from typing import List, Dict, Any


class ConfigurationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigurationValidator:
    """Validates configuration files for completeness and correctness"""
    
    REQUIRED_SECTIONS = ['rtls_system', 'arduino', 'feeders', 'room']
    VALID_RTLS_BACKENDS = ['cortex', 'ciholas', 'mock']
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration and return list of errors
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required sections
        for section in self.REQUIRED_SECTIONS:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Validate RTLS backend
        self._validate_rtls_config(config, errors)
        
        # Validate feeder configurations
        self._validate_feeder_configs(config, errors)
        
        # Validate room boundaries
        self._validate_room_config(config, errors)
        
        # Validate task logic configuration
        self._validate_task_logic_config(config, errors)
        
        return errors
    
    def _validate_rtls_config(self, config: Dict[str, Any], errors: List[str]):
        """Validate RTLS system configuration"""
        rtls_config = config.get('rtls_system', {})
        backend = rtls_config.get('backend')
        
        if backend not in self.VALID_RTLS_BACKENDS:
            errors.append(f"Invalid RTLS backend: {backend}. Must be one of {self.VALID_RTLS_BACKENDS}")
        
        # Check backend-specific configuration
        if backend == 'cortex' and 'cortex' not in config:
            errors.append("Cortex backend selected but cortex configuration missing")
        elif backend == 'ciholas' and 'ciholas' not in config:
            errors.append("Ciholas backend selected but ciholas configuration missing")
    
    def _validate_feeder_configs(self, config: Dict[str, Any], errors: List[str]):
        """Validate feeder configurations"""
        feeders = config.get('feeders', [])
        
        if not feeders:
            errors.append("No feeders configured")
            return
        
        feeder_ids = set()
        room_boundaries = config.get('room', {}).get('boundaries', {})
        
        for i, feeder in enumerate(feeders):
            feeder_id = feeder.get('id')
            
            # Check for duplicate IDs
            if feeder_id in feeder_ids:
                errors.append(f"Duplicate feeder ID: {feeder_id}")
            feeder_ids.add(feeder_id)
            
            # Support both old single position format and new multiple positions format
            if 'position' in feeder:
                # Old format - single position
                required_fields = ['id', 'position', 'activation_radius']
                for field in required_fields:
                    if field not in feeder:
                        errors.append(f"Feeder {feeder_id}: Missing required field '{field}'")
                
                position = feeder.get('position', [])
                if len(position) != 3:
                    errors.append(f"Feeder {feeder_id}: Position must be [x, y, z]")
                elif room_boundaries:
                    self._validate_position_in_room(feeder_id, position, room_boundaries, errors)
            
            elif 'positions' in feeder:
                # New format - multiple positions
                required_fields = ['id', 'positions', 'default_position', 'activation_radius']
                for field in required_fields:
                    if field not in feeder:
                        errors.append(f"Feeder {feeder_id}: Missing required field '{field}'")
                
                positions = feeder.get('positions', [])
                if not positions:
                    errors.append(f"Feeder {feeder_id}: No positions defined")
                    continue
                
                default_pos = feeder.get('default_position', 0)
                if default_pos < 0 or default_pos >= len(positions):
                    errors.append(f"Feeder {feeder_id}: default_position {default_pos} out of range (0-{len(positions)-1})")
                
                # Validate each position
                for j, pos_config in enumerate(positions):
                    if not isinstance(pos_config, dict):
                        errors.append(f"Feeder {feeder_id}, position {j}: Must be an object with name, coordinates, description")
                        continue
                    
                    pos_required = ['name', 'coordinates']
                    for field in pos_required:
                        if field not in pos_config:
                            errors.append(f"Feeder {feeder_id}, position {j}: Missing '{field}'")
                    
                    coordinates = pos_config.get('coordinates', [])
                    if len(coordinates) != 3:
                        errors.append(f"Feeder {feeder_id}, position {j}: Coordinates must be [x, y, z]")
                    elif room_boundaries:
                        self._validate_position_in_room(f"{feeder_id}_pos{j}", coordinates, room_boundaries, errors)
            
            else:
                errors.append(f"Feeder {feeder_id}: Must have either 'position' (single) or 'positions' (multiple)")
    
    def _validate_room_config(self, config: Dict[str, Any], errors: List[str]):
        """Validate room configuration"""
        room = config.get('room', {})
        boundaries = room.get('boundaries', {})
        
        required_bounds = ['x_min', 'x_max', 'y_min', 'y_max', 'z_min', 'z_max']
        for bound in required_bounds:
            if bound not in boundaries:
                errors.append(f"Room boundaries: Missing {bound}")
        
        # Check that min < max for each dimension
        if all(bound in boundaries for bound in required_bounds):
            if boundaries['x_min'] >= boundaries['x_max']:
                errors.append("Room boundaries: x_min must be less than x_max")
            if boundaries['y_min'] >= boundaries['y_max']:
                errors.append("Room boundaries: y_min must be less than y_max")
            if boundaries['z_min'] >= boundaries['z_max']:
                errors.append("Room boundaries: z_min must be less than z_max")
    
    def _validate_task_logic_config(self, config: Dict[str, Any], errors: List[str]):
        """Validate task logic configuration"""
        experiment = config.get('experiment', {})
        task_logic = experiment.get('task_logic')
        
        if task_logic:
            # Check if task logic module exists
            logic_file = f"task_logic/logics/{task_logic}.py"
            if not os.path.exists(logic_file):
                errors.append(f"Task logic module not found: {logic_file}")
            
            # Check if configuration exists for the task logic
            task_logic_configs = config.get('task_logic_config', {})
            if task_logic not in task_logic_configs:
                errors.append(f"No configuration found for task logic: {task_logic}")
    
    def _validate_position_in_room(self, feeder_id: int, position: List[float], 
                                 boundaries: Dict[str, float], errors: List[str]):
        """Check if feeder position is within room boundaries"""
        x, y, z = position
        
        if not (boundaries['x_min'] <= x <= boundaries['x_max']):
            errors.append(f"Feeder {feeder_id}: x position {x} outside room bounds "
                         f"[{boundaries['x_min']}, {boundaries['x_max']}]")
        
        if not (boundaries['y_min'] <= y <= boundaries['y_max']):
            errors.append(f"Feeder {feeder_id}: y position {y} outside room bounds "
                         f"[{boundaries['y_min']}, {boundaries['y_max']}]")
        
        if not (boundaries['z_min'] <= z <= boundaries['z_max']):
            errors.append(f"Feeder {feeder_id}: z position {z} outside room bounds "
                         f"[{boundaries['z_min']}, {boundaries['z_max']}]")
    
    def validate_and_raise(self, config: Dict[str, Any]):
        """Validate configuration and raise exception if invalid"""
        errors = self.validate(config)
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ConfigurationError(error_msg)