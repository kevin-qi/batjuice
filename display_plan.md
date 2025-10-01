# Flight Display Revamp: Development Plan

## Overview
Revamp flight visualization from real-time 3D to real-time 2D (main) + manual 3D snapshot (tab). **Critical requirement: Zero plotting delays on main thread to protect feeder control logic.**

---

## Current State Analysis

### `gui/flight_display_3d.py` (844 lines)
**Current Architecture:**
- Real-time 3D plotting with threading (`_update_loop`, `start_updates`, `stop_updates`)
- Called every 100ms from update thread
- Incremental Line3DCollection creation
- Bat selection, toggles (trigger/reactivation radius, labels), clear paths
- 10x downsampling (`display_subsample_rate=10`)
- Feeder position display (30cm squares + radius spheres)
- FPS counter

**Reusable Code:**
- UI controls: bat selection dropdown, toggles, clear button
- Data structures: `flight_data` (defaultdict with deques), `bat_colors`, `last_plotted_index`
- Feeder rendering: `_draw_feeders()`, `_draw_room_boundaries()`
- Plot initialization: `_setup_display()`, theme/styling
- Camera controls: `_reset_camera()`
- Selection change logic: `_on_selection_change()`
- FPS counter: `_draw_fps_counter()`

**To Remove:**
- Threading: `_update_loop()`, `update_thread`, `start_updates()`, `stop_updates()`
- Incremental update logic: `_update_plot()` automatic calling
- Real-time integration: `update_positions()` method

**To Add:**
- "Refresh" button
- `refresh()` method: snapshot plot on separate thread (non-blocking)

### `gui/main_window.py` (511 lines)
**Current Integration:**
- Line 11: `from .flight_display_3d import FlightDisplay3D`
- Line 291-292: Creates `FlightDisplay3D` in control tab's "Flight Paths" card
- Line 358: `self.flight_display.start_updates()` when system starts
- Line 370: `self.flight_display.stop_updates()` when system stops
- Line 417: `self.flight_display.update_positions(bat_states)` from `update_flight_display()`
- Line 295: Feeder position callback integration

**Current Layout:**
```
Control Tab
├── Session Controls (top)
├── PanedWindow (horizontal)
    ├── Left Paned (weight=3, vertical)
    │   ├── Feeders card (weight=3)
    │   └── Bats card (weight=2)
    └── Right: Flight Paths card (weight=7) ← FlightDisplay3D here
```

**To Change:**
- Replace `FlightDisplay3D` with `FlightDisplay2D` in "Flight Paths" card
- Add new tab "3D View" with manual `FlightDisplay3D`
- Both displays share `flight_data` via thread-safe lock
- Add `threading.Lock` for `flight_data` access

---

## Implementation Plan

### Phase 1: Create Shared Data Manager
**File:** `gui/flight_data_manager.py` (NEW)

**Purpose:** Thread-safe flight data storage shared between 2D/3D displays

**Implementation:**
```python
class FlightDataManager:
    def __init__(self, max_points=10000):
        self.max_points = max_points
        self.flight_data = defaultdict(lambda: {
            'x': deque(maxlen=max_points),
            'y': deque(maxlen=max_points),
            'z': deque(maxlen=max_points),
            'timestamps': deque(maxlen=max_points)
        })
        self.lock = threading.Lock()
        self._point_counters = {}
        self.display_subsample_rate = 10

    def add_position(self, bat_id, position):
        """Add position with 10x downsampling (thread-safe)"""
        if bat_id not in self._point_counters:
            self._point_counters[bat_id] = 0

        self._point_counters[bat_id] += 1

        # 10x downsampling
        if self._point_counters[bat_id] % self.display_subsample_rate == 0:
            with self.lock:
                self.flight_data[bat_id]['x'].append(position.x)
                self.flight_data[bat_id]['y'].append(position.y)
                self.flight_data[bat_id]['z'].append(position.z)
                self.flight_data[bat_id]['timestamps'].append(position.timestamp)

    def get_snapshot(self):
        """Get thread-safe snapshot copy of all data"""
        with self.lock:
            snapshot = {}
            for bat_id, data in self.flight_data.items():
                snapshot[bat_id] = {
                    'x': list(data['x']),
                    'y': list(data['y']),
                    'z': list(data['z']),
                    'timestamps': list(data['timestamps'])
                }
            return snapshot

    def clear(self):
        """Clear all data (thread-safe)"""
        with self.lock:
            self.flight_data.clear()
```

