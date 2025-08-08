# Bat Feeder Control System

A Python-based automated feeder control system for bat research experiments. This system integrates position tracking (Cortex MoCap or Ciholas UWB), Arduino-controlled feeders, and real-time monitoring through a comprehensive GUI.

## Features

- **Multi-Modal Position Tracking**: Support for Cortex MoCap (120 Hz) and Ciholas UWB (100 Hz) systems
- **Arduino Integration**: Control up to 4 DC motor feeders with beam-break detection
- **Intelligent Feeder Logic**: Distance-based activation with independent per-bat state management
- **Comprehensive Logging**: Data logging, event logging, and TTL synchronization
- **Real-Time GUI**: Live monitoring, flight path visualization, and manual controls
- **Mock Mode**: Full functionality testing without hardware dependencies

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd batjuice
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Configure system settings in `config/default_config.json`

## Usage

### Running in Mock Mode (Recommended for Testing)

```bash
python main.py --mock
```

This mode simulates:
- 3 flying bats with realistic movement patterns
- 2 feeders with beam-break detection
- TTL pulse generation
- All logging and GUI functionality

### Running with Real Hardware

```bash
python main.py
```

Ensure your hardware is connected and configured in `config/default_config.json`.

## System Architecture

```
batjuice/
├── config/                 # Configuration management
├── position_tracking/      # Cortex, Ciholas, and mock trackers
├── hardware/              # Arduino communication
├── feeder_logic/          # Core feeder control algorithms
├── logging/               # Data and event logging
├── gui/                   # Tkinter-based GUI
├── utils/                 # Data structures and utilities
└── main.py               # Application entry point
```

## Configuration

### Feeder Settings
- **Duration**: Motor activation time (100-5000 ms)
- **Probability**: Reward delivery probability (0.0-1.0)
- **Activation Distance**: Minimum distance for feeder activation (10-200 cm)

### Position Tracking
- **Cortex**: Motion capture at 120 Hz
- **Ciholas**: UWB tracking at 100 Hz  
- **Mock**: Simulated flight data for testing

### Arduino Communication
- **Port**: Serial port (e.g., COM3 on Windows)
- **Baudrate**: 9600 (default)
- **Protocol**: Simple text commands for motor control and sensor reading

## GUI Components

### Control Tab
- **Feeder Panel**: Real-time status, configuration controls, manual reward buttons
- **Bat Panel**: Live bat tracking, flight counts, reward statistics

### Monitoring Tab
- **Session Information**: Session ID, tracking system status
- **System Statistics**: Aggregate performance metrics

### Flight Paths Tab
- **Real-Time Visualization**: 2D/3D flight path display with color-coded bats
- **Interactive Controls**: Bat selection, view modes, path clearing

## Data Logging

All data is automatically logged with synchronized timestamps:

- **positions_YYYYMMDD_HHMMSS.csv**: Position tracking data
- **rewards_YYYYMMDD_HHMMSS.csv**: Reward delivery events
- **beam_breaks_YYYYMMDD_HHMMSS.csv**: Beam-break detections
- **ttl_YYYYMMDD_HHMMSS.csv**: TTL synchronization pulses
- **config_YYYYMMDD_HHMMSS.json**: Configuration change history

## Arduino Protocol

### Commands Sent to Arduino
```
PING                    # Connection test
MOTOR:feeder_id:duration # Activate motor (feeder_id: 0-3, duration: ms)
```

### Messages Received from Arduino
```
PONG                    # Connection response
BEAM:feeder_id         # Beam break detection
TTL                    # TTL pulse received
ERROR:message          # Error reporting
```

## Feeder Logic

1. **Position Monitoring**: Continuous tracking of bat positions
2. **Distance Calculation**: 3D distance from bat to each feeder
3. **State Management**: Independent activation state per bat per feeder
4. **Activation Criteria**: Bat must move beyond activation distance
5. **Reward Delivery**: Based on beam-break detection and probability settings
6. **Deactivation**: Minimum activation time prevents rapid state changes

## Research Lab Considerations

- **Simple Architecture**: Easy to understand and modify
- **Minimal Dependencies**: Uses standard Python libraries
- **Robust Logging**: Comprehensive data collection for analysis
- **Real-Time Performance**: Optimized for 100+ Hz data rates
- **Hardware Agnostic**: Mock mode for development without hardware

## Troubleshooting

### Common Issues

1. **Position Tracking Connection Failed**
   - Check network connectivity to tracking system
   - Verify host/port settings in configuration
   - Test with mock mode first

2. **Arduino Communication Failed**
   - Verify COM port and cable connection
   - Check Arduino firmware and baudrate
   - Test with mock mode for software validation

3. **GUI Performance Issues**
   - Reduce `max_flight_points` in configuration
   - Lower `update_rate_ms` for slower updates
   - Use 2D instead of 3D flight visualization

### Log Files
Check log files in the `data/` directory for detailed error information and system events.

## Development

### Adding New Tracking Systems
1. Inherit from `BaseTracker` in `position_tracking/`
2. Implement `connect()`, `disconnect()`, and `_fetch_data()` methods
3. Add configuration support in `settings.py`

### Extending GUI
- Panels are modular and can be extended independently
- Use threading for non-blocking updates
- Follow the existing pattern for real-time data display

### Custom Feeder Logic
Modify `feeder_logic/feeder_manager.py` to implement custom activation criteria or reward algorithms.

## License

[Specify your license here]

## Contact

[Your contact information]