"""Frame smoothing and pose transition detection for video analysis."""
from collections import deque
from typing import Optional, Dict, List, Tuple
import time


class PoseSmoother:
    """Sliding window smoother for pose detection results.
    
    Uses majority voting over a window of recent detections
    to reduce flickering and provide stable pose identification.
    """
    
    def __init__(self, window_size: int = 5, confidence_threshold: float = 0.6):
        """
        Args:
            window_size: Number of recent frames to consider
            confidence_threshold: Minimum confidence to accept a detection
        """
        self.window_size = window_size
        self.confidence_threshold = confidence_threshold
        self.history: deque = deque(maxlen=window_size)
        self.current_pose: Optional[str] = None
        self.pose_start_time: float = 0
        self.transitions: List[Dict] = []
    
    def update(self, pose_id: str, confidence: float, timestamp: float) -> Optional[str]:
        """Update with new detection and return smoothed pose.
        
        Args:
            pose_id: Detected pose ID
            confidence: Detection confidence (0-1)
            timestamp: Frame timestamp in seconds
            
        Returns:
            Smoothed pose ID or None if uncertain
        """
        self.history.append({
            'pose': pose_id,
            'confidence': confidence,
            'timestamp': timestamp
        })
        
        if len(self.history) < 3:
            return None
        
        # Count votes for each pose
        votes = {}
        total_weight = 0
        
        for i, entry in enumerate(self.history):
            # More recent frames have higher weight
            weight = (i + 1) / len(self.history)
            # Only count high-confidence detections
            if entry['confidence'] >= self.confidence_threshold:
                pose = entry['pose']
                votes[pose] = votes.get(pose, 0) + weight
                total_weight += weight
        
        if not votes:
            return self.current_pose
        
        # Get winner
        best_pose = max(votes, key=votes.get)
        best_ratio = votes[best_pose] / total_weight if total_weight > 0 else 0
        
        # Require majority (50%+) to change pose
        if best_ratio >= 0.5:
            if best_pose != self.current_pose:
                # Record transition
                if self.current_pose is not None:
                    self.transitions.append({
                        'from': self.current_pose,
                        'to': best_pose,
                        'timestamp': timestamp,
                        'duration': timestamp - self.pose_start_time
                    })
                self.current_pose = best_pose
                self.pose_start_time = timestamp
        
        return self.current_pose
    
    def get_transitions(self) -> List[Dict]:
        """Get all recorded pose transitions."""
        return self.transitions
    
    def get_current_sequence(self) -> List[str]:
        """Get the sequence of unique poses in order."""
        if not self.transitions:
            return [self.current_pose] if self.current_pose else []
        
        sequence = [self.transitions[0]['from']]
        for t in self.transitions:
            sequence.append(t['to'])
        return sequence
    
    def reset(self):
        """Reset the smoother state."""
        self.history.clear()
        self.current_pose = None
        self.pose_start_time = 0
        self.transitions.clear()


class PoseTransitionDetector:
    """Detect pose transitions in a sequence of detections."""
    
    def __init__(self, min_hold_frames: int = 3, change_threshold: float = 0.7):
        """
        Args:
            min_hold_frames: Minimum frames to hold a pose before allowing change
            change_threshold: Confidence threshold for accepting a change
        """
        self.min_hold_frames = min_hold_frames
        self.change_threshold = change_threshold
        self.current_pose = None
        self.hold_count = 0
        self.pending_pose = None
        self.pending_count = 0
        self.transitions = []
    
    def update(self, pose_id: str, confidence: float) -> Optional[str]:
        """Update with new detection.
        
        Returns:
            Current stable pose ID
        """
        if pose_id == self.current_pose:
            self.hold_count += 1
            self.pending_pose = None
            self.pending_count = 0
            return self.current_pose
        
        if pose_id == self.pending_pose:
            self.pending_count += 1
        else:
            self.pending_pose = pose_id
            self.pending_count = 1
        
        # Require minimum hold frames and sufficient pending count
        if (self.hold_count >= self.min_hold_frames and 
            self.pending_count >= self.min_hold_frames and
            confidence >= self.change_threshold):
            
            old_pose = self.current_pose
            self.current_pose = self.pending_pose
            self.hold_count = 0
            self.pending_pose = None
            self.pending_count = 0
            
            if old_pose:
                self.transitions.append({
                    'from': old_pose,
                    'to': self.current_pose
                })
        
        return self.current_pose
    
    def get_transitions(self) -> List[Dict]:
        """Get all detected transitions."""
        return self.transitions
    
    def reset(self):
        """Reset detector state."""
        self.current_pose = None
        self.hold_count = 0
        self.pending_pose = None
        self.pending_count = 0
        self.transitions.clear()


def analyze_with_smoothing(results: List[Dict], window_size: int = 5) -> Dict:
    """Analyze detection results with smoothing.
    
    Args:
        results: List of detection results with 'time', 'pose', 'score', 'confidence'
        window_size: Smoothing window size
        
    Returns:
        Dictionary with smoothed results and transitions
    """
    smoother = PoseSmoother(window_size=window_size)
    detector = PoseTransitionDetector(min_hold_frames=3)
    
    smoothed = []
    for r in results:
        pose = smoother.update(r['pose'], r['confidence'], r['time'])
        stable_pose = detector.update(r['pose'], r['confidence'])
        
        smoothed.append({
            'time': r['time'],
            'raw_pose': r['pose'],
            'smoothed_pose': pose,
            'stable_pose': stable_pose,
            'confidence': r['confidence']
        })
    
    return {
        'smoothed_results': smoothed,
        'transitions': smoother.get_transitions(),
        'sequence': smoother.get_current_sequence(),
        'stable_transitions': detector.get_transitions()
    }