**Lines:** ~60

---

### Phase 2: Create FlightDisplay2D
**File:** `gui/flight_display_2d.py` (NEW)

**Recycle from FlightDisplay3D:**
- `__init__` structure (parent, configs)
- `_setup_display()` → modify for 2D axes
- `_create_card_panel()` pattern (if needed)
- Bat selection dropdown + trace callback
- Clear paths button + confirmation
- Toggles: trigger radius, reactivation radius, labels
- `bat_colors` list (same colors)
- `_draw_feeders()` → adapt for 2D (X-Y projection, no Z)
- `_draw_room_boundaries()` → adapt for 2D (floor outline only)
- `_on_selection_change()` logic
- `_toggle_display()` logic
- `_clear_paths()` integration with data manager
- FPS counter display

**New Implementation:**
```python
class FlightDisplay2D:
    def __init__(self, parent, gui_config, room_config, feeder_configs, data_manager):
        self.parent = parent
        self.gui_config = gui_config
        self.room_config = room_config
        self.feeder_configs = feeder_configs
        self.data_manager = data_manager  # Shared data manager

        # Reuse from 3D
        self.selected_bat = tk.StringVar(value="All")
        self.show_trigger_radius = tk.BooleanVar(value=True)
        self.show_reactivation_radius = tk.BooleanVar(value=False)
        self.show_labels = tk.BooleanVar(value=True)
        self.bat_colors = [...]  # Same as 3D

        # 2D-specific
        self.running = False
        self.update_thread = None
        self.bat_line_collections = defaultdict(list)  # 2D LineCollection
        self.last_plotted_index = {}
        self.frame_times = deque(maxlen=30)

        self._setup_display()

    def _setup_display(self):
        """Recycle control layout from 3D, change plot to 2D"""
        # Control frame (same as 3D)
        # Bat selection dropdown
        # Buttons: Clear Paths
        # Toggles: Labels, Trigger Radius, Reactivation Radius

        # 2D matplotlib figure (instead of 3D)
        self.fig, self.ax = plt.subplots(figsize=(7, 7))
        self.ax.set_aspect('equal')

        # Dark theme (recycle from 3D)
        self.fig.patch.set_facecolor('#2B2D31')
        self.ax.set_facecolor('#2B2D31')

        # Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, parent)
        toolbar.update()

        # Initialize static elements
        self._draw_static_elements()

    def _draw_static_elements(self):
        """Recycle logic, adapt for 2D"""
        # Set axes labels
        self.ax.set_xlabel('X (m)', color='#DCDDDE')
        self.ax.set_ylabel('Y (m)', color='#DCDDDE')

        # Set room bounds (X-Y only)
        bounds = self.room_config.get('bounds', {})
        x_min, x_max = bounds.get('x_min', -3), bounds.get('x_max', 3)
        y_min, y_max = bounds.get('y_min', -3), bounds.get('y_max', 3)
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)

        # Room boundary (2D floor outline)
        self.ax.plot([x_min, x_max, x_max, x_min, x_min],
                     [y_min, y_min, y_max, y_max, y_min],
                     color='#6B7280', alpha=0.5, linewidth=1.5)

        # Draw feeders (2D squares, X-Y projection)
        self._draw_feeders_2d()

    def _draw_feeders_2d(self):
        """Adapt from 3D, use X-Y position only"""
        from matplotlib.patches import Rectangle, Circle

        for feeder in self.feeder_configs:
            x, y, z = feeder.get_current_position()
            size = 0.15  # 30cm square, half-size

            # Square
            rect = Rectangle((x-size, y-size), 2*size, 2*size,
                           facecolor='#CC7000', edgecolor='#D97E00',
                           alpha=0.6, linewidth=1.0)
            self.ax.add_patch(rect)

            # Label
            if self.show_labels.get():
                self.ax.text(x, y, f'F{feeder.feeder_id}',
                           ha='center', va='center', color='white', fontsize=8)

            # Trigger radius circle
            if self.show_trigger_radius.get():
                circle = Circle((x, y), feeder.activation_radius,
                              facecolor='none', edgecolor='#708090',
                              alpha=0.3, linewidth=1.5)
                self.ax.add_patch(circle)

            # Reactivation radius circle
            if self.show_reactivation_radius.get():
                circle = Circle((x, y), feeder.reactivation_distance,
                              facecolor='none', edgecolor='#708090',
                              alpha=0.3, linewidth=1.5, linestyle='--')
                self.ax.add_patch(circle)

    def start_updates(self):
        """Start update thread"""
        if self.running:
            return
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def stop_updates(self):
        """Stop update thread"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)

    def _update_loop(self):
        """Update loop at 10Hz"""
        while self.running:
            try:
                if self.parent.winfo_exists():
                    self.parent.after_idle(self._update_plot)
                time.sleep(0.1)  # 10 Hz
            except Exception as e:
                print(f"2D display error: {e}")
                traceback.print_exc()
                time.sleep(0.1)

    def _update_plot(self):
        """Incremental plot update with blitting"""
        try:
            # Get snapshot from data manager (thread-safe)
            flight_data = self.data_manager.get_snapshot()

            # Clear dynamic elements
            # Plot bat paths (incremental LineCollection)
            # Apply bat selection colors
            # Draw current position markers
            # FPS counter

            # Use blitting for performance
            self.canvas.draw_idle()
        except Exception as e:
            print(f"2D plot error: {e}")

    def _plot_bat_path_2d(self, data, bat_id, color):
        """Incremental 2D path plotting with LineCollection"""
        # Similar to 3D's _plot_bat_path_3d but using 2D LineCollection
        # Reuse incremental logic with last_plotted_index
        pass

    # Recycle methods:
    # - _on_selection_change()
    # - _toggle_display()
    # - _clear_paths() → calls data_manager.clear()
    # - _draw_fps_counter()
```

