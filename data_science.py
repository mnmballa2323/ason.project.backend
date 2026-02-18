"""
Security Data Science — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

ML pipeline, threat clustering, predictive model — all stdlib.
"""

import hashlib, logging, math, os, random, statistics, time
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.data_science")


# ============================================================================
#  ML PIPELINE
# ============================================================================

class FeatureType(str, Enum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    TEMPORAL = "temporal"


class Feature:
    def __init__(self, name, feat_type, extractor):
        self.name = name
        self.feat_type = feat_type
        self.extractor = extractor  # Callable: event → value
        self.importance = 0.0

    def to_dict(self):
        return {"name": self.name, "type": self.feat_type.value,
                "importance": round(self.importance, 4)}


class MLPipeline:
    """Feature engineering → model training → inference (stdlib only)."""

    def __init__(self):
        self._features: List[Feature] = []
        self._training_data: List[List[float]] = []
        self._labels: List[int] = []
        self._weights: List[float] = []
        self._trained = False
        self._accuracy = 0.0
        self._seed_features()

    def _seed_features(self):
        features = [
            ("request_rate", FeatureType.NUMERIC, lambda e: e.get("requests_per_min", 0)),
            ("error_rate", FeatureType.NUMERIC, lambda e: e.get("error_rate", 0)),
            ("payload_size", FeatureType.NUMERIC, lambda e: e.get("payload_bytes", 0)),
            ("entropy", FeatureType.NUMERIC, lambda e: e.get("entropy", 0)),
            ("unique_endpoints", FeatureType.NUMERIC, lambda e: e.get("unique_endpoints", 1)),
            ("auth_failures", FeatureType.NUMERIC, lambda e: e.get("auth_failures", 0)),
            ("geo_anomaly", FeatureType.BOOLEAN, lambda e: 1.0 if e.get("geo_anomaly") else 0.0),
            ("off_hours", FeatureType.BOOLEAN, lambda e: 1.0 if e.get("off_hours") else 0.0),
            ("new_user_agent", FeatureType.BOOLEAN, lambda e: 1.0 if e.get("new_ua") else 0.0),
            ("session_duration", FeatureType.TEMPORAL, lambda e: e.get("session_seconds", 0)),
            ("privilege_level", FeatureType.NUMERIC, lambda e: e.get("priv_level", 0)),
            ("data_volume", FeatureType.NUMERIC, lambda e: e.get("data_volume_mb", 0)),
        ]
        for name, ftype, extractor in features:
            self._features.append(Feature(name, ftype, extractor))

    def extract_features(self, event: Dict) -> List[float]:
        return [f.extractor(event) for f in self._features]

    def train(self, events: List[Dict], labels: List[int]) -> Dict:
        """Train a simple logistic regression model (stdlib only)."""
        if len(events) != len(labels):
            return {"error": "Events and labels must have same length"}

        self._training_data = [self.extract_features(e) for e in events]
        self._labels = labels
        n_features = len(self._features)

        # Initialize weights
        self._weights = [0.0] * n_features
        bias = 0.0
        learning_rate = 0.01
        epochs = 100

        for epoch in range(epochs):
            total_loss = 0
            for i, features in enumerate(self._training_data):
                # Forward pass
                z = sum(w * f for w, f in zip(self._weights, features)) + bias
                pred = 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))  # sigmoid
                error = pred - labels[i]
                total_loss += abs(error)

                # Update weights (SGD)
                for j in range(n_features):
                    self._weights[j] -= learning_rate * error * features[j]
                bias -= learning_rate * error

        # Calculate accuracy
        correct = 0
        for i, features in enumerate(self._training_data):
            z = sum(w * f for w, f in zip(self._weights, features)) + bias
            pred = 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))
            if (pred >= 0.5 and labels[i] == 1) or (pred < 0.5 and labels[i] == 0):
                correct += 1
        self._accuracy = correct / max(len(labels), 1)

        # Feature importance
        for i, f in enumerate(self._features):
            f.importance = abs(self._weights[i])

        self._trained = True
        return {
            "trained": True,
            "samples": len(events),
            "features": n_features,
            "accuracy": round(self._accuracy, 4),
            "top_features": sorted([f.to_dict() for f in self._features],
                                  key=lambda x: x["importance"], reverse=True)[:5],
        }

    def predict(self, event: Dict) -> Dict:
        if not self._trained:
            return {"error": "Model not trained"}
        features = self.extract_features(event)
        z = sum(w * f for w, f in zip(self._weights, features))
        probability = 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))
        return {
            "threat_probability": round(probability, 4),
            "is_threat": probability >= 0.5,
            "confidence": round(abs(probability - 0.5) * 2, 4),
        }

    def generate_training_data(self, n_samples: int = 500) -> Tuple[List[Dict], List[int]]:
        """Generate synthetic training data for demo."""
        events = []
        labels = []
        for _ in range(n_samples):
            is_threat = random.random() < 0.3
            event = {
                "requests_per_min": random.gauss(50, 20) if not is_threat else random.gauss(200, 50),
                "error_rate": random.gauss(0.02, 0.01) if not is_threat else random.gauss(0.3, 0.1),
                "payload_bytes": random.gauss(1024, 512) if not is_threat else random.gauss(50000, 20000),
                "entropy": random.gauss(4, 1) if not is_threat else random.gauss(7.5, 0.5),
                "unique_endpoints": random.randint(1, 5) if not is_threat else random.randint(20, 100),
                "auth_failures": random.randint(0, 1) if not is_threat else random.randint(3, 20),
                "geo_anomaly": random.random() < 0.05 if not is_threat else random.random() < 0.6,
                "off_hours": random.random() < 0.1 if not is_threat else random.random() < 0.5,
                "new_ua": random.random() < 0.1 if not is_threat else random.random() < 0.7,
                "session_seconds": random.gauss(1800, 600) if not is_threat else random.gauss(300, 100),
                "priv_level": random.randint(1, 3) if not is_threat else random.randint(5, 10),
                "data_volume_mb": random.gauss(10, 5) if not is_threat else random.gauss(500, 200),
            }
            events.append(event)
            labels.append(1 if is_threat else 0)
        return events, labels

    def get_stats(self) -> Dict:
        return {"trained": self._trained, "accuracy": round(self._accuracy, 4),
                "features": len(self._features),
                "training_samples": len(self._training_data)}


