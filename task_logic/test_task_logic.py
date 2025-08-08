"""
Test script for the modular task logic system.

This script demonstrates how to use the task logic system and test
different configurations.
"""
import time
from system_state import SystemState
from task_logic import should_deliver_reward, update_task_parameters


def test_basic_functionality():
    """Test basic task logic functionality"""
    print("=== Testing Basic Task Logic Functionality ===")
    
    # Create system state
    system_state = SystemState()
    
    # Add a bat
    bat = system_state.add_bat("bat_001", "ciholas_123", active=True)
    bat_position = (1.0, 2.0, 1.5, time.time())
    system_state.update_bat_position("bat_001", bat_position[:3], bat_position[3])
    
    # Add a feeder
    feeder = system_state.add_feeder(
        feeder_id=1,
        name="Feeder_1", 
        position=(1.1, 2.1, 1.5),
        activation_distance=50.0
    )
    
    # Test reward decision
    should_deliver, reason = should_deliver_reward(system_state, 1, "bat_001")
    print(f"First reward decision: {should_deliver} - {reason}")
    
    # Record the reward
    if should_deliver:
        system_state.record_reward_delivery(1, "bat_001")
    
    # Try again immediately (should be denied due to time constraint)
    should_deliver, reason = should_deliver_reward(system_state, 1, "bat_001")
    print(f"Immediate second attempt: {should_deliver} - {reason}")
    
    # Wait and try again
    time.sleep(0.6)  # Wait longer than min_time_between_rewards
    should_deliver, reason = should_deliver_reward(system_state, 1, "bat_001")
    print(f"After waiting: {should_deliver} - {reason}")


def test_collision_detection():
    """Test collision detection functionality"""
    print("\n=== Testing Collision Detection ===")
    
    # Create system state
    system_state = SystemState()
    
    # Add two bats near the same feeder
    system_state.add_bat("bat_001", "ciholas_123", active=True)
    system_state.add_bat("bat_002", "ciholas_456", active=True)
    
    # Position both bats near feeder
    current_time = time.time()
    system_state.update_bat_position("bat_001", (1.0, 2.0, 1.5), current_time)
    system_state.update_bat_position("bat_002", (1.1, 2.1, 1.5), current_time)  # Very close
    
    # Add feeder
    system_state.add_feeder(1, "Feeder_1", (1.05, 2.05, 1.5))
    
    # Test reward decision (should be denied due to collision)
    should_deliver, reason = should_deliver_reward(system_state, 1, "bat_001")
    print(f"With two bats near feeder: {should_deliver} - {reason}")
    
    # Move second bat away
    system_state.update_bat_position("bat_002", (5.0, 5.0, 1.5), current_time)
    
    # Test again (should be allowed now)
    should_deliver, reason = should_deliver_reward(system_state, 1, "bat_001")
    print(f"After moving second bat away: {should_deliver} - {reason}")


def test_distance_constraints():
    """Test distance constraint functionality"""
    print("\n=== Testing Distance Constraints ===")
    
    # Create system state
    system_state = SystemState()
    
    # Add bat and two feeders
    system_state.add_bat("bat_001", "ciholas_123", active=True)
    system_state.add_feeder(1, "Feeder_1", (1.0, 2.0, 1.5))
    system_state.add_feeder(2, "Feeder_2", (1.2, 2.2, 1.5))  # Close to feeder 1
    
    # Update bat position
    current_time = time.time()
    system_state.update_bat_position("bat_001", (1.0, 2.0, 1.5), current_time)
    
    # Record beam break and reward at feeder 1
    system_state.record_beam_break(1, "bat_001", 0.05, (1.0, 2.0, 1.5))
    system_state.record_reward_delivery(1, "bat_001")
    
    # Wait to satisfy time constraint
    time.sleep(0.6)
    
    # Try feeder 2 (should be denied due to distance constraint)
    should_deliver, reason = should_deliver_reward(system_state, 2, "bat_001")
    print(f"Close feeder after reward: {should_deliver} - {reason}")
    
    # Add distant feeder
    system_state.add_feeder(3, "Feeder_3", (5.0, 5.0, 1.5))  # Far from feeder 1
    system_state.update_bat_position("bat_001", (5.0, 5.0, 1.5), time.time())
    
    # Try distant feeder (should be allowed)
    should_deliver, reason = should_deliver_reward(system_state, 3, "bat_001")
    print(f"Distant feeder after reward: {should_deliver} - {reason}")


def test_parameter_updates():
    """Test parameter update functionality"""
    print("\n=== Testing Parameter Updates ===")
    
    # Get current parameters
    from task_logic import get_task_parameters
    original_params = get_task_parameters()
    print(f"Original parameters: {original_params}")
    
    # Update parameters
    update_task_parameters(
        min_time_between_rewards=2.0,
        reward_probability=0.5,
        enable_collision_detection=False
    )
    
    new_params = get_task_parameters()
    print(f"Updated parameters: {new_params}")
    
    # Restore original parameters
    update_task_parameters(**original_params)
    restored_params = get_task_parameters()
    print(f"Restored parameters: {restored_params}")


def test_history_tracking():
    """Test event history tracking"""
    print("\n=== Testing History Tracking ===")
    
    # Create system state
    system_state = SystemState()
    
    # Add bat and feeder
    system_state.add_bat("bat_001", "ciholas_123")
    system_state.add_feeder(1, "Feeder_1", (1.0, 2.0, 1.5))
    
    # Record multiple events
    for i in range(3):
        system_state.record_beam_break(1, "bat_001", 0.1, (1.0, 2.0, 1.5))
        if i % 2 == 0:  # Every other beam break gets a reward
            system_state.record_reward_delivery(1, "bat_001")
        time.sleep(0.1)
    
    # Check history
    bat = system_state.bats["bat_001"]
    feeder = system_state.feeders[1]
    
    print(f"Bat beam break history: {len(bat.beam_break_history)} events")
    print(f"Bat reward history: {len(bat.reward_history)} events")
    print(f"Feeder beam break history: {len(feeder.beam_break_history)} events")
    print(f"Feeder reward history: {len(feeder.reward_delivery_history)} events")
    
    # Check recent events
    if bat.beam_break_history:
        last_break = bat.beam_break_history[-1]
        print(f"Last beam break: {last_break.event_name} at {last_break.timestamp}")
    
    if bat.reward_history:
        last_reward = bat.reward_history[-1] 
        print(f"Last reward: {last_reward.event_name} at {last_reward.timestamp}")


if __name__ == "__main__":
    print("Task Logic System Test Suite")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        test_collision_detection()
        test_distance_constraints()
        test_parameter_updates()
        test_history_tracking()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