**Lines:** ~500-600 (recycling ~60% from FlightDisplay3D)

---

### Phase 3: Modify FlightDisplay3D for Manual Refresh
**File:** `gui/flight_display_3d.py`

**Changes:**

1. **Remove threading (lines 330-353)**
   - Delete `_update_loop()` method
   - Delete `start_updates()` method (lines 323-329)
   - Delete `stop_updates()` method (lines 332-337)
   - Delete `self.update_thread` attribute (line 44)
   - Delete `self.running` attribute (line 43)

2. **Remove real-time integration (lines 292-321)**
   - Delete `update_positions()` method entirely
   - Delete `self._point_counters` (no longer receiving live data)

3. **Modify `__init__` (lines 20-88)**
   ```python
   def __init__(self, parent, gui_config, room_config, feeder_configs, data_manager):
       # ... existing attributes ...
       self.data_manager = data_manager  # NEW: shared data

       # REMOVE these:
       # - self.running = False
       # - self.update_thread = None
       # - self.flight_data = defaultdict(...)  # Use data_manager instead

       # KEEP these:
       # - Display control variables
       # - Colors
       # - Static element tracking
       # - Incremental plotting variables

       self._setup_display()
   ```

4. **Add Refresh Button (in `_setup_display`, around line 110)**
   ```python
   # After clear_btn
   refresh_btn = ttk.Button(control_frame, text="Refresh 3D",
                           command=self._on_refresh_clicked)
   refresh_btn.pack(side=tk.LEFT, padx=(5, 10))
   ```

5. **Add `_on_refresh_clicked()` method (NEW, ~line 350)**
   ```python
   def _on_refresh_clicked(self):
       """Refresh 3D plot with latest data (on separate thread)"""
       def refresh_worker():
           try:
               # Get snapshot from data manager
               snapshot = self.data_manager.get_snapshot()

               # Schedule plot update on main thread
               self.parent.after_idle(lambda: self._refresh_plot(snapshot))
           except Exception as e:
               print(f"3D refresh error: {e}")
               traceback.print_exc()

       # Run on separate thread (non-blocking)
       refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
       refresh_thread.start()
   ```