# ============================================================================
#  THREAT CLUSTERING
# ============================================================================

class ThreatCluster:
    def __init__(self, cluster_id, centroid, members):
        self.cluster_id = cluster_id
        self.centroid = centroid
        self.members = members
        self.label = "unknown"

    def to_dict(self):
        return {"id": self.cluster_id, "size": len(self.members),
                "centroid": [round(c, 3) for c in self.centroid],
                "label": self.label}


class ThreatClustering:
    """K-means clustering of similar threats for pattern discovery."""

    def __init__(self):
        self._clusters: List[ThreatCluster] = []
        self._runs = 0

    def kmeans(self, data: List[List[float]], k: int = 5,
              max_iterations: int = 100) -> Dict:
        """Pure stdlib K-means implementation."""
        if not data or k <= 0:
            return {"error": "Invalid input"}
        self._runs += 1
        n_features = len(data[0])

        # Initialize centroids (k-means++)
        centroids = [data[random.randint(0, len(data) - 1)][:]]
        for _ in range(1, min(k, len(data))):
            distances = []
            for point in data:
                min_dist = min(self._euclidean(point, c) for c in centroids)
                distances.append(min_dist)
            total = sum(distances)
            if total == 0:
                centroids.append(data[random.randint(0, len(data) - 1)][:])
            else:
                probs = [d / total for d in distances]
                r = random.random()
                cumulative = 0
                for i, p in enumerate(probs):
                    cumulative += p
                    if cumulative >= r:
                        centroids.append(data[i][:])
                        break

        # Iterate
        assignments = [0] * len(data)
        for iteration in range(max_iterations):
            changed = False
            # Assign points
            for i, point in enumerate(data):
                min_dist = float('inf')
                best = 0
                for j, centroid in enumerate(centroids):
                    d = self._euclidean(point, centroid)
                    if d < min_dist:
                        min_dist = d
                        best = j
                if assignments[i] != best:
                    changed = True
                assignments[i] = best

            if not changed:
                break

            # Update centroids
            for j in range(len(centroids)):
                members = [data[i] for i in range(len(data)) if assignments[i] == j]
                if members:
                    centroids[j] = [sum(m[f] for m in members) / len(members)
                                   for f in range(n_features)]

        # Build clusters
        self._clusters = []
        for j in range(len(centroids)):
            members = [i for i in range(len(data)) if assignments[i] == j]
            cluster = ThreatCluster(f"C-{j}", centroids[j], members)
            # Auto-label based on centroid characteristics
            if len(centroids[j]) > 0 and centroids[j][0] > 100:
                cluster.label = "high_volume_attack"
            elif len(centroids[j]) > 5 and centroids[j][5] > 3:
                cluster.label = "credential_attack"
            elif len(centroids[j]) > 3 and centroids[j][3] > 6:
                cluster.label = "encoded_payload"
            else:
                cluster.label = "normal_traffic"
            self._clusters.append(cluster)

        return {
            "clusters": [c.to_dict() for c in self._clusters],
            "k": len(centroids),
            "iterations": iteration + 1,
            "total_points": len(data),
        }

    def _euclidean(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))

    def get_stats(self) -> Dict:
        return {"runs": self._runs, "clusters": len(self._clusters)}


# ============================================================================
#  PREDICTIVE MODEL
# ============================================================================

