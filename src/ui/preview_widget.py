"""
Preview Widget for Center Stage Camera.

High-performance video preview with OpenGL-accelerated rendering
and overlay support for face detection boxes and crop regions.
"""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


class PreviewWidget(QWidget):
    """
    Video preview widget with overlay support.
    
    Displays camera frames with optional overlays for:
    - Face detection bounding boxes
    - Crop region visualization
    - FPS and status text
    """
    
    # Signals
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_frame: Optional[np.ndarray] = None
        self._current_image: Optional[QImage] = None
        
        # Overlay options
        self._show_face_boxes = False
        self._show_crop_overlay = False
        self._show_fps = True
        
        # Overlay data
        self._face_boxes: list[tuple[float, float, float, float]] = []
        self._crop_region: Optional[tuple[float, float, float, float]] = None
        self._fps_value = 0.0
        self._status_text = ""
        self._face_count = 0
        
        # Styling
        self._background_color = QColor("#0A0A0F")
        self._face_box_color = QColor("#10B981")
        self._crop_box_color = QColor("#6366F1")
        self._text_color = QColor("#FFFFFF")
        
        # Setup
        self.setMinimumSize(640, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #0A0A0F; border-radius: 12px;")
    
    @Slot(np.ndarray)
    def update_frame(self, frame: np.ndarray) -> None:
        """
        Update the displayed frame.
        
        Args:
            frame: RGB image as numpy array
        """
        self._current_frame = frame
        
        # Convert numpy array to QImage
        height, width, channels = frame.shape
        bytes_per_line = channels * width
        
        self._current_image = QImage(
            frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        ).copy()  # Copy to own the data
        
        self.update()
    
    def set_face_boxes(self, boxes: list[tuple[float, float, float, float]]) -> None:
        """Set face bounding boxes (normalized coordinates)."""
        self._face_boxes = boxes
        self._face_count = len(boxes)
    
    def set_crop_region(self, region: Optional[tuple[float, float, float, float]]) -> None:
        """Set crop region overlay (normalized coordinates)."""
        self._crop_region = region
    
    def set_fps(self, fps: float) -> None:
        """Set FPS display value."""
        self._fps_value = fps
    
    def set_status(self, status: str) -> None:
        """Set status text overlay."""
        self._status_text = status
    
    def set_show_face_boxes(self, show: bool) -> None:
        """Toggle face box overlay."""
        self._show_face_boxes = show
    
    def set_show_crop_overlay(self, show: bool) -> None:
        """Toggle crop region overlay."""
        self._show_crop_overlay = show
    
    def set_show_fps(self, show: bool) -> None:
        """Toggle FPS display."""
        self._show_fps = show
    
    def paintEvent(self, event) -> None:
        """Paint the preview with overlays."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Fill background
        painter.fillRect(self.rect(), self._background_color)
        
        if self._current_image is not None:
            # Calculate aspect-fit scaling
            img_width = self._current_image.width()
            img_height = self._current_image.height()
            
            widget_width = self.width()
            widget_height = self.height()
            
            # Calculate scale to fit
            scale_x = widget_width / img_width
            scale_y = widget_height / img_height
            scale = min(scale_x, scale_y)
            
            # Calculate centered position
            scaled_width = int(img_width * scale)
            scaled_height = int(img_height * scale)
            x_offset = (widget_width - scaled_width) // 2
            y_offset = (widget_height - scaled_height) // 2
            
            # Draw scaled image
            scaled_image = self._current_image.scaled(
                scaled_width,
                scaled_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawImage(x_offset, y_offset, scaled_image)
            
            # Draw overlays
            if self._show_face_boxes:
                self._draw_face_boxes(painter, x_offset, y_offset, scaled_width, scaled_height)
            
            if self._show_crop_overlay and self._crop_region:
                self._draw_crop_overlay(painter, x_offset, y_offset, scaled_width, scaled_height)
            
            # Draw status overlay
            self._draw_status_overlay(painter)
        else:
            # No frame - show placeholder
            self._draw_placeholder(painter)
        
        painter.end()
    
    def _draw_face_boxes(
        self,
        painter: QPainter,
        x_offset: int,
        y_offset: int,
        width: int,
        height: int
    ) -> None:
        """Draw face detection bounding boxes."""
        pen = QPen(self._face_box_color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        for (x, y, w, h) in self._face_boxes:
            box_x = x_offset + int(x * width)
            box_y = y_offset + int(y * height)
            box_w = int(w * width)
            box_h = int(h * height)
            
            painter.drawRect(box_x, box_y, box_w, box_h)
    
    def _draw_crop_overlay(
        self,
        painter: QPainter,
        x_offset: int,
        y_offset: int,
        width: int,
        height: int
    ) -> None:
        """Draw crop region overlay."""
        if not self._crop_region:
            return
        
        x, y, w, h = self._crop_region
        
        crop_x = x_offset + int(x * width)
        crop_y = y_offset + int(y * height)
        crop_w = int(w * width)
        crop_h = int(h * height)
        
        # Draw darkened area outside crop
        dark_color = QColor(0, 0, 0, 100)
        
        # Left side
        painter.fillRect(x_offset, y_offset, crop_x - x_offset, height, dark_color)
        # Right side
        painter.fillRect(crop_x + crop_w, y_offset, 
                        x_offset + width - crop_x - crop_w, height, dark_color)
        # Top
        painter.fillRect(crop_x, y_offset, crop_w, crop_y - y_offset, dark_color)
        # Bottom
        painter.fillRect(crop_x, crop_y + crop_h, 
                        crop_w, y_offset + height - crop_y - crop_h, dark_color)
        
        # Draw crop border
        pen = QPen(self._crop_box_color, 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(crop_x, crop_y, crop_w, crop_h)
    
    def _draw_status_overlay(self, painter: QPainter) -> None:
        """Draw FPS and status text overlay."""
        if not self._show_fps and not self._status_text:
            return
        
        # Setup font
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Background pill for readability
        bg_color = QColor(0, 0, 0, 150)
        
        y_pos = 15
        x_pos = 15
        padding = 8
        
        if self._show_fps:
            fps_text = f"⚡ {self._fps_value:.0f} FPS"
            text_rect = painter.fontMetrics().boundingRect(fps_text)
            
            pill_rect = text_rect.adjusted(-padding, -padding//2, padding, padding//2)
            pill_rect.moveTopLeft(painter.fontMetrics().boundingRect(fps_text).topLeft())
            pill_rect.translate(x_pos, y_pos + text_rect.height())
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg_color)
            painter.drawRoundedRect(pill_rect, 6, 6)
            
            painter.setPen(self._text_color)
            painter.drawText(x_pos + padding, y_pos + text_rect.height(), fps_text)
            
            x_pos += pill_rect.width() + 10
        
        # Face count
        face_text = f"👤 {self._face_count} Face{'s' if self._face_count != 1 else ''}"
        text_rect = painter.fontMetrics().boundingRect(face_text)
        
        pill_rect = text_rect.adjusted(-padding, -padding//2, padding, padding//2)
        pill_rect.moveTopLeft(text_rect.topLeft())
        pill_rect.translate(x_pos, y_pos + text_rect.height())
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(pill_rect, 6, 6)
        
        painter.setPen(self._text_color)
        painter.drawText(x_pos + padding, y_pos + text_rect.height(), face_text)
    
    def _draw_placeholder(self, painter: QPainter) -> None:
        """Draw placeholder when no frame is available."""
        # Center text
        font = QFont("Segoe UI", 16)
        painter.setFont(font)
        painter.setPen(QColor("#6B7280"))
        
        text = "📷 No Camera Signal"
        rect = self.rect()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def clear(self) -> None:
        """Clear the current frame."""
        self._current_frame = None
        self._current_image = None
        self.update()