6. **Add `_refresh_plot(snapshot)` method (NEW, ~line 370)**
   ```python
   def _refresh_plot(self, snapshot):
       """Update 3D plot with snapshot data (called on main thread)"""
       try:
           # Clear existing trajectories
           for bat_id, collections in self.bat_trail_collections.items():
               for collection in collections:
                   try:
                       collection.remove()
                   except:
                       pass
           self.bat_trail_collections.clear()
           self.last_plotted_index.clear()

           # Trigger full replot
           self.needs_full_redraw = True

           # Temporarily store snapshot as flight_data
           self.flight_data_snapshot = snapshot

           # Call existing _update_plot logic
           self._update_plot_with_snapshot(snapshot)

       except Exception as e:
           print(f"3D plot refresh error: {e}")
           traceback.print_exc()
   ```

7. **Modify `_update_plot()` to work with snapshot (lines 355-468)**
   - Keep existing logic
   - Change data source from `self.flight_data` to snapshot parameter
   - Remove automatic calling (only called from refresh)

8. **Update `_clear_paths()` (lines 794-812)**
   ```python
   def _clear_paths(self):
       """Clear all flight paths"""
       # Clear data manager (shared data)
       self.data_manager.clear()

       # Clear local collections
       for bat_id, collections in self.bat_trail_collections.items():
           for collection in collections:
               try:
                   collection.remove()
               except:
                   pass
       self.bat_trail_collections.clear()
       self.last_plotted_index.clear()

       # Force redraw
       self.static_elements_drawn = False
       self.needs_full_redraw = True
       self.canvas.draw()
   ```

**Lines Changed:** ~150
**Lines Removed:** ~100
**Lines Added:** ~80

---

### Phase 4: Update MainWindow Integration
**File:** `gui/main_window.py`

**Changes:**

1. **Add imports (line 11)**
   ```python
   from .flight_display_3d import FlightDisplay3D
   from .flight_display_2d import FlightDisplay2D  # NEW
   from .flight_data_manager import FlightDataManager  # NEW
   ```

2. **Add data manager to `__init__` (after line 37)**
   ```python
   # Create shared flight data manager
   self.flight_data_manager = FlightDataManager(max_points=10000)
   ```

3. **Modify `_setup_gui()` to add 3D tab (lines 225-246)**
   ```python
   def _setup_gui(self):
       """Setup the GUI layout"""
       main_frame = ttk.Frame(self.root)
       main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

       # Create notebook for tabs
       notebook = ttk.Notebook(main_frame)
       notebook.pack(fill=tk.BOTH, expand=True)

       # Control tab (existing)
       control_frame = ttk.Frame(notebook)
       notebook.add(control_frame, text="Control")
       self._setup_control_tab(control_frame)

       # NEW: 3D View tab
       view_3d_frame = ttk.Frame(notebook)
       notebook.add(view_3d_frame, text="3D View")
       self._setup_3d_view_tab(view_3d_frame)

       # Configuration tab (existing)
       config_frame = ttk.Frame(notebook)
       notebook.add(config_frame, text="Configuration")
       self._setup_comprehensive_config_tab(config_frame)

       # Status bar
       self._setup_status_bar(main_frame)
   ```

4. **Modify `_setup_control_tab()` (lines 248-295)**
   ```python
   def _setup_control_tab(self, parent):
       """Setup the control tab"""
       # ... existing session controls ...
       # ... existing paned windows for feeders/bats ...

       # Right section - Flight Paths card
       flight_container, flight_content = self._create_card_panel(main_paned, "Flight Paths (2D)")
       main_paned.add(flight_container, weight=7)

       # CHANGE: Create 2D flight display instead of 3D
       room_config = self.settings.config.get('room', {})
       feeder_configs = self.settings.get_feeder_configs()
       self.flight_display_2d = FlightDisplay2D(
           flight_content,
           self.settings.get_gui_config(),
           room_config,
           feeder_configs,
           self.flight_data_manager  # NEW: shared data
       )

       # Keep feeder position callback
       self.feeder_controller.set_position_change_callback(self._on_feeder_position_changed)
   ```

