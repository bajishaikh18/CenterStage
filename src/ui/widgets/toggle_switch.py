"""
Toggle Switch Widget for Center Stage Camera.

A modern iOS-style animated toggle switch widget.
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    """
    Modern animated toggle switch widget.
    
    Signals:
        toggled: Emitted when the switch is toggled (bool state)
    """
    
    toggled = Signal(bool)
    
    def __init__(
        self,
        parent=None,
        checked: bool = False,
        track_color_off: QColor = QColor("#3A3A3F"),
        track_color_on: QColor = QColor("#6366F1"),
        thumb_color: QColor = QColor("#FFFFFF"),
        disabled_color: QColor = QColor("#555555"),
    ):
        super().__init__(parent)
        
        self._checked = checked
        self._track_color_off = track_color_off
        self._track_color_on = track_color_on
        self._thumb_color = thumb_color
        self._disabled_color = disabled_color
        
        # Animation progress (0 = off, 1 = on)
        self._progress = 1.0 if checked else 0.0
        
        # Animation
        self._animation = QPropertyAnimation(self, b"progress", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        # Size
        self.setFixedSize(50, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def get_progress(self) -> float:
        return self._progress
    
    def set_progress(self, value: float) -> None:
        self._progress = value
        self.update()
    
    progress = Property(float, get_progress, set_progress)
    
    @property
    def checked(self) -> bool:
        """Whether the switch is checked."""
        return self._checked
    
    @checked.setter
    def checked(self, value: bool) -> None:
        """Set the checked state."""
        if self._checked != value:
            self._checked = value
            self._animate_to(1.0 if value else 0.0)
            self.toggled.emit(value)
    
    def isChecked(self) -> bool:
        """Qt-style checked getter."""
        return self._checked
    
    def setChecked(self, checked: bool) -> None:
        """Qt-style checked setter."""
        self.checked = checked
    
    def toggle(self) -> None:
        """Toggle the switch state."""
        self.checked = not self._checked
    
    def _animate_to(self, target: float) -> None:
        """Animate to target progress value."""
        self._animation.stop()
        self._animation.setStartValue(self._progress)
        self._animation.setEndValue(target)
        self._animation.start()
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press to toggle."""
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.toggle()
        super().mousePressEvent(event)
    
    def paintEvent(self, event) -> None:
        """Paint the toggle switch."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dimensions
        width = self.width()
        height = self.height()
        track_height = height
        track_radius = track_height / 2
        thumb_radius = (height - 6) / 2
        thumb_margin = 3
        
        # Track color (interpolate between off and on)
        if not self.isEnabled():
            track_color = self._disabled_color
        else:
            r = int(self._track_color_off.red() + 
                   (self._track_color_on.red() - self._track_color_off.red()) * self._progress)
            g = int(self._track_color_off.green() + 
                   (self._track_color_on.green() - self._track_color_off.green()) * self._progress)
            b = int(self._track_color_off.blue() + 
                   (self._track_color_on.blue() - self._track_color_off.blue()) * self._progress)
            track_color = QColor(r, g, b)
        
        # Draw track
        track_path = QPainterPath()
        track_path.addRoundedRect(0, 0, width, track_height, track_radius, track_radius)
        painter.fillPath(track_path, track_color)
        
        # Calculate thumb position
        thumb_left = thumb_margin
        thumb_right = width - thumb_margin - thumb_radius * 2
        thumb_x = thumb_left + (thumb_right - thumb_left) * self._progress
        thumb_y = thumb_margin
        
        # Draw thumb with shadow
        thumb_color = self._thumb_color if self.isEnabled() else QColor("#AAAAAA")
        
        # Shadow
        shadow_color = QColor(0, 0, 0, 40)
        painter.setBrush(shadow_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(thumb_x + 1), int(thumb_y + 2), 
                           int(thumb_radius * 2), int(thumb_radius * 2))
        
        # Thumb
        painter.setBrush(thumb_color)
        painter.drawEllipse(int(thumb_x), int(thumb_y), 
                           int(thumb_radius * 2), int(thumb_radius * 2))
        
        painter.end()
