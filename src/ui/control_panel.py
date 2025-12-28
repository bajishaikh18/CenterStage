"""
Control Panel for Center Stage Camera.

Provides controls for camera selection, Center Stage settings,
and application configuration.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.camera import CameraCapture, CameraInfo
from .widgets import SliderWithLabel, StatusIndicator, ToggleSwitch
from .widgets.status_indicator import StatusType


class ControlPanel(QWidget):
    """
    Control panel with all camera and Center Stage settings.
    
    Signals:
        camera_changed: Camera index changed
        center_stage_toggled: Center Stage enabled/disabled
        smoothing_changed: Smoothing value changed (0-100)
        zoom_changed: Zoom range changed (min, max)
        virtual_camera_toggled: Virtual camera enabled/disabled
        face_boxes_toggled: Show/hide face boxes
        crop_overlay_toggled: Show/hide crop overlay
    """
    
    camera_changed = Signal(int)
    center_stage_toggled = Signal(bool)
    smoothing_changed = Signal(int)
    zoom_min_changed = Signal(int)
    zoom_max_changed = Signal(int)
    virtual_camera_toggled = Signal(bool)
    face_boxes_toggled = Signal(bool)
    crop_overlay_toggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._cameras: list[CameraInfo] = []
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the control panel UI."""
        # Main layout with scroll area for responsiveness
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # ===== Camera Section =====
        camera_group = self._create_section("📷  Camera")
        camera_layout = QVBoxLayout()
        camera_layout.setSpacing(12)
        
        # Camera dropdown
        camera_row = QHBoxLayout()
        camera_label = QLabel("Source")
        camera_label.setObjectName("controlLabel")
        camera_row.addWidget(camera_label)
        
        self._camera_combo = QComboBox()
        self._camera_combo.setObjectName("cameraCombo")
        self._camera_combo.setMinimumWidth(200)
        self._camera_combo.addItem("Detecting cameras...")
        camera_row.addWidget(self._camera_combo, 1)
        
        camera_layout.addLayout(camera_row)
        
        # Camera status
        self._camera_status = StatusIndicator(label="Camera Status", status=StatusType.INACTIVE)
        camera_layout.addWidget(self._camera_status)
        
        camera_group.setLayout(camera_layout)
        content_layout.addWidget(camera_group)
        
        # ===== Center Stage Section =====
        cs_group = self._create_section("🎯  Center Stage")
        cs_layout = QVBoxLayout()
        cs_layout.setSpacing(16)
        
        # Enable toggle
        enable_row = QHBoxLayout()
        enable_label = QLabel("Enable Center Stage")
        enable_label.setObjectName("controlLabel")
        enable_row.addWidget(enable_label)
        enable_row.addStretch()
        
        self._cs_toggle = ToggleSwitch(checked=True)
        enable_row.addWidget(self._cs_toggle)
        
        cs_layout.addLayout(enable_row)
        
        # Tracking status
        self._tracking_status = StatusIndicator(label="Tracking", status=StatusType.INACTIVE)
        cs_layout.addWidget(self._tracking_status)
        
        # Separator
        cs_layout.addWidget(self._create_separator())
        
        # Smoothing slider
        self._smoothing_slider = SliderWithLabel(
            label="🔄  Smoothness",
            min_value=1,
            max_value=10,
            default_value=5,
            suffix="",
        )
        cs_layout.addWidget(self._smoothing_slider)
        
        # Zoom range
        self._zoom_min_slider = SliderWithLabel(
            label="🔍  Min Zoom",
            min_value=10,
            max_value=20,
            default_value=10,
            suffix="x",
        )
        self._zoom_min_slider.setMultiplier(0.1)
        cs_layout.addWidget(self._zoom_min_slider)
        
        self._zoom_max_slider = SliderWithLabel(
            label="🔍  Max Zoom",
            min_value=15,
            max_value=30,
            default_value=25,
            suffix="x",
        )
        self._zoom_max_slider.setMultiplier(0.1)
        cs_layout.addWidget(self._zoom_max_slider)
        
        cs_group.setLayout(cs_layout)
        content_layout.addWidget(cs_group)
        
        # ===== Display Section =====
        display_group = self._create_section("🖥️  Display")
        display_layout = QVBoxLayout()
        display_layout.setSpacing(12)
        
        # Show face boxes
        face_row = QHBoxLayout()
        face_label = QLabel("Show Face Boxes")
        face_label.setObjectName("controlLabel")
        face_row.addWidget(face_label)
        face_row.addStretch()
        self._face_boxes_toggle = ToggleSwitch(checked=False)
        face_row.addWidget(self._face_boxes_toggle)
        display_layout.addLayout(face_row)
        
        # Show crop overlay
        crop_row = QHBoxLayout()
        crop_label = QLabel("Show Crop Overlay")
        crop_label.setObjectName("controlLabel")
        crop_row.addWidget(crop_label)
        crop_row.addStretch()
        self._crop_overlay_toggle = ToggleSwitch(checked=False)
        crop_row.addWidget(self._crop_overlay_toggle)
        display_layout.addLayout(crop_row)
        
        display_group.setLayout(display_layout)
        content_layout.addWidget(display_group)
        
        # ===== Virtual Camera Section =====
        vcam_group = self._create_section("📹  Virtual Camera")
        vcam_layout = QVBoxLayout()
        vcam_layout.setSpacing(12)
        
        vcam_row = QHBoxLayout()
        vcam_label = QLabel("Enable Virtual Camera")
        vcam_label.setObjectName("controlLabel")
        vcam_row.addWidget(vcam_label)
        vcam_row.addStretch()
        self._vcam_toggle = ToggleSwitch(checked=False)
        vcam_row.addWidget(self._vcam_toggle)
        vcam_layout.addLayout(vcam_row)
        
        self._vcam_status = StatusIndicator(label="Virtual Camera", status=StatusType.INACTIVE)
        vcam_layout.addWidget(self._vcam_status)
        
        vcam_info = QLabel("Use as camera in Zoom, Teams, etc.")
        vcam_info.setObjectName("infoLabel")
        vcam_info.setWordWrap(True)
        vcam_layout.addWidget(vcam_info)
        
        vcam_group.setLayout(vcam_layout)
        content_layout.addWidget(vcam_group)
        
        # Spacer at bottom
        content_layout.addStretch()
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
    
    def _create_section(self, title: str) -> QGroupBox:
        """Create a styled section group box."""
        group = QGroupBox(title)
        group.setObjectName("controlSection")
        return group
    
    def _create_separator(self) -> QFrame:
        """Create a horizontal separator line."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        return line
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self._camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        self._cs_toggle.toggled.connect(self.center_stage_toggled)
        self._smoothing_slider.valueChanged.connect(self.smoothing_changed)
        self._zoom_min_slider.valueChanged.connect(self.zoom_min_changed)
        self._zoom_max_slider.valueChanged.connect(self.zoom_max_changed)
        self._vcam_toggle.toggled.connect(self.virtual_camera_toggled)
        self._face_boxes_toggle.toggled.connect(self.face_boxes_toggled)
        self._crop_overlay_toggle.toggled.connect(self.crop_overlay_toggled)
    
    def _on_camera_changed(self, index: int) -> None:
        """Handle camera selection change."""
        if 0 <= index < len(self._cameras):
            self.camera_changed.emit(self._cameras[index].index)
    
    def set_cameras(self, cameras: list[CameraInfo]) -> None:
        """Update available cameras list."""
        self._cameras = cameras
        self._camera_combo.clear()
        
        if cameras:
            for cam in cameras:
                self._camera_combo.addItem(str(cam), cam.index)
        else:
            self._camera_combo.addItem("No cameras found")
    
    def set_camera_connected(self, connected: bool) -> None:
        """Update camera connection status."""
        self._camera_status.setStatus(
            StatusType.ACTIVE if connected else StatusType.INACTIVE
        )
        self._camera_status.setLabel(
            "Connected" if connected else "Disconnected"
        )
    
    def set_tracking_active(self, active: bool) -> None:
        """Update tracking status."""
        self._tracking_status.setStatus(
            StatusType.ACTIVE if active else StatusType.INACTIVE
        )
        self._tracking_status.setLabel(
            "Tracking Face" if active else "No Face Detected"
        )
    
    def set_virtual_camera_active(self, active: bool) -> None:
        """Update virtual camera status."""
        self._vcam_status.setStatus(
            StatusType.ACTIVE if active else StatusType.INACTIVE
        )
        self._vcam_status.setLabel(
            "Broadcasting" if active else "Off"
        )
    
    def get_smoothing(self) -> float:
        """Get smoothing value (0.01-0.2)."""
        # Map 1-10 slider to 0.01-0.2 smoothing factor
        return self._smoothing_slider.value * 0.02
    
    def get_zoom_range(self) -> tuple[float, float]:
        """Get zoom range (min, max)."""
        return (
            self._zoom_min_slider.value * 0.1,
            self._zoom_max_slider.value * 0.1,
        )
