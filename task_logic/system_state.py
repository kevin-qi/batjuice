"""
Enhanced system state data structures for modular task logic.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import time


@dataclass
class HistoryEvent:
    """Base class for all historical events"""
    timestamp: float
    bat_id: str
    feeder_id: int
    event_name: str
    
    @classmethod
    def create_now(cls, bat_id: str, feeder_id: int, event_name: str):
        """Create event with current timestamp"""
        return cls(time.time(), bat_id, feeder_id, event_name)


@dataclass
class BeamBreakEvent(HistoryEvent):
    """Beam break trigger event"""
    distance_to_feeder: float = 0.0
    bat_position: Optional[tuple] = None  # (x, y, z) at time of trigger
    
    def __post_init__(self):
        if not self.event_name:
            self.event_name = "beam_break"


@dataclass
class RewardDeliveryEvent(HistoryEvent):
    """Reward delivery event"""
    manual: bool = False
    duration_ms: int = 0
    motor_speed: int = 0
    
    def __post_init__(self):
        if not self.event_name:
            self.event_name = "reward_delivery"


@dataclass
class SystemBat:
    """Enhanced bat state with complete history tracking"""
    bat_id: str
    tag_id: str  # SN for Ciholas, markerset name for Cortex
    active: bool = True
    
    # Task logic state
    activation_state: str = "ACTIVE"  # "ACTIVE" or "INACTIVE"
    last_reward_feeder_id: Optional[int] = None
    last_reward_time: Optional[float] = None
    distance_threshold_met_time: Optional[float] = None  # When bat first moved >D away
    
    # Current state
    last_position: Optional[tuple] = None  # (x, y, z, timestamp)
    
    # Event histories
    beam_break_history: List[BeamBreakEvent] = field(default_factory=list)
    reward_history: List[RewardDeliveryEvent] = field(default_factory=list)
    
    def add_beam_break(self, feeder_id: int, distance: float = 0.0, position: Optional[tuple] = None):
        """Add beam break event to history"""
        event = BeamBreakEvent(
            timestamp=time.time(),
            bat_id=self.bat_id,
            feeder_id=feeder_id,
            event_name="beam_break",
            distance_to_feeder=distance,
            bat_position=position
        )
        self.beam_break_history.append(event)
    
    def add_reward(self, feeder_id: int, manual: bool = False, duration_ms: int = 0, motor_speed: int = 0):
        """Add reward delivery event to history"""
        event = RewardDeliveryEvent(
            timestamp=time.time(),
            bat_id=self.bat_id,
            feeder_id=feeder_id,
            event_name="reward_delivery",
            manual=manual,
            duration_ms=duration_ms,
            motor_speed=motor_speed
        )
        self.reward_history.append(event)
    
    def get_last_beam_break_time(self) -> float:
        """Get timestamp of most recent beam break"""
        if not self.beam_break_history:
            return 0.0
        return self.beam_break_history[-1].timestamp
    
    def get_last_reward_time(self) -> float:
        """Get timestamp of most recent reward"""
        if not self.reward_history:
            return 0.0
        return self.reward_history[-1].timestamp
    
    def get_beam_breaks_for_feeder(self, feeder_id: int) -> List[BeamBreakEvent]:
        """Get all beam break events for specific feeder"""
        return [event for event in self.beam_break_history if event.feeder_id == feeder_id]
    
    def get_rewards_for_feeder(self, feeder_id: int) -> List[RewardDeliveryEvent]:
        """Get all reward events for specific feeder"""
        return [event for event in self.reward_history if event.feeder_id == feeder_id]


@dataclass
class SystemFeeder:
    """Enhanced feeder state with complete history tracking"""
    feeder_id: int
    name: str
    active: bool = True
    
    # Task logic state
    owner_bat_id: Optional[str] = None  # Which bat currently "owns" this feeder
    owner_since: Optional[float] = None  # When current ownership started
    
    # Physical properties
    position: tuple = (0.0, 0.0, 0.0)  # (x, y, z)
    activation_radius: float = 3.0  # meters - max distance for valid beam break and feeder ownership
    reactivation_distance: float = 2.0  # meters - min distance bat must fly to be eligible for rewards again
    
    # Motor configuration
    duration_ms: int = 500
    motor_speed: int = 255
    probability: float = 1.0  # Reward probability (0.0-1.0) for partial reinforcement
    
    # Event histories - tracks which bats triggered events
    beam_break_history: List[BeamBreakEvent] = field(default_factory=list)
    reward_delivery_history: List[RewardDeliveryEvent] = field(default_factory=list)
    
    def add_beam_break(self, bat_id: str, distance: float = 0.0, bat_position: Optional[tuple] = None):
        """Add beam break event to feeder history"""
        event = BeamBreakEvent(
            timestamp=time.time(),
            bat_id=bat_id,
            feeder_id=self.feeder_id,
            event_name="beam_break",
            distance_to_feeder=distance,
            bat_position=bat_position
        )
        self.beam_break_history.append(event)
    
    def add_reward_delivery(self, bat_id: str, manual: bool = False):
        """Add reward delivery event to feeder history"""
        event = RewardDeliveryEvent(
            timestamp=time.time(),
            bat_id=bat_id,
            feeder_id=self.feeder_id,
            event_name="reward_delivery",
            manual=manual,
            duration_ms=self.duration_ms,
            motor_speed=self.motor_speed
        )
        self.reward_delivery_history.append(event)
    
    def get_last_beam_break_time(self) -> float:
        """Get timestamp of most recent beam break"""
        if not self.beam_break_history:
            return 0.0
        return self.beam_break_history[-1].timestamp
    
    def get_last_reward_time(self) -> float:
        """Get timestamp of most recent reward delivery"""
        if not self.reward_delivery_history:
            return 0.0
        return self.reward_delivery_history[-1].timestamp
    
    def get_beam_breaks_by_bat(self, bat_id: str) -> List[BeamBreakEvent]:
        """Get all beam break events triggered by specific bat"""
        return [event for event in self.beam_break_history if event.bat_id == bat_id]
    
    def get_rewards_to_bat(self, bat_id: str) -> List[RewardDeliveryEvent]:
        """Get all reward deliveries to specific bat"""
        return [event for event in self.reward_delivery_history if event.bat_id == bat_id]


@dataclass
class SystemState:
    """Complete system state for task logic evaluation"""
    timestamp: float = field(default_factory=time.time)
    
    # Core components
    bats: Dict[str, SystemBat] = field(default_factory=dict)
    feeders: Dict[int, SystemFeeder] = field(default_factory=dict)
    
    # Session info
    session_start_time: float = 0.0
    session_id: str = ""
    
    def add_bat(self, bat_id: str, tag_id: str, active: bool = True) -> SystemBat:
        """Add or update bat in system state"""
        if bat_id not in self.bats:
            self.bats[bat_id] = SystemBat(bat_id=bat_id, tag_id=tag_id, active=active)
        else:
            self.bats[bat_id].tag_id = tag_id
            self.bats[bat_id].active = active
        return self.bats[bat_id]
    
    def add_feeder(self, feeder_id: int, name: str, position: tuple, active: bool = True, 
                   activation_radius: float = 3.0, reactivation_distance: float = 2.0, 
                   duration_ms: int = 500, motor_speed: int = 255, probability: float = 1.0) -> SystemFeeder:
        """Add or update feeder in system state"""
        if feeder_id not in self.feeders:
            self.feeders[feeder_id] = SystemFeeder(
                feeder_id=feeder_id,
                name=name,
                position=position,
                active=active,
                activation_radius=activation_radius,
                reactivation_distance=reactivation_distance,
                duration_ms=duration_ms,
                motor_speed=motor_speed,
                probability=probability
            )
        else:
            feeder = self.feeders[feeder_id]
            feeder.name = name
            feeder.position = position
            feeder.active = active
            feeder.activation_radius = activation_radius
            feeder.reactivation_distance = reactivation_distance
            feeder.duration_ms = duration_ms
            feeder.motor_speed = motor_speed
            feeder.probability = probability
        return self.feeders[feeder_id]
    
    def update_bat_position(self, bat_id: str, position: tuple, timestamp: float = None):
        """Update bat position and check for activation state changes"""
        if bat_id in self.bats:
            if timestamp is None:
                timestamp = time.time()
            self.bats[bat_id].last_position = (*position, timestamp)
            
            # Update activation state based on new position
            self._update_bat_activation_state(self.bats[bat_id], timestamp)
    
    def _update_bat_activation_state(self, bat: 'SystemBat', current_time: float):
        """Update bat activation state based on current position"""
        if bat.activation_state == "ACTIVE":
            return  # Already active
        
        
        # Check if bat can become active again
        if bat.last_reward_feeder_id is None or bat.last_reward_feeder_id not in self.feeders:
            bat.activation_state = "ACTIVE"
            return
        
        # Check if position is recent enough
        if not bat.last_position or len(bat.last_position) < 4:
            return  # No position data, stay INACTIVE
        
        pos_timestamp = bat.last_position[3]
        if current_time - pos_timestamp > 1.0:  # position_timeout
            return  # Position too old, stay INACTIVE
        
        # Calculate distance from last reward feeder
        bat_pos = bat.last_position[:3]
        last_reward_feeder = self.feeders[bat.last_reward_feeder_id]
        distance = self._calculate_3d_distance(bat_pos, last_reward_feeder.position)
        
        
        # Check if bat is far enough away
        if distance >= last_reward_feeder.reactivation_distance:
            # Bat is far enough - check timing requirement
            if bat.distance_threshold_met_time is None:
                # First time being far enough - record timestamp
                bat.distance_threshold_met_time = current_time
            elif current_time - bat.distance_threshold_met_time >= 0.2:  # reactivation_time
                # Been far enough for required time - reactivate!
                bat.activation_state = "ACTIVE"
                bat.distance_threshold_met_time = None
            else:
                time_remaining = 0.2 - (current_time - bat.distance_threshold_met_time)
        else:
            # Bat moved closer - reset timing
            bat.distance_threshold_met_time = None
    
    def _calculate_3d_distance(self, pos1: tuple, pos2: tuple) -> float:
        """Calculate 3D Euclidean distance between two positions"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        dz = pos1[2] - pos2[2]
        return (dx*dx + dy*dy + dz*dz)**0.5
    
    def record_beam_break(self, feeder_id: int, bat_id: str, distance: float = 0.0, 
                         bat_position: Optional[tuple] = None):
        """Record beam break event in both bat and feeder histories"""
        if bat_id in self.bats:
            self.bats[bat_id].add_beam_break(feeder_id, distance, bat_position)
        
        if feeder_id in self.feeders:
            self.feeders[feeder_id].add_beam_break(bat_id, distance, bat_position)
    
    def record_reward_delivery(self, feeder_id: int, bat_id: str, manual: bool = False):
        """Record reward delivery in both bat and feeder histories"""
        if bat_id in self.bats:
            duration_ms = self.feeders[feeder_id].duration_ms if feeder_id in self.feeders else 0
            motor_speed = self.feeders[feeder_id].motor_speed if feeder_id in self.feeders else 0
            self.bats[bat_id].add_reward(feeder_id, manual, duration_ms, motor_speed)
        
        if feeder_id in self.feeders:
            self.feeders[feeder_id].add_reward_delivery(bat_id, manual)
    
    def get_active_bats(self) -> Dict[str, SystemBat]:
        """Get all active bats"""
        return {bat_id: bat for bat_id, bat in self.bats.items() if bat.active}
    
    def get_active_feeders(self) -> Dict[int, SystemFeeder]:
        """Get all active feeders"""
        return {feeder_id: feeder for feeder_id, feeder in self.feeders.items() if feeder.active}
    
    def to_dict(self) -> dict:
        """Convert system state to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp,
            'session_start_time': self.session_start_time,
            'session_id': self.session_id,
            'bats': {
                bat_id: {
                    'bat_id': bat.bat_id,
                    'tag_id': bat.tag_id,
                    'active': bat.active,
                    'activation_state': bat.activation_state,
                    'last_reward_feeder_id': bat.last_reward_feeder_id,
                    'last_reward_time': bat.last_reward_time,
                    'distance_threshold_met_time': bat.distance_threshold_met_time,
                    'last_position': bat.last_position,
                    'beam_break_history': [
                        {
                            'timestamp': event.timestamp,
                            'feeder_id': event.feeder_id,
                            'distance_to_feeder': event.distance_to_feeder,
                            'bat_position': event.bat_position
                        } for event in bat.beam_break_history
                    ],
                    'reward_history': [
                        {
                            'timestamp': event.timestamp,
                            'feeder_id': event.feeder_id,
                            'manual': event.manual,
                            'duration_ms': event.duration_ms,
                            'motor_speed': event.motor_speed
                        } for event in bat.reward_history
                    ]
                } for bat_id, bat in self.bats.items()
            },
            'feeders': {
                feeder_id: {
                    'feeder_id': feeder.feeder_id,
                    'name': feeder.name,
                    'active': feeder.active,
                    'owner_bat_id': feeder.owner_bat_id,
                    'owner_since': feeder.owner_since,
                    'position': feeder.position,
                    'activation_radius': feeder.activation_radius,
                    'reactivation_distance': feeder.reactivation_distance,
                    'duration_ms': feeder.duration_ms,
                    'motor_speed': feeder.motor_speed,
                    'beam_break_history': [
                        {
                            'timestamp': event.timestamp,
                            'bat_id': event.bat_id,
                            'distance_to_feeder': event.distance_to_feeder,
                            'bat_position': event.bat_position
                        } for event in feeder.beam_break_history
                    ],
                    'reward_delivery_history': [
                        {
                            'timestamp': event.timestamp,
                            'bat_id': event.bat_id,
                            'manual': event.manual,
                            'duration_ms': event.duration_ms,
                            'motor_speed': event.motor_speed
                        } for event in feeder.reward_delivery_history
                    ]
                } for feeder_id, feeder in self.feeders.items()
            }
        }
