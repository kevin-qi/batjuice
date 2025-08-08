# Mock Testing Guide

The bat feeder software provides modular mocking capabilities to test different components in isolation or combination.

## Mock Flags

### `--mock-arduino`
**Purpose**: Mock Arduino hardware without requiring physical connection.

**Behavior**:
- Logs all serial communication that would have been sent to Arduino to `mock_arduino.txt`
- Shows TX (transmitted) and RX (received) messages with timestamps
- Simulates Arduino responses (motor start/stop confirmations)
- No beam break or TTL simulation (for clean testing)

**Use Case**: Test feeder logic, logging, and GUI without requiring Arduino hardware.

**Example**:
```bash
python main.py --mock-arduino
```

**Log File Format** (`mock_arduino.txt`):
```
=== Mock Arduino Communication Log ===
Started: 2025-01-05 14:30:25
Port: COM3 (MOCKED)
Baudrate: 9600

[14:30:25.123] SYSTEM: Mock Arduino connected
[14:30:25.124] SYSTEM: Started reading from Arduino
[14:30:30.456] TX: MOTOR:0:500
[14:30:30.457] RX: MOTOR_START:0:500
[14:30:30.957] RX: MOTOR_STOP:0
```

### `--mock-rtls`
**Purpose**: Mock RTLS (Real-Time Location System) position tracking without requiring Cortex/Ciholas hardware.

**Behavior**:
- Generates simulated bat flight data with realistic movement patterns
- Alternates between stationary (5-10s) and moving (2-4s) phases
- Respects room boundaries and feeder locations
- Triggers feeder activation based on distance logic

**Use Case**: Test position-based feeder activation, flight display, and logging without requiring motion capture or UWB systems.

**Example**:
```bash
python main.py --mock-rtls
```

### `--mock` (Full Mock Mode)
**Purpose**: Mock both Arduino and RTLS systems simultaneously.

**Behavior**: Combines both `--mock-arduino` and `--mock-rtls` behaviors.

**Use Case**: Complete software testing without any hardware dependencies.

**Example**:
```bash
python main.py --mock
```

## Testing Scenarios

### 1. Arduino Communication Testing
Test Arduino commands and logging without hardware:
```bash
python main.py --mock-arduino
```
- Start session in GUI
- Use "Manual Reward" buttons
- Check `mock_arduino.txt` for logged commands
- Verify events are logged to `events.csv`

### 2. Position Tracking Testing  
Test flight display and feeder activation logic:
```bash
python main.py --mock-rtls
```
- Start session in GUI
- Watch simulated bat movements in 3D display
- Observe feeder state changes based on bat distance
- Test beam break simulation and reward delivery

### 3. Integration Testing
Test complete system integration:
```bash
python main.py --mock
```
- All GUI panels functional
- Flight data drives feeder activation
- Manual rewards trigger Arduino commands
- All events logged properly

### 4. Real Hardware Testing
Test with specific hardware components:

**Arduino only** (with real RTLS):
```bash
python main.py --mock-rtls
```

**RTLS only** (with real Arduino):
```bash
python main.py --mock-arduino
```

**Both real** (production mode):
```bash
python main.py
```

## Debugging and Logs

### Mock Arduino Log (`mock_arduino.txt`)
- `TX`: Commands sent to Arduino
- `RX`: Responses from Arduino  
- `SYSTEM`: Connection/status messages
- Timestamps in HH:MM:SS.mmm format

### Events Log (`*_events.csv`)
Always generated regardless of mock mode:
- `beam_break`: Sensor activations
- `motor_start/motor_stop`: Motor control events
- `reward`: Reward delivery attempts
- `ttl`: External sync pulses
- `session_start/session_end`: Session boundaries

### System Log (`*_feeder_session.log`)
System-level events and errors for debugging.

## Benefits

1. **Modular Testing**: Test individual components without full hardware setup
2. **Development**: Write and debug code without lab access
3. **Debugging**: Isolate issues to specific subsystems
4. **Documentation**: Mock logs provide clear communication protocol examples
5. **Validation**: Verify software behavior before hardware deployment

## Notes

- Mock files are created in the current working directory
- Each session creates new timestamped log files
- Mock Arduino responds immediately (no serial delays)
- Mock RTLS generates deterministic but randomized flight patterns
- All business logic (feeder activation, logging, GUI) remains identical to real hardware mode