class PredictiveModel:
    """Predict next attack vector based on historical patterns."""

    ATTACK_VECTORS = [
        "phishing", "credential_stuffing", "sql_injection", "xss",
        "ransomware", "supply_chain", "insider_threat", "ddos",
        "zero_day", "data_exfiltration", "privilege_escalation",
        "lateral_movement",
    ]

    def __init__(self):
        self._history: List[Dict] = []
        self._transition_matrix: Dict[str, Dict[str, float]] = {}
        self._predictions: List[Dict] = []
        self._build_transition_matrix()

    def _build_transition_matrix(self):
        """Markov chain transition probabilities between attack types."""
        for vector in self.ATTACK_VECTORS:
            self._transition_matrix[vector] = {}
            remaining = 1.0
            # Assign higher probabilities to likely follow-up attacks
            follow_ups = {
                "phishing": {"credential_stuffing": 0.35, "lateral_movement": 0.20},
                "credential_stuffing": {"privilege_escalation": 0.30, "data_exfiltration": 0.25},
                "sql_injection": {"data_exfiltration": 0.40, "privilege_escalation": 0.20},
                "xss": {"credential_stuffing": 0.25, "phishing": 0.20},
                "ransomware": {"data_exfiltration": 0.15, "lateral_movement": 0.15},
                "supply_chain": {"lateral_movement": 0.30, "privilege_escalation": 0.25},
                "insider_threat": {"data_exfiltration": 0.45, "privilege_escalation": 0.20},
                "ddos": {"sql_injection": 0.15, "xss": 0.10},
                "zero_day": {"privilege_escalation": 0.35, "lateral_movement": 0.25},
                "data_exfiltration": {"ransomware": 0.20, "insider_threat": 0.15},
                "privilege_escalation": {"lateral_movement": 0.40, "data_exfiltration": 0.30},
                "lateral_movement": {"data_exfiltration": 0.35, "ransomware": 0.20},
            }
            assigned = follow_ups.get(vector, {})
            for target, prob in assigned.items():
                self._transition_matrix[vector][target] = prob
                remaining -= prob
            # Distribute remaining probability
            other_vectors = [v for v in self.ATTACK_VECTORS
                           if v != vector and v not in assigned]
            if other_vectors:
                per_other = remaining / len(other_vectors)
                for other in other_vectors:
                    self._transition_matrix[vector][other] = round(per_other, 4)

    def record_attack(self, attack_type: str, severity: str = "medium",
                     details: Dict = None) -> Dict:
        record = {
            "type": attack_type, "severity": severity,
            "details": details or {},
            "ts": datetime.now(timezone.utc).isoformat()}
        self._history.append(record)
        return record

    def predict_next(self, recent_attacks: List[str] = None) -> Dict:
        """Predict most likely next attack vector using Markov chain."""
        if not recent_attacks:
            recent_attacks = [h["type"] for h in self._history[-5:]]
        if not recent_attacks:
            return {"error": "No attack history"}

        last_attack = recent_attacks[-1]
        transitions = self._transition_matrix.get(last_attack, {})

        # Weight by recency
        predictions = []
        for vector, base_prob in sorted(transitions.items(), key=lambda x: x[1], reverse=True):
            # Boost probability if seen in recent history
            recency_boost = 1.0
            if vector in recent_attacks:
                recency_boost = 1.3
            adjusted_prob = min(1.0, base_prob * recency_boost)
            predictions.append({
                "vector": vector,
                "probability": round(adjusted_prob, 4),
                "confidence": "high" if adjusted_prob > 0.25 else "medium" if adjusted_prob > 0.10 else "low",
            })

        predictions.sort(key=lambda x: x["probability"], reverse=True)
        result = {
            "based_on": last_attack,
            "recent_history": recent_attacks,
            "predictions": predictions[:5],
            "recommended_defenses": self._recommend_defenses(predictions[0]["vector"] if predictions else ""),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._predictions.append(result)
        return result

    def _recommend_defenses(self, predicted_vector: str) -> List[str]:
        defenses = {
            "phishing": ["Email filtering", "Security awareness training", "MFA enforcement"],
            "credential_stuffing": ["Rate limiting", "MFA", "Credential monitoring"],
            "sql_injection": ["WAF rules", "Parameterized queries", "Input validation"],
            "xss": ["CSP headers", "Output encoding", "WAF"],
            "ransomware": ["Immutable backups", "EDR", "Network segmentation"],
            "supply_chain": ["SBOM validation", "Code signing", "Dependency scanning"],
            "insider_threat": ["UEBA", "DLP", "Access reviews"],
            "ddos": ["CDN", "Rate limiting", "Auto-scaling"],
            "zero_day": ["Virtual patching", "Behavioral detection", "Micro-segmentation"],
            "data_exfiltration": ["DLP", "DNS monitoring", "Egress filtering"],
            "privilege_escalation": ["Least privilege", "PAM", "Anomaly detection"],
            "lateral_movement": ["Micro-segmentation", "NDR", "Zero trust"],
        }
        return defenses.get(predicted_vector, ["Monitor and investigate"])

    def get_stats(self) -> Dict:
        return {"history": len(self._history),
                "predictions": len(self._predictions),
                "vectors_tracked": len(self.ATTACK_VECTORS)}


# Singletons
ml_pipeline = MLPipeline()
threat_clustering = ThreatClustering()
predictive_model = PredictiveModel()
