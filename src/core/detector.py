"""
Face Detection Module for Center Stage Camera.

OPTIMIZED: Lightweight face detection for real-time performance.
Uses OpenCV's Haar Cascade with frame skipping and downscaling.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class FaceDetection:
    """Represents a detected face with bounding box and confidence."""
    
    x: float
    y: float
    width: float
    height: float
    confidence: float
    tracking_id: Optional[int] = None
    
    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    def to_pixels(self, frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
        return (
            int(self.x * frame_width),
            int(self.y * frame_height),
            int(self.width * frame_width),
            int(self.height * frame_height),
        )


@dataclass
class DetectionResult:
    """Result of face detection on a frame."""
    
    faces: list[FaceDetection]
    processing_time_ms: float
    
    @property
    def face_count(self) -> int:
        return len(self.faces)
    
    @property
    def has_faces(self) -> bool:
        return len(self.faces) > 0
    
    @property
    def primary_face(self) -> Optional[FaceDetection]:
        if not self.faces:
            return None
        return max(self.faces, key=lambda f: f.area)
    
    def get_bounding_box(self) -> Optional[tuple[float, float, float, float]]:
        if not self.faces:
            return None
        min_x = min(f.x for f in self.faces)
        min_y = min(f.y for f in self.faces)
        max_x = max(f.x + f.width for f in self.faces)
        max_y = max(f.y + f.height for f in self.faces)
        return (min_x, min_y, max_x - min_x, max_y - min_y)


class FaceDetector:
    """
    OPTIMIZED lightweight face detector.
    
    Performance optimizations:
    - Downscales frame before detection (4x faster)
    - Caches last detection for frame skipping
    - Minimal processing overhead
    """
    
    # Detection frame size (smaller = faster)
    DETECT_WIDTH = 320
    
    def __init__(
        self,
        min_confidence: float = 0.5,
        max_faces: int = 5,
        model_selection: int = 0,
    ):
        self._min_confidence = min_confidence
        self._max_faces = max_faces
        
        # Load cascade classifier
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Cache for frame skipping
        self._last_result: Optional[DetectionResult] = None
        self._frame_count = 0
        self._detect_interval = 3  # Detect every N frames
    
    @property
    def min_confidence(self) -> float:
        return self._min_confidence
    
    @min_confidence.setter
    def min_confidence(self, value: float) -> None:
        self._min_confidence = max(0.0, min(1.0, value))
    
    def detect(self, frame: np.ndarray, force: bool = False) -> DetectionResult:
        """
        Detect faces in a frame.
        
        Uses frame skipping - only runs detection every N frames,
        returns cached result otherwise.
        """
        self._frame_count += 1
        
        # Skip detection if we have cached result (HUGE performance boost)
        if not force and self._last_result is not None:
            if self._frame_count % self._detect_interval != 0:
                return self._last_result
        
        start_time = time.perf_counter()
        
        height, width = frame.shape[:2]
        
        # Downscale for faster detection
        scale = self.DETECT_WIDTH / width
        small_width = self.DETECT_WIDTH
        small_height = int(height * scale)
        
        small_frame = cv2.resize(frame, (small_width, small_height), interpolation=cv2.INTER_NEAREST)
        gray = cv2.cvtColor(small_frame, cv2.COLOR_RGB2GRAY)
        
        # Fast detection with relaxed parameters
        detected_faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,  # Faster
            minNeighbors=4,   # Less strict
            minSize=(20, 20),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        faces: list[FaceDetection] = []
        
        for i, (x, y, w, h) in enumerate(detected_faces[:self._max_faces]):
            # Convert back to original scale (normalized coordinates)
            face = FaceDetection(
                x=(x / small_width),
                y=(y / small_height),
                width=(w / small_width),
                height=(h / small_height),
                confidence=0.9,
                tracking_id=i,
            )
            faces.append(face)
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        result = DetectionResult(faces=faces, processing_time_ms=processing_time)
        self._last_result = result
        
        return result
    
    def close(self) -> None:
        pass
    
    def __del__(self):
        pass
