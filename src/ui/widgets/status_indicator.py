"""
Status Indicator Widget for Center Stage Camera.

A colored status indicator dot with optional label.
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusType(Enum):
    """Status indicator types with colors."""
    INACTIVE = "#6B7280"   # Gray
    ACTIVE = "#10B981"     # Green
    WARNING = "#F59E0B"    # Amber
    ERROR = "#EF4444"      # Red
    INFO = "#6366F1"       # Indigo


class StatusIndicator(QWidget):
    """
    Colored status indicator with optional label.
    """
    
    def __init__(
        self,
        parent=None,
        label: str = "",
        status: StatusType = StatusType.INACTIVE,
        dot_size: int = 10,
    ):
        super().__init__(parent)
        
        self._status = status
        self._dot_size = dot_size
        self._pulsing = False
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Dot widget
        self._dot = _StatusDot(self, dot_size, QColor(status.value))
        layout.addWidget(self._dot)
        
        # Label
        self._label = QLabel(label)
        self._label.setObjectName("statusLabel")
        layout.addWidget(self._label)
        
        layout.addStretch()
    
    @property
    def status(self) -> StatusType:
        """Get current status."""
        return self._status
    
    @status.setter
    def status(self, value: StatusType) -> None:
        """Set status."""
        self._status = value
        self._dot.set_color(QColor(value.value))
    
    def setStatus(self, status: StatusType) -> None:
        """Qt-style status setter."""
        self.status = status
    
    def setLabel(self, label: str) -> None:
        """Set label text."""
        self._label.setText(label)
    
    def setActive(self, active: bool = True) -> None:
        """Convenience method to set active/inactive."""
        self.status = StatusType.ACTIVE if active else StatusType.INACTIVE


class _StatusDot(QWidget):
    """Internal dot widget with glow effect."""
    
    def __init__(self, parent, size: int, color: QColor):
        super().__init__(parent)
        self._size = size
        self._color = color
        self.setFixedSize(size + 4, size + 4)  # Extra space for glow
    
    def set_color(self, color: QColor) -> None:
        """Set dot color."""
        self._color = color
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the status dot with glow."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = self._size / 2
        
        # Glow effect (semi-transparent larger circle)
        glow_color = QColor(self._color)
        glow_color.setAlpha(80)
        painter.setBrush(glow_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            int(center_x - radius - 2),
            int(center_y - radius - 2),
            int(self._size + 4),
            int(self._size + 4)
        )
        
        # Main dot
        painter.setBrush(self._color)
        painter.drawEllipse(
            int(center_x - radius),
            int(center_y - radius),
            int(self._size),
            int(self._size)
        )
        
        painter.end()
