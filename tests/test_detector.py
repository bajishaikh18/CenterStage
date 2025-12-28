"""
Tests for Face Detector Module.

Tests face detection functionality with mock data.
"""

import pytest
import numpy as np

from src.core.detector import FaceDetector, FaceDetection, DetectionResult


class TestFaceDetection:
    """Tests for FaceDetection class."""
    
    def test_center_calculation(self):
        """Test center point calculation."""
        face = FaceDetection(x=0.2, y=0.3, width=0.4, height=0.5, confidence=0.9)
        cx, cy = face.center
        
        assert cx == pytest.approx(0.4)  # 0.2 + 0.4/2
        assert cy == pytest.approx(0.55)  # 0.3 + 0.5/2
    
    def test_area_calculation(self):
        """Test area calculation."""
        face = FaceDetection(x=0.0, y=0.0, width=0.5, height=0.4, confidence=0.9)
        assert face.area == pytest.approx(0.2)  # 0.5 * 0.4
    
    def test_to_pixels(self):
        """Test conversion to pixel coordinates."""
        face = FaceDetection(x=0.25, y=0.5, width=0.5, height=0.25, confidence=0.9)
        x, y, w, h = face.to_pixels(1920, 1080)
        
        assert x == 480   # 0.25 * 1920
        assert y == 540   # 0.5 * 1080
        assert w == 960   # 0.5 * 1920
        assert h == 270   # 0.25 * 1080


class TestDetectionResult:
    """Tests for DetectionResult class."""
    
    def test_no_faces(self):
        """Test detection with no faces."""
        result = DetectionResult(faces=[], processing_time_ms=5.0)
        
        assert not result.has_faces
        assert result.face_count == 0
        assert result.primary_face is None
        assert result.get_bounding_box() is None
    
    def test_single_face(self):
        """Test detection with single face."""
        face = FaceDetection(x=0.3, y=0.2, width=0.2, height=0.3, confidence=0.9)
        result = DetectionResult(faces=[face], processing_time_ms=5.0)
        
        assert result.has_faces
        assert result.face_count == 1
        assert result.primary_face == face
    
    def test_primary_face_is_largest(self):
        """Test that primary face is the largest by area."""
        small_face = FaceDetection(x=0.1, y=0.1, width=0.1, height=0.1, confidence=0.9)
        large_face = FaceDetection(x=0.4, y=0.4, width=0.3, height=0.4, confidence=0.9)
        
        result = DetectionResult(
            faces=[small_face, large_face],
            processing_time_ms=5.0
        )
        
        assert result.primary_face == large_face
    
    def test_bounding_box_multiple_faces(self):
        """Test bounding box encompasses all faces."""
        face1 = FaceDetection(x=0.1, y=0.2, width=0.1, height=0.1, confidence=0.9)
        face2 = FaceDetection(x=0.6, y=0.5, width=0.2, height=0.2, confidence=0.9)
        
        result = DetectionResult(faces=[face1, face2], processing_time_ms=5.0)
        
        bbox = result.get_bounding_box()
        assert bbox is not None
        
        x, y, w, h = bbox
        assert x == pytest.approx(0.1)   # min x
        assert y == pytest.approx(0.2)   # min y
        assert x + w == pytest.approx(0.8)  # max x (0.6 + 0.2)
        assert y + h == pytest.approx(0.7)  # max y (0.5 + 0.2)


class TestFaceDetector:
    """Tests for FaceDetector class.
    
    Note: These tests use a mock approach since actual MediaPipe
    detection requires real images.
    """
    
    def test_init(self):
        """Test detector initialization."""
        detector = FaceDetector(min_confidence=0.7, max_faces=3)
        assert detector.min_confidence == 0.7
    
    def test_confidence_setter(self):
        """Test confidence threshold update."""
        detector = FaceDetector(min_confidence=0.5)
        detector.min_confidence = 0.8
        assert detector.min_confidence == 0.8
    
    def test_confidence_clamped(self):
        """Test confidence is clamped to valid range."""
        detector = FaceDetector(min_confidence=0.5)
        detector.min_confidence = 1.5  # Out of range
        assert detector.min_confidence == 1.0
        
        detector.min_confidence = -0.5  # Out of range
        assert detector.min_confidence == 0.0
    
    def test_detect_returns_result(self):
        """Test detection returns a DetectionResult."""
        detector = FaceDetector()
        
        # Create a blank test image
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        result = detector.detect(frame)
        
        assert isinstance(result, DetectionResult)
        assert result.processing_time_ms >= 0
