"""
Camera Capture Module for Center Stage Camera.

Provides threaded camera capture with configurable resolution and FPS,
multi-camera enumeration, and frame buffering for smooth playback.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal


class CameraState(Enum):
    """Camera connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class CameraInfo:
    """Information about an available camera."""
    index: int
    name: str
    resolution: tuple[int, int]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.resolution[0]}x{self.resolution[1]})"


class CameraCapture(QObject):
    """
    Threaded camera capture with Qt signal support.
    
    Signals:
        frame_ready: Emitted when a new frame is available (numpy array)
        state_changed: Emitted when camera state changes
        fps_updated: Emitted with current FPS value
    """
    
    frame_ready = Signal(np.ndarray)
    state_changed = Signal(CameraState)
    fps_updated = Signal(float)
    
    # Common resolutions to try
    RESOLUTIONS = [
        (1920, 1080),  # Full HD
        (1280, 720),   # HD
        (640, 480),    # VGA
    ]
    
    def __init__(
        self,
        camera_index: int = 0,
        target_fps: int = 30,
        resolution: tuple[int, int] = (1280, 720),
    ):
        super().__init__()
        self._camera_index = camera_index
        self._target_fps = target_fps
        self._resolution = resolution
        
        self._capture: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._state = CameraState.DISCONNECTED
        
        # Frame timing
        self._frame_interval = 1.0 / target_fps
        self._last_frame_time = 0.0
        self._fps_samples: list[float] = []
        
        # Current frame (thread-safe access)
        self._current_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
    
    @staticmethod
    def enumerate_cameras(max_cameras: int = 10) -> list[CameraInfo]:
        """
        Enumerate available cameras on the system.
        
        Args:
            max_cameras: Maximum number of cameras to check
            
        Returns:
            List of CameraInfo for available cameras
        """
        cameras = []
        
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                # Get camera properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                cameras.append(CameraInfo(
                    index=i,
                    name=f"Camera {i}",
                    resolution=(width, height)
                ))
                cap.release()
            else:
                # Stop at first unavailable index
                break
        
        return cameras
    
    @property
    def state(self) -> CameraState:
        """Current camera state."""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """Whether capture is currently running."""
        return self._running
    
    @property
    def resolution(self) -> tuple[int, int]:
        """Current capture resolution."""
        return self._resolution
    
    @property
    def current_frame(self) -> Optional[np.ndarray]:
        """Get the most recent frame (thread-safe)."""
        with self._frame_lock:
            return self._current_frame.copy() if self._current_frame is not None else None
    
    def _set_state(self, state: CameraState) -> None:
        """Update state and emit signal."""
        if self._state != state:
            self._state = state
            self.state_changed.emit(state)
    
    def start(self) -> bool:
        """
        Start camera capture in a background thread.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self._running:
            return True
        
        self._set_state(CameraState.CONNECTING)
        
        # Open camera with DirectShow backend (Windows)
        self._capture = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        
        if not self._capture.isOpened():
            self._set_state(CameraState.ERROR)
            return False
        
        # Set resolution
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])
        
        # Set FPS
        self._capture.set(cv2.CAP_PROP_FPS, self._target_fps)
        
        # Get actual resolution (may differ from requested)
        actual_width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._resolution = (actual_width, actual_height)
        
        # Start capture thread
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        
        self._set_state(CameraState.CONNECTED)
        return True
    
    def stop(self) -> None:
        """Stop camera capture and release resources."""
        self._running = False
        
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        
        self._set_state(CameraState.DISCONNECTED)
    
    def _capture_loop(self) -> None:
        """Main capture loop running in background thread."""
        while self._running and self._capture is not None:
            loop_start = time.perf_counter()
            
            ret, frame = self._capture.read()
            
            if ret and frame is not None:
                # Convert BGR to RGB for Qt display
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Update current frame (thread-safe)
                with self._frame_lock:
                    self._current_frame = frame_rgb
                
                # Emit signal for UI update
                self.frame_ready.emit(frame_rgb)
                
                # Calculate FPS
                self._update_fps()
            else:
                # Frame read failed
                self._set_state(CameraState.ERROR)
                break
            
            # Frame rate limiting
            elapsed = time.perf_counter() - loop_start
            sleep_time = self._frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _update_fps(self) -> None:
        """Calculate and emit current FPS."""
        current_time = time.perf_counter()
        
        if self._last_frame_time > 0:
            frame_time = current_time - self._last_frame_time
            instant_fps = 1.0 / frame_time if frame_time > 0 else 0
            
            # Keep rolling average of last 30 samples
            self._fps_samples.append(instant_fps)
            if len(self._fps_samples) > 30:
                self._fps_samples.pop(0)
            
            avg_fps = sum(self._fps_samples) / len(self._fps_samples)
            self.fps_updated.emit(avg_fps)
        
        self._last_frame_time = current_time
    
    def set_camera(self, camera_index: int) -> bool:
        """
        Switch to a different camera.
        
        Args:
            camera_index: Index of the camera to switch to
            
        Returns:
            True if switch was successful
        """
        was_running = self._running
        
        if was_running:
            self.stop()
        
        self._camera_index = camera_index
        
        if was_running:
            return self.start()
        
        return True
    
    def set_resolution(self, width: int, height: int) -> bool:
        """
        Change capture resolution.
        
        Args:
            width: Target width
            height: Target height
            
        Returns:
            True if change was successful
        """
        was_running = self._running
        
        if was_running:
            self.stop()
        
        self._resolution = (width, height)
        
        if was_running:
            return self.start()
        
        return True
    
    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
