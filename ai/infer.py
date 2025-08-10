from typing import List
from .features import compute_feature_vector
from .model import AdaBoostStumps
import json


def load_model(model_path: str = "ai_model.json"):
    with open(model_path, "r") as f:
        return AdaBoostStumps.from_json(f.read())


def predict_score(model, candles: List[dict]) -> float:
    feats, _ = compute_feature_vector(candles, window=min(50, len(candles)))
    proba = model.predict_proba_one(feats)
    return float(proba)