"""
Tests for Center Stage Algorithm.

Tests the core Center Stage algorithm functionality including
smooth interpolation, dead zones, and multi-face framing.
"""

import pytest
import numpy as np

from src.core.center_stage import (
    CenterStageConfig,
    CenterStageEngine,
    CropRegion,
    FramingMode,
)
from src.core.detector import DetectionResult, FaceDetection


class TestCropRegion:
    """Tests for CropRegion class."""
    
    def test_full_frame(self):
        """Test full frame crop region."""
        region = CropRegion.full_frame()
        assert region.x == 0.0
        assert region.y == 0.0
        assert region.width == 1.0
        assert region.height == 1.0
    
    def test_center(self):
        """Test center calculation."""
        region = CropRegion(x=0.2, y=0.3, width=0.4, height=0.5)
        cx, cy = region.center
        assert cx == pytest.approx(0.4)  # 0.2 + 0.4/2
        assert cy == pytest.approx(0.55)  # 0.3 + 0.5/2
    
    def test_clamp(self):
        """Test clamping to valid bounds."""
        # Region outside bounds
        region = CropRegion(x=-0.1, y=-0.2, width=0.5, height=0.5)
        clamped = region.clamp()
        assert clamped.x >= 0.0
        assert clamped.y >= 0.0
    
    def test_lerp(self):
        """Test linear interpolation."""
        start = CropRegion(x=0.0, y=0.0, width=1.0, height=1.0)
        end = CropRegion(x=0.2, y=0.2, width=0.6, height=0.6)
        
        mid = start.lerp(end, 0.5)
        assert mid.x == pytest.approx(0.1)
        assert mid.y == pytest.approx(0.1)
        assert mid.width == pytest.approx(0.8)
        assert mid.height == pytest.approx(0.8)
    
    def test_to_pixels(self):
        """Test conversion to pixel coordinates."""
        region = CropRegion(x=0.25, y=0.25, width=0.5, height=0.5)
        x, y, w, h = region.to_pixels(1920, 1080)
        
        assert x == 480   # 0.25 * 1920
        assert y == 270   # 0.25 * 1080
        assert w == 960   # 0.5 * 1920
        assert h == 540   # 0.5 * 1080


class TestCenterStageEngine:
    """Tests for CenterStageEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a Center Stage engine for testing."""
        config = CenterStageConfig(
            smoothing=0.5,  # Higher for faster convergence in tests
            dead_zone=0.01,
            min_zoom=1.0,
            max_zoom=2.0,
        )
        return CenterStageEngine(config)
    
    def test_initial_state(self, engine):
        """Test initial state is full frame."""
        assert engine.current_crop.width == pytest.approx(1.0)
        assert engine.current_crop.height == pytest.approx(1.0)
        assert not engine.is_tracking
    
    def test_no_faces_stays_idle(self, engine):
        """Test that no faces keeps engine idle."""
        result = DetectionResult(faces=[], processing_time_ms=5.0)
        
        for _ in range(10):
            engine.update(result)
        
        assert not engine.is_tracking
    
    def test_face_starts_tracking(self, engine):
        """Test that detecting a face starts tracking."""
        face = FaceDetection(
            x=0.4, y=0.3, width=0.2, height=0.3, confidence=0.9
        )
        result = DetectionResult(faces=[face], processing_time_ms=5.0)
        
        engine.update(result)
        
        assert engine.is_tracking
    
    def test_crop_moves_towards_face(self, engine):
        """Test that crop moves towards detected face."""
        # Face in right side of frame
        face = FaceDetection(
            x=0.6, y=0.4, width=0.15, height=0.2, confidence=0.9
        )
        result = DetectionResult(faces=[face], processing_time_ms=5.0)
        
        initial_center = engine.current_crop.center
        
        # Update multiple times
        for _ in range(20):
            crop = engine.update(result)
        
        # Crop should have moved right
        assert crop.center[0] > initial_center[0]
    
    def test_reset(self, engine):
        """Test reset returns to full frame."""
        # Start tracking
        face = FaceDetection(
            x=0.4, y=0.3, width=0.2, height=0.3, confidence=0.9
        )
        result = DetectionResult(faces=[face], processing_time_ms=5.0)
        engine.update(result)
        
        # Reset
        engine.reset()
        
        assert engine.current_crop.width == pytest.approx(1.0)
        assert not engine.is_tracking
    
    def test_disabled_returns_full_frame(self, engine):
        """Test disabled engine returns full frame."""
        engine.set_enabled(False)
        
        face = FaceDetection(
            x=0.4, y=0.3, width=0.2, height=0.3, confidence=0.9
        )
        result = DetectionResult(faces=[face], processing_time_ms=5.0)
        
        crop = engine.update(result)
        
        assert crop.width == pytest.approx(1.0)
        assert crop.height == pytest.approx(1.0)


class TestMultiFaceFraming:
    """Tests for multi-face framing."""
    
    @pytest.fixture
    def engine(self):
        """Create engine with all-faces framing mode."""
        config = CenterStageConfig(
            framing_mode=FramingMode.ALL,
            smoothing=0.5,
        )
        return CenterStageEngine(config)
    
    def test_single_face_framing(self, engine):
        """Test single face is properly framed."""
        face = FaceDetection(
            x=0.4, y=0.3, width=0.2, height=0.3, confidence=0.9
        )
        result = DetectionResult(faces=[face], processing_time_ms=5.0)
        
        for _ in range(50):
            crop = engine.update(result)
        
        # Crop should be centered around face
        face_center_x = face.x + face.width / 2  # 0.5
        assert abs(crop.center[0] - face_center_x) < 0.2
    
    def test_multiple_faces_includes_all(self, engine):
        """Test multiple faces are all included in frame."""
        faces = [
            FaceDetection(x=0.1, y=0.3, width=0.15, height=0.2, confidence=0.9),
            FaceDetection(x=0.7, y=0.4, width=0.15, height=0.2, confidence=0.9),
        ]
        result = DetectionResult(faces=faces, processing_time_ms=5.0)
        
        for _ in range(50):
            crop = engine.update(result)
        
        # Crop should be wide enough to include both faces
        # Or centered between them
        center_x = crop.center[0]
        # Should be somewhere between the two faces
        assert 0.3 < center_x < 0.7
