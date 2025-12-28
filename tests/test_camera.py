"""
Tests for Camera Capture Module.

Tests camera enumeration and capture functionality.
"""

import pytest

from src.core.camera import CameraCapture, CameraInfo, CameraState


class TestCameraInfo:
    """Tests for CameraInfo class."""
    
    def test_string_representation(self):
        """Test string representation."""
        info = CameraInfo(index=0, name="Test Camera", resolution=(1920, 1080))
        assert str(info) == "Test Camera (1920x1080)"
    
    def test_attributes(self):
        """Test attribute access."""
        info = CameraInfo(index=1, name="Webcam", resolution=(1280, 720))
        assert info.index == 1
        assert info.name == "Webcam"
        assert info.resolution == (1280, 720)


class TestCameraCapture:
    """Tests for CameraCapture class.
    
    Note: Actual camera tests require hardware and are skipped
    if no camera is available.
    """
    
    def test_init(self):
        """Test camera initialization."""
        camera = CameraCapture(camera_index=0, target_fps=30)
        assert camera.state == CameraState.DISCONNECTED
        assert not camera.is_running
    
    def test_resolution_property(self):
        """Test resolution property."""
        camera = CameraCapture(resolution=(1920, 1080))
        assert camera.resolution == (1920, 1080)
    
    def test_enumerate_cameras(self):
        """Test camera enumeration."""
        # This should always work, even if no camera returns empty list
        cameras = CameraCapture.enumerate_cameras(max_cameras=5)
        assert isinstance(cameras, list)
        
        for cam in cameras:
            assert isinstance(cam, CameraInfo)
            assert cam.index >= 0
    
    def test_current_frame_none_before_start(self):
        """Test that current_frame is None before starting."""
        camera = CameraCapture()
        assert camera.current_frame is None
    
    def test_set_camera(self):
        """Test camera switching."""
        camera = CameraCapture(camera_index=0)
        result = camera.set_camera(1)
        
        # Should return True even if camera doesn't exist
        # (actual connection happens on start)
        assert result is True
    
    def test_set_resolution(self):
        """Test resolution change."""
        camera = CameraCapture(resolution=(640, 480))
        result = camera.set_resolution(1280, 720)
        
        assert result is True
        assert camera.resolution == (1280, 720)


class TestCameraState:
    """Tests for CameraState enum."""
    
    def test_states_exist(self):
        """Test all expected states exist."""
        assert CameraState.DISCONNECTED.value == "disconnected"
        assert CameraState.CONNECTING.value == "connecting"
        assert CameraState.CONNECTED.value == "connected"
        assert CameraState.ERROR.value == "error"
