"""
Abstract base class for position tracking systems.
"""
from abc import ABC, abstractmethod
from typing import Optional, Callable
import threading
import queue
from utils.data_structures import Position


class BaseTracker(ABC):
    """Abstract base class for position tracking systems"""
    
    def __init__(self, callback: Optional[Callable[[Position], None]] = None):
        """
        Initialize tracker
        
        Args:
            callback: Function to call when new position data is received
        """
        self.callback = callback
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.position_queue = queue.Queue()
        
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the tracking system
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the tracking system"""
        pass
    
    @abstractmethod
    def _fetch_data(self):
        """Internal method to fetch data from tracking system"""
        pass
    
    def start_tracking(self):
        """Start the tracking thread"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
    
    def stop_tracking(self):
        """Stop the tracking thread"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
    
    def _tracking_loop(self):
        """Main tracking loop running in separate thread"""
        while self.running:
            try:
                self._fetch_data()
            except Exception as e:
                print(f"Error in tracking loop: {e}")
                continue
    
    def get_latest_positions(self) -> list[Position]:
        """
        Get all positions from the queue
        
        Returns:
            list[Position]: List of position updates
        """
        positions = []
        try:
            while True:
                positions.append(self.position_queue.get_nowait())
        except queue.Empty:
            pass
        return positions
    
    def _add_position(self, position: Position):
        """Add position to queue and call callback if provided"""
        self.position_queue.put(position)
        if self.callback:
            self.callback(position)