"""Vinyasa flow sequence detection and classification.

Detects common yoga sequences from a stream of pose detections:
- Sun Salutation A (Surya Namaskar A)
- Sun Salutation B (Surya Namaskar B)
- Warrior sequences
- Standing balance sequences
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import time
import numpy as np


class SequenceType(Enum):
    """Types of vinyasa sequences."""
    SUN_A = "sun_salutation_a"
    SUN_B = "sun_salutation_b"
    WARRIOR_FLOW = "warrior_flow"
    STANDING_BALANCE = "standing_balance"
    SEATED_SEQUENCE = "seated_sequence"
    BACKBEND_SEQUENCE = "backbend_sequence"
    UNKNOWN = "unknown"


@dataclass
class PoseTransition:
    """A transition between two poses."""
    from_pose: str
    to_pose: str
    timestamp: float
    confidence: float = 0.0


@dataclass
class SequenceMatch:
    """A detected sequence match."""
    sequence_type: SequenceType
    start_idx: int
    end_idx: int
    start_time: float
    end_time: float
    poses: List[str]
    score: float  # 0-100 match quality
    confidence: float


# ── Sequence Definitions ──────────────────────────────────────────────

SEQUENCES = {
    SequenceType.SUN_A: {
        "name": "拜日式A",
        "name_en": "Sun Salutation A",
        "poses": [
            "mountain",           # 山式 (Tadasana)
            "upward_salute",      # 手臂上举 (Urdhva Hastasana)
            "standing_forward_bend",  # 站立前屈 (Uttanasana)
            "half_forward_fold",  # 半前屈 (Ardha Uttanasana)
            "plank",              # 平板 (Phalakasana)
            "chaturanga",         # 四柱 (Chaturanga Dandasana)
            "upward_facing_dog",  # 上犬 (Urdhva Mukha Svanasana)
            "downward_facing_dog",       # 下犬 (Adho Mukha Svanasana)
            "standing_forward_bend",  # 站立前屈
            "mountain",           # 山式
        ],
        "min_poses": 5,
        "required_poses": ["plank", "downward_facing_dog"],
    },
    SequenceType.SUN_B: {
        "name": "拜日式B",
        "name_en": "Sun Salutation B",
        "poses": [
            "mountain",           # 山式
            "chair",              # 幻椅 (Utkatasana)
            "standing_forward_bend",  # 站立前屈
            "half_forward_fold",  # 半前屈
            "plank",              # 平板
            "chaturanga",         # 四柱
            "upward_facing_dog",  # 上犬
            "downward_facing_dog",    # 下犬
            "warrior1",           # 战士一 (Virabhadrasana I)
            "plank",              # 平板
            "chaturanga",         # 四柱
            "upward_facing_dog",  # 上犬
            "downward_facing_dog",    # 下犬
            "mountain",           # 山式
        ],
        "min_poses": 6,
        "required_poses": ["chair", "warrior1", "downward_facing_dog"],
    },
    SequenceType.WARRIOR_FLOW: {
        "name": "战士流动",
        "name_en": "Warrior Flow",
        "poses": [
            "low_lunge",          # 低弓步
            "warrior1",           # 战士一
            "warrior2",           # 战士二
            "side_angle",         # 侧角
            "reverse_warrior",    # 反战
            "triangle",           # 三角
        ],
        "min_poses": 3,
        "required_poses": ["warrior2"],
    },
    SequenceType.STANDING_BALANCE: {
        "name": "站立平衡序列",
        "name_en": "Standing Balance",
        "poses": [
            "mountain",           # 山式
            "tree",               # 树式
            "warrior3",           # 战士三
            "extended_hand_to_toe",  # 手抓大脚趾
            "natarajasana",       # 舞王
        ],
        "min_poses": 3,
        "required_poses": ["tree"],
    },
    SequenceType.SEATED_SEQUENCE: {
        "name": "坐姿序列",
        "name_en": "Seated Sequence",
        "poses": [
            "staff_pose",         # 手杖
            "paschimottanasana",  # 坐立前屈
            "boat",               # 船式
            "half_forward_fold",  # 半前屈
        ],
        "min_poses": 3,
        "required_poses": ["paschimottanasana"],
    },
    SequenceType.BACKBEND_SEQUENCE: {
        "name": "后弯序列",
        "name_en": "Backbend Sequence",
        "poses": [
            "bridge",             # 桥式
            "wheel",              # 轮式
            "camel",              # 骆驼
            "upward_facing_dog",  # 上犬
            "cobra",              # 眼镜蛇
        ],
        "min_poses": 3,
        "required_poses": [],
    },
}


# ── Pose Alias Mapping ────────────────────────────────────────────────

POSE_ALIASES = {
    # Common alternative names
    "upward_salute": ["urdhva_hastasana", "arms_up"],
    "standing_forward_bend": ["uttanasana", "forward_fold"],
    "half_forward_fold": ["ardha_uttanasana", "half_forward"],
    "upward_facing_dog": ["urdhva_mukha_svanasana", "up_dog", "upward_dog"],
    "downward_facing_dog": ["adhoh_mukha_svananasana", "down_dog", "downward_facing_dog"],
    "chaturanga": ["chaturanga_dandasana", "four_limbed_staff"],
    "wheel": ["urdhva_dhanurasana", "upward_bow"],
    "low_lunge": ["anjaneyasana", "crescent_lunge"],
    "reverse_warrior": ["viparita_virabhadrasana", "peaceful_warrior"],
    "extended_hand_to_toe": ["utthita_hasta_padangusthasana", "hand_to_big_toe"],
    "natarajasana": ["lord_of_the_dance", "dancer_pose"],
    "paschimottanasana": ["seated_forward_bend", "seated_forward_fold"],
    "mountain": ["tadasana"],
}


def normalize_pose(pose_id: str) -> str:
    """Normalize pose ID to standard form."""
    # Check direct match
    if pose_id in POSE_ALIASES or pose_id in {v for vals in POSE_ALIASES.values() for v in vals}:
        for standard, aliases in POSE_ALIASES.items():
            if pose_id == standard or pose_id in aliases:
                return standard
    return pose_id


# ── Sequence Detector ─────────────────────────────────────────────────

class SequenceDetector:
    """Detect yoga sequences from a stream of pose detections."""
    
    def __init__(self, window_size: int = 15, min_match_score: float = 50.0):
        """
        Args:
            window_size: Number of recent poses to consider
            min_match_score: Minimum score to consider a sequence match
        """
        self.window_size = window_size
        self.min_match_score = min_match_score
        self.history: List[Dict] = []
        self.current_sequence: Optional[SequenceMatch] = None
        self.detected_sequences: List[SequenceMatch] = []
    
    def update(self, pose_id: str, timestamp: float, confidence: float = 1.0) -> Optional[SequenceMatch]:
        """Add a new pose detection and check for sequences.
        
        Args:
            pose_id: Detected pose ID
            timestamp: Time in seconds
            confidence: Detection confidence (0-1)
            
        Returns:
            Detected sequence match, or None if no new sequence detected
        """
        normalized = normalize_pose(pose_id)
        
        self.history.append({
            "pose": normalized,
            "timestamp": timestamp,
            "confidence": confidence,
        })
        
        # Keep only recent history
        if len(self.history) > self.window_size * 2:
            self.history = self.history[-self.window_size * 2:]
        
        # Check for sequence matches
        match = self._find_best_match()
        
        if match and match.score >= self.min_match_score:
            if self.current_sequence is None or match.sequence_type != self.current_sequence.sequence_type:
                # New sequence detected
                self.current_sequence = match
                self.detected_sequences.append(match)
                return match
        
        return None
    
    def _find_best_match(self) -> Optional[SequenceMatch]:
        """Find the best matching sequence in recent history."""
        best_match = None
        
        for seq_type, seq_def in SEQUENCES.items():
            match = self._match_sequence(seq_type, seq_def)
            if match and (best_match is None or match.score > best_match.score):
                best_match = match
        
        return best_match
    
    def _match_sequence(self, seq_type: SequenceType, seq_def: Dict) -> Optional[SequenceMatch]:
        """Check if recent poses match a specific sequence."""
        recent_poses = [h["pose"] for h in self.history[-self.window_size:]]
        
        if len(recent_poses) < seq_def["min_poses"]:
            return None
        
        # Check required poses
        for required in seq_def["required_poses"]:
            if required not in recent_poses:
                return None
        
        # Calculate match score using longest common subsequence
        template = seq_def["poses"]
        lcs_len = self._lcs_length(recent_poses, template)
        
        # Score based on LCS length relative to template
        score = (lcs_len / len(template)) * 100
        
        # Bonus for exact sequence match
        if self._is_exact_subsequence(recent_poses, template):
            score = min(100, score * 1.2)
        
        if score < 30:
            return None
        
        # Find start and end indices
        start_idx = max(0, len(self.history) - self.window_size)
        end_idx = len(self.history) - 1
        
        return SequenceMatch(
            sequence_type=seq_type,
            start_idx=start_idx,
            end_idx=end_idx,
            start_time=self.history[start_idx]["timestamp"],
            end_time=self.history[end_idx]["timestamp"],
            poses=recent_poses,
            score=score,
            confidence=np.mean([h["confidence"] for h in self.history[start_idx:end_idx+1]]),
        )
    
    def _lcs_length(self, seq1: List[str], seq2: List[str]) -> int:
        """Compute length of longest common subsequence."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        return dp[m][n]
    
    def _is_exact_subsequence(self, seq: List[str], template: List[str]) -> bool:
        """Check if template is an exact subsequence of seq."""
        i = 0
        for pose in seq:
            if i < len(template) and pose == template[i]:
                i += 1
        return i == len(template)
    
    def get_current_sequence(self) -> Optional[SequenceMatch]:
        """Get the currently detected sequence."""
        return self.current_sequence
    
    def get_sequence_history(self) -> List[SequenceMatch]:
        """Get all detected sequences."""
        return self.detected_sequences
    
    def reset(self):
        """Reset detector state."""
        self.history.clear()
        self.current_sequence = None
        self.detected_sequences.clear()