5. **Add `_setup_3d_view_tab()` (NEW, after line 295)**
   ```python
   def _setup_3d_view_tab(self, parent):
       """Setup the 3D view tab with manual refresh"""
       # Create card panel for 3D view
       view_container, view_content = self._create_card_panel(parent, "3D View (Manual Refresh)")
       view_container.pack(fill=tk.BOTH, expand=True)

       # Create 3D flight display (manual refresh mode)
       room_config = self.settings.config.get('room', {})
       feeder_configs = self.settings.get_feeder_configs()
       self.flight_display_3d = FlightDisplay3D(
           view_content,
           self.settings.get_gui_config(),
           room_config,
           feeder_configs,
           self.flight_data_manager  # NEW: shared data
       )
   ```

6. **Update `start_gui_updates()` (lines 352-359)**
   ```python
   def start_gui_updates(self):
       """Start the GUI update thread"""
       # ... existing setup ...

       if self.system_started:
           self.feeder_panel.start_updates()
           self.bat_panel.start_updates()
           self.flight_display_2d.start_updates()  # CHANGE: 2D only
           # NOTE: 3D is manual refresh, no start_updates()
   ```

7. **Update `stop_gui_updates()` (lines 360-374)**
   ```python
   def stop_gui_updates(self):
       """Stop the GUI update thread"""
       self.running = False

       # Stop component updates
       if hasattr(self, 'feeder_panel'):
           self.feeder_panel.stop_updates()
       if hasattr(self, 'bat_panel'):
           self.bat_panel.stop_updates()
       if hasattr(self, 'flight_display_2d'):  # CHANGE
           self.flight_display_2d.stop_updates()
       # NOTE: 3D has no stop_updates()

       if self.update_thread and self.update_thread.is_alive():
           self.update_thread.join(timeout=1.0)
   ```

8. **Update `update_flight_display()` (lines 414-417)**
   ```python
   def update_flight_display(self, bat_states: Dict):
       """Update flight display with new data"""
       if self.system_started:
           # Add to shared data manager (thread-safe)
           for bat_id, bat_state in bat_states.items():
               if bat_state.last_position:
                   self.flight_data_manager.add_position(bat_id, bat_state.last_position)
           # NOTE: 2D display auto-updates via its thread
           # NOTE: 3D display updates on manual refresh
   ```

9. **Update `_on_feeder_position_changed()` callback**
   ```python
   def _on_feeder_position_changed(self, feeder_configs):
       """Callback when feeder positions change"""
       # Update both displays
       if hasattr(self, 'flight_display_2d'):
           self.flight_display_2d.update_feeder_positions(feeder_configs)
       if hasattr(self, 'flight_display_3d'):
           self.flight_display_3d.update_feeder_positions(feeder_configs)
   ```

**Lines Changed:** ~80
**Lines Added:** ~40

---

## Threading Architecture Summary

### Main Thread (GUI + Feeder Control)
- **NEVER BLOCKS** - Critical requirement
- Tkinter event loop
- Feeder control logic
- Session controls
- Feeder/bat panel updates

### 2D Display Thread (Continuous)
- Runs at 10 Hz
- Reads from `flight_data_manager` (thread-safe snapshot)
- Plots incrementally with blitting
- Calls `parent.after_idle(_update_plot)` for thread-safe GUI updates

### 3D Refresh Thread (On-Demand)
- Spawned when "Refresh 3D" clicked
- Gets snapshot from `flight_data_manager`
- Calls `parent.after_idle(_refresh_plot)` for thread-safe GUI updates
- Thread dies after refresh completes

### Data Flow
```
RTLS Position Stream (100 Hz)
    ↓
main_window.update_flight_display(bat_states)
    ↓
flight_data_manager.add_position() [with 10x downsampling]
    ↓ (thread-safe lock)
flight_data_manager.flight_data (10 Hz data)
    ↓
    ├─→ 2D Display (auto-reads via thread)
    └─→ 3D Display (manual snapshot on refresh)
```

