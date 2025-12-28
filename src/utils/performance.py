"""
Performance Monitoring for Center Stage Camera.

Provides FPS counting, performance profiling, and metrics collection.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot."""
    
    fps: float
    frame_time_ms: float
    detection_time_ms: float
    processing_time_ms: float
    render_time_ms: float
    
    @property
    def total_time_ms(self) -> float:
        """Total time per frame."""
        return self.detection_time_ms + self.processing_time_ms + self.render_time_ms


class FPSCounter:
    """
    Accurate FPS counter with rolling average.
    
    Uses a deque to maintain a rolling window of frame times,
    providing a smooth FPS reading.
    """
    
    def __init__(self, window_size: int = 60):
        """
        Initialize FPS counter.
        
        Args:
            window_size: Number of frames to average over
        """
        self._window_size = window_size
        self._frame_times: deque[float] = deque(maxlen=window_size)
        self._last_time: Optional[float] = None
    
    def tick(self) -> float:
        """
        Record a frame and return current FPS.
        
        Call this once per frame to update the FPS counter.
        
        Returns:
            Current FPS (rolling average)
        """
        current_time = time.perf_counter()
        
        if self._last_time is not None:
            frame_time = current_time - self._last_time
            self._frame_times.append(frame_time)
        
        self._last_time = current_time
        
        return self.fps
    
    @property
    def fps(self) -> float:
        """Current FPS (rolling average)."""
        if not self._frame_times:
            return 0.0
        
        avg_frame_time = sum(self._frame_times) / len(self._frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
    
    @property
    def frame_time_ms(self) -> float:
        """Average frame time in milliseconds."""
        if not self._frame_times:
            return 0.0
        return (sum(self._frame_times) / len(self._frame_times)) * 1000
    
    def reset(self) -> None:
        """Reset the FPS counter."""
        self._frame_times.clear()
        self._last_time = None


class PerformanceProfiler:
    """
    Performance profiler for timing code sections.
    
    Usage:
        profiler = PerformanceProfiler()
        
        with profiler.measure("detection"):
            # Detection code...
        
        with profiler.measure("processing"):
            # Processing code...
        
        metrics = profiler.get_metrics()
    """
    
    def __init__(self, window_size: int = 30):
        """
        Initialize profiler.
        
        Args:
            window_size: Number of samples to average
        """
        self._window_size = window_size
        self._timings: dict[str, deque[float]] = {}
        self._current_section: Optional[str] = None
        self._section_start: float = 0.0
        self._fps_counter = FPSCounter(window_size)
    
    class _TimingContext:
        """Context manager for timing a section."""
        
        def __init__(self, profiler: "PerformanceProfiler", section: str):
            self._profiler = profiler
            self._section = section
            self._start_time = 0.0
        
        def __enter__(self):
            self._start_time = time.perf_counter()
            return self
        
        def __exit__(self, *args):
            elapsed = (time.perf_counter() - self._start_time) * 1000
            self._profiler._record(self._section, elapsed)
    
    def measure(self, section: str) -> _TimingContext:
        """
        Create a timing context for a section.
        
        Args:
            section: Name of the section to time
            
        Returns:
            Context manager for timing
        """
        return self._TimingContext(self, section)
    
    def _record(self, section: str, time_ms: float) -> None:
        """Record a timing sample."""
        if section not in self._timings:
            self._timings[section] = deque(maxlen=self._window_size)
        self._timings[section].append(time_ms)
    
    def tick_frame(self) -> None:
        """Mark a frame boundary for FPS counting."""
        self._fps_counter.tick()
    
    def get_average(self, section: str) -> float:
        """Get average time for a section in milliseconds."""
        times = self._timings.get(section)
        if not times:
            return 0.0
        return sum(times) / len(times)
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return PerformanceMetrics(
            fps=self._fps_counter.fps,
            frame_time_ms=self._fps_counter.frame_time_ms,
            detection_time_ms=self.get_average("detection"),
            processing_time_ms=self.get_average("processing"),
            render_time_ms=self.get_average("render"),
        )
    
    def reset(self) -> None:
        """Reset all profiling data."""
        self._timings.clear()
        self._fps_counter.reset()
    
    def get_summary(self) -> str:
        """Get a formatted summary of performance."""
        metrics = self.get_metrics()
        return (
            f"FPS: {metrics.fps:.1f} | "
            f"Frame: {metrics.frame_time_ms:.1f}ms | "
            f"Det: {metrics.detection_time_ms:.1f}ms | "
            f"Proc: {metrics.processing_time_ms:.1f}ms | "
            f"Render: {metrics.render_time_ms:.1f}ms"
        )