# ── Sequence Feedback ─────────────────────────────────────────────────

def get_sequence_feedback(match: SequenceMatch) -> Dict:
    """Generate feedback for a detected sequence.
    
    Args:
        match: Detected sequence match
        
    Returns:
        Dictionary with feedback information
    """
    seq_def = SEQUENCES.get(match.sequence_type, {})
    
    # Find which pose should come next
    detected_poses = match.poses
    template = seq_def.get("poses", [])
    
    # Find where we are in the sequence
    current_idx = 0
    for i, template_pose in enumerate(template):
        if i < len(detected_poses) and detected_poses[-(len(template)-i)] == template_pose:
            current_idx = i + 1
    
    next_pose = template[current_idx] if current_idx < len(template) else None
    
    # Generate feedback
    feedback = {
        "sequence_name": seq_def.get("name", "Unknown"),
        "sequence_name_en": seq_def.get("name_en", "Unknown"),
        "score": match.score,
        "progress": f"{current_idx}/{len(template)}",
        "next_pose": next_pose,
        "message": "",
    }
    
    if match.score >= 80:
        feedback["message"] = f"很好的{feedback['sequence_name']}流动！"
    elif match.score >= 50:
        feedback["message"] = f"正在执行{feedback['sequence_name']}，继续！"
    else:
        feedback["message"] = f"检测到{feedback['sequence_name']}序列"
    
    if next_pose:
        feedback["suggestion"] = f"下一个体式: {next_pose}"
    
    return feedback


