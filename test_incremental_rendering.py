#!/usr/bin/env python3
"""
Test script for incremental rendering performance
Simulates bat position updates to measure rendering performance
"""
import time
import numpy as np
from dataclasses import dataclass
from typing import Dict


@dataclass
class Position:
    """Position data structure"""
    x: float
    y: float
    z: float
    timestamp: float


@dataclass
class BatState:
    """Simple bat state for testing"""
    bat_id: str
    last_position: Position


def generate_flight_trajectory(bat_id: str, n_points: int) -> list:
    """Generate a realistic 3D flight trajectory"""
    positions = []
    t = 0
    dt = 0.01  # 100 Hz

    # Start position
    x, y, z = 0.0, 0.0, 1.5

    # Velocity
    vx, vy, vz = 1.0, 0.5, 0.2

    for i in range(n_points):
        # Add some sinusoidal movement for realism
        x += vx * dt + 0.1 * np.sin(t * 2)
        y += vy * dt + 0.1 * np.cos(t * 3)
        z += vz * dt + 0.05 * np.sin(t * 5)

        # Keep within room bounds
        x = np.clip(x, -2.5, 2.5)
        y = np.clip(y, -2.5, 2.5)
        z = np.clip(z, 0.5, 2.5)

        # Change direction occasionally
        if i % 100 == 0:
            vx = np.random.uniform(-1.5, 1.5)
            vy = np.random.uniform(-1.5, 1.5)
            vz = np.random.uniform(-0.5, 0.5)

        positions.append(Position(x, y, z, t))
        t += dt

    return positions


def simulate_realtime_updates(flight_display, bat_id: str, positions: list,
                              batch_size: int = 10):
    """Simulate real-time position updates"""
    print(f"\nSimulating real-time updates for {bat_id}")
    print(f"Total points: {len(positions)}")
    print(f"Batch size: {batch_size} points per update")

    frame_times = []

    for i in range(0, len(positions), batch_size):
        batch = positions[i:i+batch_size]

        # Create bat states dictionary
        bat_states = {
            bat_id: BatState(bat_id=bat_id, last_position=batch[-1])
        }

        # Measure update time
        start = time.time()
        flight_display.update_positions(bat_states)

        # Force a plot update (normally done by background thread)
        flight_display._update_plot()

        # Process GUI events
        flight_display.parent.update()

        elapsed = time.time() - start
        frame_times.append(elapsed)

        # Print progress every 100 batches
        if (i // batch_size) % 100 == 0:
            avg_fps = 1.0 / np.mean(frame_times[-100:]) if len(frame_times) >= 100 else 1.0 / np.mean(frame_times)
            total_points = i + batch_size
            print(f"  {total_points:6d} points | Avg FPS: {avg_fps:6.2f} | "
                  f"Avg frame time: {np.mean(frame_times[-100:]) * 1000:.2f}ms")

    # Final statistics
    print(f"\n=== Performance Summary ===")
    print(f"Total points rendered: {len(positions)}")
    print(f"Total frames: {len(frame_times)}")
    print(f"Average FPS: {1.0 / np.mean(frame_times):.2f}")
    print(f"Min frame time: {min(frame_times) * 1000:.2f}ms")
    print(f"Max frame time: {max(frame_times) * 1000:.2f}ms")
    print(f"Median frame time: {np.median(frame_times) * 1000:.2f}ms")


def main():
    """Main test function"""
    import tkinter as tk
    from gui.flight_display_3d import FlightDisplay3D
    from config.feeder_config import FeederConfig

    print("=" * 60)
    print("Incremental Rendering Performance Test")
    print("=" * 60)

    # Create GUI
    root = tk.Tk()
    root.title("Performance Test - Incremental Rendering")
    root.geometry("900x800")

    # Test configuration
    gui_config = {
        'default_camera_elevation': 30,
        'default_camera_azimuth': 225,
        'refresh_rate_hz': 10
    }

    room_config = {
        'bounds': {
            'x_min': -3, 'x_max': 3,
            'y_min': -3, 'y_max': 3,
            'z_min': 0, 'z_max': 3
        }
    }

    # Create mock feeder
    feeder_config = FeederConfig(
        feeder_id=1,
        x=1.0, y=1.0, z=1.0,
        activation_radius=0.5,
        reactivation_distance=1.0
    )

    # Create display
    display_frame = ttk.Frame(root)
    display_frame.pack(fill=tk.BOTH, expand=True)

    flight_display = FlightDisplay3D(
        display_frame,
        gui_config,
        room_config,
        [feeder_config]
    )

    # Start display updates
    flight_display.start_updates()

    # Generate test trajectories
    print("\nGenerating test trajectories...")
    test_cases = [
        ("Bat_001", 1000, "1K points"),
        ("Bat_002", 5000, "5K points"),
        ("Bat_003", 10000, "10K points"),
    ]

    for bat_id, n_points, label in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Test Case: {label}")
        print(f"{'=' * 60}")

        positions = generate_flight_trajectory(bat_id, n_points)
        simulate_realtime_updates(flight_display, bat_id, positions, batch_size=10)

        # Pause between tests
        print(f"\nWaiting 2 seconds before next test...")
        time.sleep(2)

    print(f"\n{'=' * 60}")
    print("All tests complete!")
    print(f"{'=' * 60}")
    print("\nThe display now shows all trajectories.")
    print("You can interact with the 3D plot:")
    print("  - Rotate: Click and drag")
    print("  - Zoom: Mouse wheel")
    print("  - Pan: Right-click and drag")
    print("\nClose the window to exit.")

    # Keep window open
    root.mainloop()

    # Cleanup
    flight_display.stop_updates()


if __name__ == "__main__":
    from tkinter import ttk
    main()
