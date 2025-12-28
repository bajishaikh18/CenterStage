"""
Slider With Label Widget for Center Stage Camera.

A styled slider with value label display.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget


class SliderWithLabel(QWidget):
    """
    Styled slider with label and value display.
    
    Signals:
        valueChanged: Emitted when slider value changes
    """
    
    valueChanged = Signal(int)
    
    def __init__(
        self,
        parent=None,
        label: str = "",
        min_value: int = 0,
        max_value: int = 100,
        default_value: int = 50,
        suffix: str = "",
        show_value: bool = True,
    ):
        super().__init__(parent)
        
        self._suffix = suffix
        self._show_value = show_value
        self._multiplier = 1.0  # For float values displayed as int
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header row (label + value)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self._label = QLabel(label)
        self._label.setObjectName("sliderLabel")
        header_layout.addWidget(self._label)
        
        header_layout.addStretch()
        
        self._value_label = QLabel()
        self._value_label.setObjectName("sliderValue")
        self._value_label.setVisible(show_value)
        header_layout.addWidget(self._value_label)
        
        layout.addLayout(header_layout)
        
        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setObjectName("styledSlider")
        self._slider.setMinimum(min_value)
        self._slider.setMaximum(max_value)
        self._slider.setValue(default_value)
        self._slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._slider)
        
        # Initial value display
        self._update_value_label()
    
    def _on_value_changed(self, value: int) -> None:
        """Handle slider value change."""
        self._update_value_label()
        self.valueChanged.emit(value)
    
    def _update_value_label(self) -> None:
        """Update the value label display."""
        value = self._slider.value()
        
        if self._multiplier != 1.0:
            display_value = value * self._multiplier
            if display_value == int(display_value):
                text = f"{int(display_value)}{self._suffix}"
            else:
                text = f"{display_value:.1f}{self._suffix}"
        else:
            text = f"{value}{self._suffix}"
        
        self._value_label.setText(text)
    
    @property
    def value(self) -> int:
        """Get current slider value."""
        return self._slider.value()
    
    @value.setter
    def value(self, val: int) -> None:
        """Set slider value."""
        self._slider.setValue(val)
    
    def setValue(self, value: int) -> None:
        """Qt-style value setter."""
        self._slider.setValue(value)
    
    def setRange(self, min_val: int, max_val: int) -> None:
        """Set slider range."""
        self._slider.setMinimum(min_val)
        self._slider.setMaximum(max_val)
    
    def setMultiplier(self, multiplier: float) -> None:
        """Set display multiplier for float values."""
        self._multiplier = multiplier
        self._update_value_label()
    
    def setSuffix(self, suffix: str) -> None:
        """Set value suffix."""
        self._suffix = suffix
        self._update_value_label()
    
    def setLabel(self, label: str) -> None:
        """Set the label text."""
        self._label.setText(label)