# ── Utility Functions ─────────────────────────────────────────────────

def analyze_sequence(pose_sequence: List[str]) -> List[Dict]:
    """Analyze a sequence of poses for patterns.
    
    Args:
        pose_sequence: List of pose IDs
        
    Returns:
        List of detected sequences with scores
    """
    detector = SequenceDetector(window_size=len(pose_sequence))
    
    results = []
    for i, pose in enumerate(pose_sequence):
        match = detector.update(pose, timestamp=float(i))
        if match:
            results.append({
                "sequence": match.sequence_type.value,
                "name": SEQUENCES[match.sequence_type]["name"],
                "start": match.start_idx,
                "end": match.end_idx,
                "score": match.score,
            })
    
    return results


# ── Example Usage ─────────────────────────────────────────────────────

if __name__ == "__main__":
    # Example: Sun Salutation A sequence
    sun_a_sequence = [
        "mountain",
        "upward_salute",
        "standing_forward_bend",
        "half_forward_fold",
        "plank",
        "chaturanga",
        "upward_facing_dog",
        "downward_facing_dog",
        "standing_forward_bend",
        "mountain",
    ]
    
    print("Testing Sun Salutation A detection:")
    print(f"Input sequence: {sun_a_sequence}")
    print()
    
    results = analyze_sequence(sun_a_sequence)
    
    if results:
        for r in results:
            print(f"Detected: {r['name']} (score: {r['score']:.1f}%)")
    else:
        print("No sequences detected")
