"""
Center Stage Algorithm for Center Stage Camera.

The heart of the application - implements Apple-style Center Stage behavior
with smooth pan/zoom simulation, dead zones, and multi-face framing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import cv2
import numpy as np

from .detector import DetectionResult, FaceDetection


class FramingMode(Enum):
    """How to frame detected faces."""
    SINGLE = "single"      # Focus on primary (largest) face
    ALL = "all"            # Frame all detected faces
    CLOSEST = "closest"    # Focus on closest (largest) face


@dataclass
class CropRegion:
    """
    Represents a crop region in normalized coordinates (0-1).
    
    The crop region defines what portion of the original frame
    to extract and scale up to create the output.
    """
    
    # Top-left corner (normalized 0-1)
    x: float
    y: float
    
    # Size (normalized 0-1)
    width: float
    height: float
    
    @property
    def center(self) -> tuple[float, float]:
        """Center point of the region."""
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def right(self) -> float:
        """Right edge of the region."""
        return self.x + self.width
    
    @property
    def bottom(self) -> float:
        """Bottom edge of the region."""
        return self.y + self.height
    
    def to_pixels(self, frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
        """Convert to pixel coordinates."""
        return (
            int(self.x * frame_width),
            int(self.y * frame_height),
            int(self.width * frame_width),
            int(self.height * frame_height),
        )
    
    @classmethod
    def full_frame(cls) -> "CropRegion":
        """Create a crop region covering the full frame."""
        return cls(x=0.0, y=0.0, width=1.0, height=1.0)
    
    def clamp(self) -> "CropRegion":
        """Clamp region to valid bounds (0-1)."""
        x = max(0.0, min(self.x, 1.0 - self.width))
        y = max(0.0, min(self.y, 1.0 - self.height))
        width = min(self.width, 1.0 - x)
        height = min(self.height, 1.0 - y)
        return CropRegion(x=x, y=y, width=width, height=height)
    
    def lerp(self, target: "CropRegion", factor: float) -> "CropRegion":
        """Linear interpolation towards target region."""
        return CropRegion(
            x=self.x + (target.x - self.x) * factor,
            y=self.y + (target.y - self.y) * factor,
            width=self.width + (target.width - self.width) * factor,
            height=self.height + (target.height - self.height) * factor,
        )


@dataclass
class CenterStageConfig:
    """Configuration for Center Stage behavior."""
    
    # Smoothing factor (0-1): lower = smoother, higher = more responsive
    smoothing: float = 0.08
    
    # Dead zone (0-1): minimum movement required before tracking kicks in
    dead_zone: float = 0.015
    
    # Zoom levels
    min_zoom: float = 1.0      # Minimum zoom (1.0 = no zoom)
    max_zoom: float = 2.5      # Maximum zoom
    
    # Padding around faces (as fraction of frame)
    face_padding: float = 0.35
    
    # Aspect ratio to maintain (width/height)
    aspect_ratio: float = 16 / 9
    
    # Framing mode
    framing_mode: FramingMode = FramingMode.ALL
    
    # Frames to wait before returning to full frame when no faces
    frames_until_reset: int = 60
    
    # Enable/disable Center Stage
    enabled: bool = True


@dataclass
class CenterStageState:
    """Internal state for Center Stage algorithm."""
    
    # Current crop region
    current_crop: CropRegion = field(default_factory=CropRegion.full_frame)
    
    # Target crop region (what we're moving towards)
    target_crop: CropRegion = field(default_factory=CropRegion.full_frame)
    
    # Frames since last face detection
    frames_without_face: int = 0
    
    # Whether currently tracking
    is_tracking: bool = False


class CenterStageEngine:
    """
    Implements Center Stage camera behavior.
    
    Features:
    - Smooth pan/zoom with exponential interpolation
    - Dead zone to prevent jittery movement
    - Multi-face framing with configurable modes
    - Graceful fallback to full frame when faces are lost
    - Maintains aspect ratio
    """
    
    def __init__(self, config: Optional[CenterStageConfig] = None):
        """
        Initialize the Center Stage engine.
        
        Args:
            config: Configuration settings (uses defaults if None)
        """
        self.config = config or CenterStageConfig()
        self._state = CenterStageState()
    
    @property
    def is_tracking(self) -> bool:
        """Whether currently tracking a face."""
        return self._state.is_tracking
    
    @property
    def current_crop(self) -> CropRegion:
        """Current crop region."""
        return self._state.current_crop
    
    @property
    def zoom_level(self) -> float:
        """Current effective zoom level."""
        return 1.0 / self._state.current_crop.width
    
    def reset(self) -> None:
        """Reset to full frame."""
        self._state = CenterStageState()
    
    def update(self, detection_result: DetectionResult) -> CropRegion:
        """
        Update Center Stage with new detection result.
        
        Args:
            detection_result: Face detection result
            
        Returns:
            Current crop region to apply
        """
        if not self.config.enabled:
            return CropRegion.full_frame()
        
        if detection_result.has_faces:
            # Calculate target crop based on detected faces
            self._state.target_crop = self._calculate_target_crop(detection_result)
            self._state.frames_without_face = 0
            self._state.is_tracking = True
        else:
            # No faces detected
            self._state.frames_without_face += 1
            
            # Gradually return to full frame after timeout
            if self._state.frames_without_face >= self.config.frames_until_reset:
                self._state.target_crop = CropRegion.full_frame()
                self._state.is_tracking = False
        
        # Smooth interpolation towards target
        self._state.current_crop = self._smooth_transition(
            self._state.current_crop,
            self._state.target_crop,
        )
        
        return self._state.current_crop
    
    def _calculate_target_crop(self, result: DetectionResult) -> CropRegion:
        """
        Calculate the optimal crop region to frame detected faces.
        
        Args:
            result: Detection result with faces
            
        Returns:
            Target crop region
        """
        if self.config.framing_mode == FramingMode.SINGLE:
            # Use only the primary (largest) face
            primary = result.primary_face
            if primary is None:
                return CropRegion.full_frame()
            faces = [primary]
        else:
            # Use all faces
            faces = result.faces
        
        # Get bounding box encompassing all faces
        min_x = min(f.x for f in faces)
        min_y = min(f.y for f in faces)
        max_x = max(f.x + f.width for f in faces)
        max_y = max(f.y + f.height for f in faces)
        
        # Add padding
        face_width = max_x - min_x
        face_height = max_y - min_y
        
        padding_x = face_width * self.config.face_padding
        padding_y = face_height * self.config.face_padding
        
        # Expand bounds with padding
        min_x = max(0.0, min_x - padding_x)
        min_y = max(0.0, min_y - padding_y)
        max_x = min(1.0, max_x + padding_x)
        max_y = min(1.0, max_y + padding_y)
        
        # Calculate required size
        region_width = max_x - min_x
        region_height = max_y - min_y
        
        # Adjust to maintain aspect ratio
        target_ratio = self.config.aspect_ratio
        current_ratio = region_width / region_height if region_height > 0 else target_ratio
        
        if current_ratio > target_ratio:
            # Too wide, increase height
            new_height = region_width / target_ratio
            height_increase = new_height - region_height
            min_y = max(0.0, min_y - height_increase / 2)
            region_height = new_height
        else:
            # Too tall, increase width
            new_width = region_height * target_ratio
            width_increase = new_width - region_width
            min_x = max(0.0, min_x - width_increase / 2)
            region_width = new_width
        
        # Apply zoom limits
        max_size = 1.0 / self.config.min_zoom  # Minimum zoom = largest crop
        min_size = 1.0 / self.config.max_zoom  # Maximum zoom = smallest crop
        
        region_width = max(min_size, min(max_size, region_width))
        region_height = region_width / target_ratio
        
        # Center the crop on the face center
        face_center_x = (min_x + max_x) / 2
        face_center_y = (min_y + max_y) / 2
        
        crop_x = face_center_x - region_width / 2
        crop_y = face_center_y - region_height / 2
        
        crop = CropRegion(
            x=crop_x,
            y=crop_y,
            width=region_width,
            height=region_height,
        )
        
        return crop.clamp()
    
    def _smooth_transition(
        self,
        current: CropRegion,
        target: CropRegion,
    ) -> CropRegion:
        """
        Apply smooth interpolation with dead zone.
        
        Args:
            current: Current crop region
            target: Target crop region
            
        Returns:
            Smoothly interpolated crop region
        """
        # Check dead zone - if movement is very small, don't move
        dx = abs(target.center[0] - current.center[0])
        dy = abs(target.center[1] - current.center[1])
        dw = abs(target.width - current.width)
        
        total_delta = dx + dy + dw
        
        if total_delta < self.config.dead_zone:
            return current
        
        # Exponential smoothing (lerp)
        smoothed = current.lerp(target, self.config.smoothing)
        
        return smoothed.clamp()
    
    def apply_crop(
        self,
        frame: np.ndarray,
        crop: Optional[CropRegion] = None,
        output_size: Optional[tuple[int, int]] = None,
    ) -> np.ndarray:
        """
        Apply crop region to a frame.
        
        Args:
            frame: Input frame (RGB)
            crop: Crop region to apply (uses current if None)
            output_size: Output size (width, height), uses input size if None
            
        Returns:
            Cropped and scaled frame
        """
        if crop is None:
            crop = self._state.current_crop
        
        h, w = frame.shape[:2]
        
        # Convert to pixel coordinates
        x, y, cw, ch = crop.to_pixels(w, h)
        
        # Ensure valid bounds
        x = max(0, min(x, w - cw))
        y = max(0, min(y, h - ch))
        cw = min(cw, w - x)
        ch = min(ch, h - y)
        
        # Crop the frame
        cropped = frame[y:y+ch, x:x+cw]
        
        # Scale to output size
        if output_size is None:
            output_size = (w, h)
        
        scaled = cv2.resize(cropped, output_size, interpolation=cv2.INTER_LINEAR)
        
        return scaled
    
    def draw_debug_overlay(
        self,
        frame: np.ndarray,
        crop: Optional[CropRegion] = None,
        color: tuple[int, int, int] = (0, 255, 255),
    ) -> np.ndarray:
        """
        Draw debug overlay showing current crop region.
        
        Args:
            frame: Input frame (RGB)
            crop: Crop region to visualize
            color: Overlay color (R, G, B)
            
        Returns:
            Frame with debug overlay
        """
        if crop is None:
            crop = self._state.current_crop
        
        h, w = frame.shape[:2]
        output = frame.copy()
        
        # Draw crop rectangle
        x, y, cw, ch = crop.to_pixels(w, h)
        cv2.rectangle(output, (x, y), (x + cw, y + ch), color, 2)
        
        # Draw center crosshair
        cx, cy = int(crop.center[0] * w), int(crop.center[1] * h)
        cv2.line(output, (cx - 10, cy), (cx + 10, cy), color, 2)
        cv2.line(output, (cx, cy - 10), (cx, cy + 10), color, 2)
        
        # Draw zoom level
        zoom_text = f"Zoom: {self.zoom_level:.1f}x"
        cv2.putText(output, zoom_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Draw tracking status
        status = "TRACKING" if self.is_tracking else "IDLE"
        cv2.putText(output, status, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        return output
    
    def set_smoothing(self, value: float) -> None:
        """Set smoothing factor (0-1)."""
        self.config.smoothing = max(0.01, min(0.5, value))
    
    def set_zoom_range(self, min_zoom: float, max_zoom: float) -> None:
        """Set zoom range."""
        self.config.min_zoom = max(1.0, min_zoom)
        self.config.max_zoom = max(self.config.min_zoom, max_zoom)
    
    def set_framing_mode(self, mode: FramingMode) -> None:
        """Set framing mode."""
        self.config.framing_mode = mode
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable Center Stage."""
        self.config.enabled = enabled
        if not enabled:
            self.reset()
