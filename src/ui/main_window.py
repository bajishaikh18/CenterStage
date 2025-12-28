"""
Main Window for Center Stage Camera.

The main application window with custom title bar, preview area,
control panel, and status bar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core.camera import CameraCapture, CameraState
from ..core.center_stage import CenterStageConfig, CenterStageEngine
from ..core.detector import FaceDetector
from ..core.virtual_camera import VirtualCameraOutput
from ..utils.config import Config
from ..utils.performance import FPSCounter
from .control_panel import ControlPanel
from .preview_widget import PreviewWidget


class MainWindow(QMainWindow):
    """
    Main application window for Center Stage Camera.
    
    Features:
    - Custom frameless title bar
    - Live camera preview with overlays
    - Collapsible control panel
    - Status bar with metrics
    - Virtual camera output for Teams/Zoom
    """
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self._config = Config()
        self._camera = CameraCapture(
            camera_index=self._config.app.camera_index,
            resolution=self._config.app.resolution,
        )
        self._detector = FaceDetector(
            min_confidence=self._config.app.detection_confidence,
        )
        self._center_stage = CenterStageEngine(
            CenterStageConfig(
                smoothing=self._config.app.smoothing,
                enabled=self._config.app.center_stage_enabled,
            )
        )
        self._fps_counter = FPSCounter()
        
        # Virtual camera output
        self._virtual_camera = VirtualCameraOutput(
            width=1280,
            height=720,
            fps=30,
        )
        
        # State
        self._is_processing = False
        self._frame_count = 0  # For throttling UI updates
        
        # Setup UI
        self._setup_window()
        self._setup_ui()
        self._load_styles()
        self._connect_signals()
        
        # Start camera after UI is ready
        QTimer.singleShot(100, self._initialize_camera)
    
    def _setup_window(self) -> None:
        """Configure main window properties."""
        self.setWindowTitle("Center Stage")
        self.setMinimumSize(1024, 640)
        
        # Set window size from config
        self.resize(
            self._config.app.window_width,
            self._config.app.window_height
        )
        
        # Center on screen if no saved position
        if self._config.app.window_x is None:
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                x = (geo.width() - self.width()) // 2
                y = (geo.height() - self.height()) // 2
                self.move(x, y)
        else:
            self.move(self._config.app.window_x, self._config.app.window_y)
    
    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== Title Bar =====
        self._title_bar = self._create_title_bar()
        main_layout.addWidget(self._title_bar)
        
        # ===== Content Area (Preview + Controls) =====
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(1)
        content_splitter.setStyleSheet(
            "QSplitter::handle { background-color: rgba(255, 255, 255, 0.05); }"
        )
        
        # Preview container
        preview_container = QFrame()
        preview_container.setObjectName("previewContainer")
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(16, 16, 8, 16)
        
        self._preview = PreviewWidget()
        self._preview.set_show_fps(self._config.app.show_fps)
        self._preview.set_show_face_boxes(self._config.app.show_face_boxes)
        self._preview.set_show_crop_overlay(self._config.app.show_crop_overlay)
        preview_layout.addWidget(self._preview)
        
        content_splitter.addWidget(preview_container)
        
        # Control panel
        control_container = QFrame()
        control_container.setObjectName("controlPanel")
        control_container.setFixedWidth(320)
        control_layout = QVBoxLayout(control_container)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        self._control_panel = ControlPanel()
        control_layout.addWidget(self._control_panel)
        
        content_splitter.addWidget(control_container)
        
        # Set initial sizes
        content_splitter.setSizes([700, 320])
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 0)
        
        main_layout.addWidget(content_splitter, 1)
        
        # ===== Status Bar =====
        self._status_bar = self._create_status_bar()
        main_layout.addWidget(self._status_bar)
    
    def _create_title_bar(self) -> QWidget:
        """Create custom title bar."""
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(48)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(12)
        
        # App icon and title
        title_label = QLabel("🎥 CENTER STAGE")
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Window controls
        minimize_btn = QPushButton("—")
        minimize_btn.setObjectName("titleBarButton")
        minimize_btn.setFixedSize(36, 28)
        minimize_btn.clicked.connect(self.showMinimized)
        layout.addWidget(minimize_btn)
        
        maximize_btn = QPushButton("□")
        maximize_btn.setObjectName("titleBarButton")
        maximize_btn.setFixedSize(36, 28)
        maximize_btn.clicked.connect(self._toggle_maximize)
        layout.addWidget(maximize_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(36, 28)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        return title_bar
    
    def _create_status_bar(self) -> QWidget:
        """Create status bar."""
        status_bar = QFrame()
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(32)
        
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(24)
        
        self._fps_label = QLabel("⚡ -- FPS")
        self._fps_label.setObjectName("statusBarLabel")
        layout.addWidget(self._fps_label)
        
        self._face_label = QLabel("👤 0 Faces")
        self._face_label.setObjectName("statusBarLabel")
        layout.addWidget(self._face_label)
        
        self._tracking_label = QLabel("🎯 Idle")
        self._tracking_label.setObjectName("statusBarLabel")
        layout.addWidget(self._tracking_label)
        
        layout.addStretch()
        
        self._vcam_label = QLabel("📹 Virtual Camera: Off")
        self._vcam_label.setObjectName("statusBarLabel")
        layout.addWidget(self._vcam_label)
        
        return status_bar
    
    def _load_styles(self) -> None:
        """Load and apply stylesheet."""
        style_path = Path(__file__).parent.parent / "styles" / "dark_theme.qss"
        if style_path.exists():
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
    
    def _connect_signals(self) -> None:
        """Connect all signals and slots."""
        # Camera signals
        self._camera.frame_ready.connect(self._on_frame_ready)
        self._camera.state_changed.connect(self._on_camera_state_changed)
        self._camera.fps_updated.connect(self._on_fps_updated)
        
        # Control panel signals
        self._control_panel.camera_changed.connect(self._on_camera_changed)
        self._control_panel.center_stage_toggled.connect(self._on_center_stage_toggled)
        self._control_panel.smoothing_changed.connect(self._on_smoothing_changed)
        self._control_panel.zoom_min_changed.connect(self._on_zoom_changed)
        self._control_panel.zoom_max_changed.connect(self._on_zoom_changed)
        self._control_panel.face_boxes_toggled.connect(self._preview.set_show_face_boxes)
        self._control_panel.crop_overlay_toggled.connect(self._preview.set_show_crop_overlay)
        self._control_panel.virtual_camera_toggled.connect(self._on_virtual_camera_toggled)
    
    def _initialize_camera(self) -> None:
        """Initialize camera and enumerate devices."""
        # Enumerate cameras
        cameras = CameraCapture.enumerate_cameras()
        self._control_panel.set_cameras(cameras)
        
        if cameras:
            # Start first camera
            self._camera.start()
    
    @Slot(np.ndarray)
    def _on_frame_ready(self, frame: np.ndarray) -> None:
        """Process and display a new frame - OPTIMIZED for minimal latency."""
        if self._is_processing:
            return
        
        self._is_processing = True
        self._frame_count += 1
        
        try:
            # Run face detection (handles its own frame skipping)
            detection = self._detector.detect(frame)
            
            # Update Center Stage
            crop = self._center_stage.update(detection)
            
            # Apply crop if Center Stage is enabled
            if self._center_stage.config.enabled:
                processed_frame = self._center_stage.apply_crop(frame, crop)
            else:
                processed_frame = frame
            
            # PRIORITY: Send to virtual camera FIRST (lowest latency path)
            if self._virtual_camera.is_running:
                self._virtual_camera.send_frame(processed_frame)
            
            # Update preview (every frame for smooth display)
            self._preview.update_frame(processed_frame)
            
            # Update UI elements only every 5 frames (reduces overhead)
            if self._frame_count % 5 == 0:
                # Update overlays
                if detection.has_faces:
                    boxes = [(f.x, f.y, f.width, f.height) for f in detection.faces]
                    self._preview.set_face_boxes(boxes)
                else:
                    self._preview.set_face_boxes([])
                
                self._preview.set_crop_region(
                    (crop.x, crop.y, crop.width, crop.height) 
                    if self._center_stage.config.enabled else None
                )
                
                # Update status labels
                self._face_label.setText(f"👤 {detection.face_count} Face{'s' if detection.face_count != 1 else ''}")
                self._tracking_label.setText(
                    "🎯 Tracking" if self._center_stage.is_tracking else "🎯 Idle"
                )
                self._control_panel.set_tracking_active(self._center_stage.is_tracking)
                
                # Update FPS
                fps = self._fps_counter.tick()
                self._preview.set_fps(fps)
            
        finally:
            self._is_processing = False
    
    @Slot(CameraState)
    def _on_camera_state_changed(self, state: CameraState) -> None:
        """Handle camera state changes."""
        connected = state == CameraState.CONNECTED
        self._control_panel.set_camera_connected(connected)
    
    @Slot(float)
    def _on_fps_updated(self, fps: float) -> None:
        """Update FPS display."""
        self._fps_label.setText(f"⚡ {fps:.0f} FPS")
    
    @Slot(int)
    def _on_camera_changed(self, index: int) -> None:
        """Handle camera selection change."""
        self._camera.set_camera(index)
        self._config.app.camera_index = index
    
    @Slot(bool)
    def _on_center_stage_toggled(self, enabled: bool) -> None:
        """Handle Center Stage toggle."""
        self._center_stage.set_enabled(enabled)
        self._config.app.center_stage_enabled = enabled
    
    @Slot(int)
    def _on_smoothing_changed(self, value: int) -> None:
        """Handle smoothing slider change."""
        smoothing = value * 0.02  # Map 1-10 to 0.02-0.2
        self._center_stage.set_smoothing(smoothing)
        self._config.app.smoothing = smoothing
    
    @Slot()
    def _on_zoom_changed(self) -> None:
        """Handle zoom range change."""
        min_zoom, max_zoom = self._control_panel.get_zoom_range()
        self._center_stage.set_zoom_range(min_zoom, max_zoom)
        self._config.app.min_zoom = min_zoom
        self._config.app.max_zoom = max_zoom
    
    @Slot(bool)
    def _on_virtual_camera_toggled(self, enabled: bool) -> None:
        """Handle virtual camera toggle."""
        if enabled:
            if not VirtualCameraOutput.is_available():
                QMessageBox.warning(
                    self,
                    "Virtual Camera Not Available",
                    "pyvirtualcam is not installed.\n\n"
                    "Please install OBS Virtual Camera first:\n"
                    "1. Download OBS Studio from obsproject.com\n"
                    "2. Install and run OBS\n"
                    "3. Go to Tools > VirtualCam\n"
                    "4. Click 'Start'\n\n"
                    "Then restart Center Stage."
                )
                self._control_panel.set_virtual_camera_active(False)
                return
            
            success = self._virtual_camera.start()
            if success:
                self._vcam_label.setText("📹 Virtual Camera: ON")
                self._control_panel.set_virtual_camera_active(True)
            else:
                QMessageBox.warning(
                    self,
                    "Virtual Camera Error",
                    "Failed to start virtual camera.\n\n"
                    "Make sure OBS Virtual Camera is installed and running:\n"
                    "1. Open OBS Studio\n"
                    "2. Go to Tools > VirtualCam\n"
                    "3. Click 'Start'\n\n"
                    "Then try again."
                )
                self._control_panel.set_virtual_camera_active(False)
        else:
            self._virtual_camera.stop()
            self._vcam_label.setText("📹 Virtual Camera: Off")
            self._control_panel.set_virtual_camera_active(False)
    
    def _toggle_maximize(self) -> None:
        """Toggle window maximize state."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close."""
        # Save window position
        self._config.app.window_x = self.x()
        self._config.app.window_y = self.y()
        self._config.app.window_width = self.width()
        self._config.app.window_height = self.height()
        self._config.save()
        
        # Stop virtual camera
        self._virtual_camera.stop()
        
        # Stop camera
        self._camera.stop()
        
        event.accept()
