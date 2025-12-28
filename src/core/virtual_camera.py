"""
Virtual Camera Output for Center Stage Camera.

OPTIMIZED: Minimal latency virtual camera output.
"""

from __future__ import annotations

import threading
from typing import Optional

import cv2
import numpy as np

try:
    import pyvirtualcam
    from pyvirtualcam import PixelFormat
    VIRTUAL_CAM_AVAILABLE = True
except ImportError:
    VIRTUAL_CAM_AVAILABLE = False


class VirtualCameraOutput:
    """
    OPTIMIZED virtual camera output for minimal latency.
    
    - Uses 720p output (good quality, low overhead)
    - Skips sleep_until_next_frame for lower latency
    - Non-blocking frame sending
    """
    
    BACKENDS = ['unitycapture', 'obs']
    
    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
    ):
        self._width = width
        self._height = height
        self._fps = fps
        
        self._cam: Optional[pyvirtualcam.Camera] = None
        self._running = False
        self._lock = threading.Lock()
        self._backend_used = None
        
        # Pre-allocate buffer for speed
        self._frame_buffer = np.zeros((height, width, 3), dtype=np.uint8)
    
    @staticmethod
    def is_available() -> bool:
        return VIRTUAL_CAM_AVAILABLE
    
    @property
    def is_running(self) -> bool:
        return self._running and self._cam is not None
    
    @property
    def device_name(self) -> Optional[str]:
        if self._cam is not None:
            return self._cam.device
        return None
    
    @property
    def backend(self) -> Optional[str]:
        return self._backend_used
    
    def start(self) -> bool:
        if not VIRTUAL_CAM_AVAILABLE:
            print("pyvirtualcam not installed.")
            return False
        
        if self._running:
            return True
        
        for backend in self.BACKENDS:
            try:
                with self._lock:
                    self._cam = pyvirtualcam.Camera(
                        width=self._width,
                        height=self._height,
                        fps=self._fps,
                        fmt=PixelFormat.RGB,
                        backend=backend,
                    )
                    self._running = True
                    self._backend_used = backend
                    print(f"Virtual camera started: {self._cam.device}")
                return True
            except Exception:
                continue
        
        print("Failed to start virtual camera. Install UnityCapture.")
        return False
    
    def stop(self) -> None:
        with self._lock:
            if self._cam is not None:
                try:
                    self._cam.close()
                except Exception:
                    pass
                self._cam = None
            self._running = False
            self._backend_used = None
    
    def send_frame(self, frame: np.ndarray) -> bool:
        """Send frame with MINIMAL latency."""
        if not self._running or self._cam is None:
            return False
        
        try:
            h, w = frame.shape[:2]
            
            # Resize only if needed
            if w != self._width or h != self._height:
                # Use INTER_NEAREST for speed (minimal quality loss at 720p)
                frame = cv2.resize(frame, (self._width, self._height), 
                                   interpolation=cv2.INTER_LINEAR)
            
            # Ensure contiguous
            if not frame.flags['C_CONTIGUOUS']:
                frame = np.ascontiguousarray(frame)
            
            # Send without waiting (lower latency)
            with self._lock:
                if self._cam is not None:
                    self._cam.send(frame)
                    # REMOVED: sleep_until_next_frame() - causes lag!
            
            return True
        except Exception:
            return False
    
    def __del__(self):
        self.stop()
