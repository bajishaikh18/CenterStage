"""
Configuration Management for Center Stage Camera.

Provides persistent configuration storage with JSON backend,
default values, and type-safe access.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class AppConfig:
    """Application configuration."""
    
    # Camera settings
    camera_index: int = 0
    resolution_width: int = 1280
    resolution_height: int = 720
    target_fps: int = 30
    
    # Center Stage settings
    center_stage_enabled: bool = True
    smoothing: float = 0.08
    dead_zone: float = 0.015
    min_zoom: float = 1.0
    max_zoom: float = 2.5
    face_padding: float = 0.35
    framing_mode: str = "all"  # "single", "all", "closest"
    
    # Face detection settings
    detection_confidence: float = 0.5
    max_faces: int = 5
    
    # UI settings
    theme: str = "dark"  # "dark" or "light"
    always_on_top: bool = False
    show_fps: bool = True
    show_face_boxes: bool = False
    show_crop_overlay: bool = False
    
    # Virtual camera
    virtual_camera_enabled: bool = False
    
    # Window position (None = center)
    window_x: Optional[int] = None
    window_y: Optional[int] = None
    window_width: int = 1280
    window_height: int = 800
    
    @property
    def resolution(self) -> tuple[int, int]:
        """Get resolution as tuple."""
        return (self.resolution_width, self.resolution_height)


class Config:
    """
    Configuration manager with persistent storage.
    
    Saves and loads configuration from a JSON file.
    """
    
    DEFAULT_CONFIG_PATH = Path.home() / ".centerstage" / "config.json"
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to config file (uses default if None)
        """
        self._path = config_path or self.DEFAULT_CONFIG_PATH
        self._config = AppConfig()
        self._load()
    
    @property
    def app(self) -> AppConfig:
        """Get application configuration."""
        return self._config
    
    def _load(self) -> None:
        """Load configuration from file."""
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                    # Update config with loaded values
                    for key, value in data.items():
                        if hasattr(self._config, key):
                            setattr(self._config, key, value)
            except (json.JSONDecodeError, IOError):
                # Use defaults if file is corrupted
                pass
    
    def save(self) -> None:
        """Save configuration to file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self._path, "w") as f:
            json.dump(asdict(self._config), f, indent=2)
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = AppConfig()
        self.save()
    
    def get(self, key: str, default=None):
        """Get a configuration value."""
        return getattr(self._config, key, default)
    
    def set(self, key: str, value) -> None:
        """Set a configuration value."""
        if hasattr(self._config, key):
            setattr(self._config, key, value)