---

## File Change Summary

### New Files
1. **`gui/flight_data_manager.py`** - 60 lines
   - Thread-safe data storage
   - 10x downsampling logic
   - Snapshot copy method

2. **`gui/flight_display_2d.py`** - 500-600 lines
   - Real-time 2D plotting
   - Recycles 60% from FlightDisplay3D
   - FuncAnimation + blitting
   - All existing UI controls

### Modified Files
1. **`gui/flight_display_3d.py`** - 844 lines → ~750 lines
   - Remove: Threading, real-time updates (~100 lines)
   - Add: Refresh button, snapshot methods (~80 lines)
   - Modify: Constructor, data source (~50 lines)

2. **`gui/main_window.py`** - 511 lines → ~550 lines
   - Add: Data manager initialization
   - Add: 3D view tab setup
   - Modify: Control tab (3D → 2D)
   - Modify: Update methods to use data manager
   - Lines changed: ~120

### Deprecated Code Removal
- `gui/flight_display_3d.py`:
  - `_update_loop()` (lines 338-353)
  - `start_updates()` (lines 323-329)
  - `stop_updates()` (lines 332-337)
  - `update_positions()` (lines 292-321)
  - Direct `flight_data` management (replaced by data_manager)

---

## Testing Plan

### Phase 1: Data Manager
1. Create `flight_data_manager.py`
2. Unit test: Thread safety with concurrent add/read
3. Unit test: 10x downsampling correctness

### Phase 2: 2D Display
1. Create `flight_display_2d.py` skeleton
2. Test: Static elements (feeders, room, controls)
3. Test: Bat selection dropdown
4. Test: Incremental 2D line plotting
5. Test: Blitting performance with 100K points

### Phase 3: 3D Modification
1. Modify `flight_display_3d.py` constructor
2. Remove threading code
3. Add refresh button
4. Test: Manual refresh with snapshot data
5. Test: Refresh thread doesn't block main thread

### Phase 4: Integration
1. Modify `main_window.py` imports
2. Add data manager
3. Replace 3D with 2D in control tab
4. Add 3D view tab
5. Test: Both displays working independently
6. Test: Clear paths affects both displays
7. Test: Feeder position updates affect both displays

### Phase 5: Performance Validation
1. Test: Feeder control logic never blocks (measure latency)
2. Test: 2D display FPS with 100K points
3. Test: 3D refresh can take 1s without affecting feeder control
4. Test: Memory usage with long recordings

---

## Risk Mitigation

### Risk 1: Main Thread Blocking
**Mitigation:** All plotting on separate threads with `parent.after_idle()` for GUI updates

### Risk 2: Data Race Conditions
**Mitigation:** `threading.Lock` on all `flight_data` access

### Risk 3: 2D Blitting Not Working
**Mitigation:** Fallback to `draw_idle()` if blitting fails, still better than 3D

### Risk 4: Memory Leaks with Long Recordings
**Mitigation:** `deque(maxlen=10000)` limits memory, already tested in 3D version

### Risk 5: Breaking Existing Feeder Control
**Mitigation:** Minimal changes to `main_window.py` update logic, keep existing callback structure

---

## Timeline Estimate

- **Phase 1 (Data Manager):** 1-2 hours
- **Phase 2 (2D Display):** 6-8 hours (recycling speeds up)
- **Phase 3 (3D Modification):** 2-3 hours
- **Phase 4 (Integration):** 2-3 hours
- **Phase 5 (Testing):** 3-4 hours

**Total:** 14-20 hours

---

## Success Criteria

1. ✅ Feeder control logic has ZERO plotting delays (measured with timing)
2. ✅ 2D display updates in real-time at 10 Hz
3. ✅ 2D display maintains 30+ FPS with 100K points
4. ✅ 3D refresh button works without blocking main thread
5. ✅ Both displays share same data via thread-safe manager
6. ✅ Bat selection, toggles, clear paths work in both displays
7. ✅ Feeder position updates reflected in both displays
8. ✅ Session start/stop works correctly
9. ✅ No memory leaks with long recordings
10. ✅ All existing features preserved
