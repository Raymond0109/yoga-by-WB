"""Learned pose classifier using ensemble of simple models.

Uses features extracted from world landmarks to classify poses.
Supports KNN, SVM, and Random Forest with optional ensemble.
"""

from __future__ import annotations
import os
import json
import pickle
import numpy as np
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from .features import extract_features

# Model storage path
MODEL_DIR = Path(__file__).parent.parent / "data" / "models"
MODEL_PATH = MODEL_DIR / "pose_classifier.pkl"


class PoseClassifier:
    """Learned pose classifier using scikit-learn models."""

    def __init__(self):
        self.model = None
        self.label_encoder = {}  # asana_id -> index
        self.label_decoder = {}  # index -> asana_id
        self.is_fitted = False
        self.feature_dim = None

    def fit(self, X: np.ndarray, y: List[str]) -> None:
        """Train classifier on feature matrix X and labels y.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: List of asana_id strings
        """
        from sklearn.ensemble import RandomForestClassifier, VotingClassifier
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.svm import SVC
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline

        # Encode labels
        unique_labels = sorted(set(y))
        self.label_encoder = {label: idx for idx, label in enumerate(unique_labels)}
        self.label_decoder = {idx: label for label, idx in self.label_encoder.items()}
        y_encoded = np.array([self.label_encoder[label] for label in y])

        self.feature_dim = X.shape[1]

        # Create ensemble of models
        knn = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', KNeighborsClassifier(n_neighbors=5, weights='distance'))
        ])

        svm = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', SVC(kernel='rbf', C=10, gamma='scale', probability=True))
        ])

        rf = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42))
        ])

        # Voting ensemble
        self.model = VotingClassifier(
            estimators=[('knn', knn), ('svm', svm), ('rf', rf)],
            voting='soft',
            weights=[1, 2, 2]  # SVM and RF weighted higher
        )

        self.model.fit(X, y_encoded)
        self.is_fitted = True

    def predict_proba(self, X: np.ndarray) -> Dict[str, float]:
        """Predict probability distribution over asanas.

        Args:
            X: Feature vector (1, n_features) or (n_features,)

        Returns:
            Dict mapping asana_id to probability
        """
        if not self.is_fitted:
            return {}

        if X.ndim == 1:
            X = X.reshape(1, -1)

        proba = self.model.predict_proba(X)[0]
        return {self.label_decoder[i]: float(p) for i, p in enumerate(proba)}

    def predict(self, X: np.ndarray) -> Tuple[str, float]:
        """Predict most likely asana.

        Args:
            X: Feature vector (1, n_features) or (n_features,)

        Returns:
            Tuple of (asana_id, confidence)
        """
        proba = self.predict_proba(X)
        if not proba:
            return None, 0.0
        best_id = max(proba, key=proba.get)
        return best_id, proba[best_id]

    def save(self, path: Optional[Path] = None) -> None:
        """Save model to disk."""
        path = path or MODEL_PATH
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'label_encoder': self.label_encoder,
                'label_decoder': self.label_decoder,
                'feature_dim': self.feature_dim,
            }, f)

    def load(self, path: Optional[Path] = None) -> bool:
        """Load model from disk. Returns True if successful."""
        path = path or MODEL_PATH
        if not path.exists():
            return False
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.model = data['model']
            self.label_encoder = data['label_encoder']
            self.label_decoder = data['label_decoder']
            self.feature_dim = data['feature_dim']
            self.is_fitted = True
            return True
        except Exception:
            return False


def train_from_ref_data(ref_dir: Optional[str] = None) -> PoseClassifier:
    """Train classifier from reference landmark data.

    Args:
        ref_dir: Path to data/ref directory

    Returns:
        Trained PoseClassifier
    """
    if ref_dir is None:
        ref_dir = os.path.join(os.path.dirname(__file__), "..", "data", "ref")

    X_list = []
    y_list = []

    for asana_id in sorted(os.listdir(ref_dir)):
        asana_dir = os.path.join(ref_dir, asana_id)
        if not os.path.isdir(asana_dir):
            continue

        for fname in sorted(os.listdir(asana_dir)):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(asana_dir, fname)
            with open(fpath) as f:
                data = json.load(f)

            # Handle both list and dict formats
            world = data if isinstance(data, list) else data.get('world_landmarks', data.get('landmarks', []))
            if not world or len(world) < 33:
                continue

            features = extract_features(world)
            X_list.append(features)
            y_list.append(asana_id)

    X = np.array(X_list)
    print(f"Training on {len(X)} samples, {len(set(y_list))} classes, {X.shape[1]} features")

    clf = PoseClassifier()
    clf.fit(X, y_list)
    clf.save()
    print(f"Model saved to {MODEL_PATH}")

    return clf


def load_classifier() -> Optional[PoseClassifier]:
    """Load trained classifier from disk."""
    clf = PoseClassifier()
    if clf.load():
        return clf
    return None
