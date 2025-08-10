import json
import math
from typing import List, Dict, Any

class LogisticModel:
    def __init__(self, n_features: int, lr: float = 0.05, l2: float = 1e-4):
        self.weights = [0.0] * n_features
        self.bias = 0.0
        self.lr = lr
        self.l2 = l2

    @staticmethod
    def _sigmoid(z: float) -> float:
        if z < -35:
            return 0.0
        if z > 35:
            return 1.0
        return 1.0 / (1.0 + math.exp(-z))

    def predict_proba_one(self, x: List[float]) -> float:
        z = self.bias
        for w, xi in zip(self.weights, x):
            z += w * xi
        return self._sigmoid(z)

    def fit(self, X: List[List[float]], y: List[int], epochs: int = 10, shuffle: bool = True):
        n = len(X)
        if n == 0:
            return
        idxs = list(range(n))
        for _ in range(epochs):
            if shuffle:
                # simple Fisher-Yates shuffle
                for i in range(n - 1, 0, -1):
                    j = int((i + 1) * 0.6180339887498949) % (i + 1)  # deterministic
                    idxs[i], idxs[j] = idxs[j], idxs[i]
            for i in idxs:
                xi = X[i]
                yi = y[i]
                p = self.predict_proba_one(xi)
                err = p - yi
                # Update with L2
                for k in range(len(self.weights)):
                    grad = err * xi[k] + self.l2 * self.weights[k]
                    self.weights[k] -= self.lr * grad
                self.bias -= self.lr * err

    def to_json(self) -> str:
        return json.dumps({
            "weights": self.weights,
            "bias": self.bias,
            "lr": self.lr,
            "l2": self.l2
        })

    @staticmethod
    def from_json(s: str) -> 'LogisticModel':
        obj = json.loads(s)
        m = LogisticModel(len(obj["weights"]), lr=obj.get("lr", 0.05), l2=obj.get("l2", 1e-4))
        m.weights = obj["weights"]
        m.bias = obj["bias"]
        return m