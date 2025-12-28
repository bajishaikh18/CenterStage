"""
Face Tracker Module for Center Stage Camera.

Provides object tracking to maintain face identity between detection frames,
reducing jitter and improving performance by running detection less frequently.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np


class TrackerType(Enum):
    """Available OpenCV tracker types."""
    CSRT = "csrt"      # Accurate but slower
    KCF = "kcf"        # Fast but less accurate
    MOSSE = "mosse"    # Fastest, least accurate


@dataclass 
class TrackedFace:
    """A face being tracked across frames."""
    
    tracking_id: int
    bbox: tuple[int, int, int, int]  # x, y, w, h in pixels
    confidence: float
    frames_since_detection: int = 0
    is_lost: bool = False
    
    @property
    def center(self) -> tuple[int, int]:
        """Center point of tracked face."""
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)
    
    def to_normalized(self, frame_width: int, frame_height: int) -> tuple[float, float, float, float]:
        """Convert to normalized coordinates (0-1)."""
        x, y, w, h = self.bbox
        return (
            x / frame_width,
            y / frame_height,
            w / frame_width,
            h / frame_height,
        )


class FaceTracker:
    """
    Multi-face tracker using OpenCV tracking algorithms.
    
    Maintains identity of faces between detection frames, allowing
    for smoother tracking and reduced CPU usage.
    """
    
    def __init__(
        self,
        tracker_type: TrackerType = TrackerType.KCF,
        max_frames_without_detection: int = 30,
    ):
        """
        Initialize the face tracker.
        
        Args:
            tracker_type: OpenCV tracker algorithm to use
            max_frames_without_detection: Frames before a track is considered lost
        """
        self._tracker_type = tracker_type
        self._max_frames_lost = max_frames_without_detection
        
        self._trackers: dict[int, cv2.Tracker] = {}
        self._tracked_faces: dict[int, TrackedFace] = {}
        self._next_id = 0
    
    def _create_tracker(self) -> cv2.Tracker:
        """Create a new OpenCV tracker instance."""
        if self._tracker_type == TrackerType.CSRT:
            return cv2.TrackerCSRT.create()
        elif self._tracker_type == TrackerType.KCF:
            return cv2.TrackerKCF.create()
        elif self._tracker_type == TrackerType.MOSSE:
            return cv2.legacy.TrackerMOSSE.create()
        else:
            return cv2.TrackerKCF.create()
    
    def init_tracks(
        self,
        frame: np.ndarray,
        detections: list[tuple[int, int, int, int]],
    ) -> list[TrackedFace]:
        """
        Initialize tracking for detected faces.
        
        Args:
            frame: Current frame (RGB)
            detections: List of (x, y, w, h) bounding boxes in pixels
            
        Returns:
            List of tracked faces
        """
        # Clear existing tracks
        self._trackers.clear()
        self._tracked_faces.clear()
        
        # Convert RGB to BGR for OpenCV
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        for bbox in detections:
            tracking_id = self._next_id
            self._next_id += 1
            
            # Create and initialize tracker
            tracker = self._create_tracker()
            tracker.init(frame_bgr, bbox)
            
            self._trackers[tracking_id] = tracker
            self._tracked_faces[tracking_id] = TrackedFace(
                tracking_id=tracking_id,
                bbox=bbox,
                confidence=1.0,
            )
        
        return list(self._tracked_faces.values())
    
    def update(self, frame: np.ndarray) -> list[TrackedFace]:
        """
        Update all tracks with new frame.
        
        Args:
            frame: Current frame (RGB)
            
        Returns:
            List of currently tracked faces
        """
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        lost_ids = []
        
        for tracking_id, tracker in self._trackers.items():
            success, bbox = tracker.update(frame_bgr)
            
            tracked = self._tracked_faces[tracking_id]
            tracked.frames_since_detection += 1
            
            if success:
                tracked.bbox = tuple(int(v) for v in bbox)
                tracked.confidence = max(0.5, 1.0 - tracked.frames_since_detection * 0.02)
            else:
                tracked.is_lost = True
                lost_ids.append(tracking_id)
            
            # Check if track has been lost too long
            if tracked.frames_since_detection > self._max_frames_lost:
                tracked.is_lost = True
                lost_ids.append(tracking_id)
        
        # Remove lost tracks
        for tid in set(lost_ids):
            self._trackers.pop(tid, None)
            self._tracked_faces.pop(tid, None)
        
        return list(self._tracked_faces.values())
    
    def refresh_tracks(
        self,
        frame: np.ndarray,
        detections: list[tuple[int, int, int, int]],
        iou_threshold: float = 0.3,
    ) -> list[TrackedFace]:
        """
        Refresh existing tracks with new detections.
        
        Matches new detections to existing tracks using IoU,
        updates matched tracks, and creates new tracks for unmatched detections.
        
        Args:
            frame: Current frame (RGB)
            detections: New detection bounding boxes
            iou_threshold: Minimum IoU to consider a match
            
        Returns:
            Updated list of tracked faces
        """
        if not detections:
            return list(self._tracked_faces.values())
        
        if not self._tracked_faces:
            return self.init_tracks(frame, detections)
        
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Match detections to existing tracks
        matched_tracks = set()
        matched_detections = set()
        
        for i, det_bbox in enumerate(detections):
            best_iou = 0.0
            best_track_id = None
            
            for tracking_id, tracked in self._tracked_faces.items():
                if tracking_id in matched_tracks:
                    continue
                
                iou = self._calculate_iou(tracked.bbox, det_bbox)
                if iou > best_iou and iou >= iou_threshold:
                    best_iou = iou
                    best_track_id = tracking_id
            
            if best_track_id is not None:
                # Update existing track
                matched_tracks.add(best_track_id)
                matched_detections.add(i)
                
                # Reinitialize tracker with new detection
                tracker = self._create_tracker()
                tracker.init(frame_bgr, det_bbox)
                self._trackers[best_track_id] = tracker
                
                self._tracked_faces[best_track_id].bbox = det_bbox
                self._tracked_faces[best_track_id].confidence = 1.0
                self._tracked_faces[best_track_id].frames_since_detection = 0
        
        # Create new tracks for unmatched detections
        for i, det_bbox in enumerate(detections):
            if i not in matched_detections:
                tracking_id = self._next_id
                self._next_id += 1
                
                tracker = self._create_tracker()
                tracker.init(frame_bgr, det_bbox)
                
                self._trackers[tracking_id] = tracker
                self._tracked_faces[tracking_id] = TrackedFace(
                    tracking_id=tracking_id,
                    bbox=det_bbox,
                    confidence=1.0,
                )
        
        return list(self._tracked_faces.values())
    
    @staticmethod
    def _calculate_iou(
        bbox1: tuple[int, int, int, int],
        bbox2: tuple[int, int, int, int],
    ) -> float:
        """Calculate Intersection over Union between two bounding boxes."""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        inter_x1 = max(x1, x2)
        inter_y1 = max(y1, y2)
        inter_x2 = min(x1 + w1, x2 + w2)
        inter_y2 = min(y1 + h1, y2 + h2)
        
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union_area = area1 + area2 - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    @property
    def active_tracks(self) -> int:
        """Number of currently active tracks."""
        return len(self._tracked_faces)
    
    def clear(self) -> None:
        """Clear all tracks."""
        self._trackers.clear()
        self._tracked_faces.clear()
