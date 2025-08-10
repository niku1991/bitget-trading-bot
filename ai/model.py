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
                # simple deterministic shuffle
                for i in range(n - 1, 0, -1):
                    j = int((i + 1) * 0.6180339887498949) % (i + 1)
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
            "type": "logistic",
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

class DecisionStump:
    def __init__(self, feature_idx: int = 0, threshold: float = 0.0, polarity: int = 1, alpha: float = 0.0):
        self.feature_idx = feature_idx
        self.threshold = threshold
        self.polarity = polarity  # +1 means predict +1 when x[fi] >= thr, -1 means inverse
        self.alpha = alpha

    def predict(self, x: List[float]) -> int:
        val = x[self.feature_idx]
        pred = 1 if (val >= self.threshold) else -1
        return pred if self.polarity == 1 else -pred

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_idx": self.feature_idx,
            "threshold": self.threshold,
            "polarity": self.polarity,
            "alpha": self.alpha,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'DecisionStump':
        return DecisionStump(d["feature_idx"], d["threshold"], d["polarity"], d.get("alpha", 0.0))

class AdaBoostStumps:
    def __init__(self, n_rounds: int = 50):
        self.n_rounds = n_rounds
        self.stumps: List[DecisionStump] = []

    def fit(self, X: List[List[float]], y: List[int]):
        # y in {0,1} -> convert to {-1, +1}
        y2 = [1 if v == 1 else -1 for v in y]
        n = len(X)
        if n == 0:
            return
        m = len(X[0])
        # initialize weights
        w = [1.0 / n] * n
        self.stumps = []
        for _ in range(self.n_rounds):
            best_stump = None
            best_err = float('inf')
            # search stumps
            for fi in range(m):
                # candidate thresholds from data points
                vals = [row[fi] for row in X]
                # unique thresholds reduced for speed
                unique_vals = sorted(set(vals))
                if len(unique_vals) > 50:
                    step = max(1, len(unique_vals) // 50)
                    unique_vals = unique_vals[::step]
                for thr in unique_vals:
                    for polarity in (1, -1):
                        err = 0.0
                        for i, row in enumerate(X):
                            pred = 1 if (row[fi] >= thr) else -1
                            if polarity == -1:
                                pred = -pred
                            if pred != y2[i]:
                                err += w[i]
                        if err < best_err:
                            best_err = err
                            best_stump = DecisionStump(fi, thr, polarity, 0.0)
            if best_stump is None:
                break
            # avoid degenerate
            best_err = max(1e-9, min(0.499999, best_err))
            alpha = 0.5 * math.log((1 - best_err) / best_err)
            best_stump.alpha = alpha
            self.stumps.append(best_stump)
            # update weights
            Z = 0.0
            for i, row in enumerate(X):
                pred = best_stump.predict(row)
                w[i] = w[i] * math.exp(-alpha * y2[i] * pred)
                Z += w[i]
            # normalize
            if Z > 0:
                w = [wi / Z for wi in w]

    def decision_function(self, x: List[float]) -> float:
        score = 0.0
        for stump in self.stumps:
            score += stump.alpha * stump.predict(x)
        return score

    def predict_proba_one(self, x: List[float]) -> float:
        # map score to [0,1]
        score = self.decision_function(x)
        # squashing
        return 1.0 / (1.0 + math.exp(-score))

    def to_json(self) -> str:
        return json.dumps({
            "type": "adaboost_stumps",
            "n_rounds": self.n_rounds,
            "stumps": [s.to_dict() for s in self.stumps]
        })

    @staticmethod
    def from_json(s: str) -> 'AdaBoostStumps':
        obj = json.loads(s)
        model = AdaBoostStumps(n_rounds=obj.get("n_rounds", 50))
        model.stumps = [DecisionStump.from_dict(d) for d in obj.get("stumps", [])]
        return model