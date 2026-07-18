"""Final optimized classifier with feature selection."""
from __future__ import annotations
import os
import json
import pickle
import numpy as np
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, f_classif

from .features_v2 import extract_features

MODEL_DIR = Path(__file__).parent.parent / "data" / "models"
MODEL_PATH = MODEL_DIR / "pose_classifier_v2.pkl"


class PoseClassifierV2:
    """Optimized pose classifier with feature selection."""

    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: List[str]) -> None:
        """Train classifier with feature selection."""
        self.label_encoder = LabelEncoder()
        y_encoded = self.label_encoder.fit_transform(y)

        # Use feature selection (k=30 best features)
        # Combined with ensemble of RF, SVM, KNN
        rf = Pipeline([
            ('scaler', StandardScaler()),
            ('select', SelectKBest(f_classif, k=30)),
            ('clf', RandomForestClassifier(n_estimators=500, max_depth=None, random_state=42))
        ])

        svm = Pipeline([
            ('scaler', StandardScaler()),
            ('select', SelectKBest(f_classif, k=30)),
            ('clf', SVC(kernel='rbf', C=10, gamma='scale', probability=True))
        ])

        knn = Pipeline([
            ('scaler', StandardScaler()),
            ('select', SelectKBest(f_classif, k=30)),
            ('clf', KNeighborsClassifier(n_neighbors=5, weights='distance'))
        ])

        self.model = VotingClassifier(
            estimators=[('rf', rf), ('svm', svm), ('knn', knn)],
            voting='soft',
            weights=[3, 2, 1]  # RF weighted highest
        )

        self.model.fit(X, y_encoded)
        self.is_fitted = True

    def predict_proba(self, X: np.ndarray) -> Dict[str, float]:
        """Predict probability distribution over asanas."""
        if not self.is_fitted:
            return {}
        if X.ndim == 1:
            X = X.reshape(1, -1)
        proba = self.model.predict_proba(X)[0]
        return {self.label_encoder.inverse_transform([i])[0]: float(p) 
                for i, p in enumerate(proba)}

    def predict(self, X: np.ndarray) -> Tuple[str, float]:
        """Predict most likely asana."""
        proba = self.predict_proba(X)
        if not proba:
            return None, 0.0
        best_id = max(proba, key=proba.get)
        return best_id, proba[best_id]

    def save(self, path: Optional[Path] = None) -> None:
        path = path or MODEL_PATH
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'label_encoder': self.label_encoder,
            }, f)

    def load(self, path: Optional[Path] = None) -> bool:
        path = path or MODEL_PATH
        if not path.exists():
            return False
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            self.model = data['model']
            self.label_encoder = data['label_encoder']
            self.is_fitted = True
            return True
        except Exception:
            return False


def train_from_ref_data_v2(ref_dir: Optional[str] = None) -> PoseClassifierV2:
    """Train optimized classifier from reference data."""
    if ref_dir is None:
        ref_dir = os.path.join(os.path.dirname(__file__), "..", "data", "ref")

    X_list, y_list = [], []
    for asana_id in sorted(os.listdir(ref_dir)):
        asana_dir = os.path.join(ref_dir, asana_id)
        if not os.path.isdir(asana_dir):
            continue
        for fname in sorted(os.listdir(asana_dir)):
            if not fname.endswith('.json'):
                continue
            with open(os.path.join(asana_dir, fname)) as f:
                data = json.load(f)
            world = data if isinstance(data, list) else data.get('world_landmarks', data.get('landmarks', []))
            if not world or len(world) < 33:
                continue
            X_list.append(extract_features(world))
            y_list.append(asana_id)

    X = np.array(X_list)
    print(f"Training v2: {len(X)} samples, {len(set(y_list))} classes, {X.shape[1]} features")

    clf = PoseClassifierV2()
    clf.fit(X, y_list)
    clf.save()
    print(f"Model saved to {MODEL_PATH}")
    return clf


def load_classifier_v2() -> Optional[PoseClassifierV2]:
    """Load trained v2 classifier."""
    clf = PoseClassifierV2()
    if clf.load():
        return clf
    return None
