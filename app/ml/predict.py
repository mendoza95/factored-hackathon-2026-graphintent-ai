from pathlib import Path
from typing import Any, Dict

import joblib
import pandas as pd

from app.ml.data import FEATURE_COLS


class IntentPredictor:
    """
    Inference class for predicting call intent using
    the trained ColumnTransformer model.
    """

    def __init__(self, model_path: Path):
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        """Load the trained joblib model pipeline."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {self.model_path}. "
                "Ensure app/ml/train_classifier.py has been executed."
            )
        self.pipeline = joblib.load(self.model_path)

    def _prepare_payload(self, raw_payload: Dict[str, Any]) -> pd.DataFrame:
        full_text = str(raw_payload.get("full_text") or "").strip()
        keywords = str(raw_payload.get("detected_keywords") or "").strip()
        intents = str(raw_payload.get("detected_intents") or "").strip()
        topics = str(raw_payload.get("main_topics") or "").strip()

        text_parts = [p for p in [full_text, keywords, intents, topics] if p]
        rich_text = " ".join(text_parts) if text_parts else ""

        data = {
            "rich_text": [rich_text],
            "channel": [raw_payload.get("channel") or "chat"],
            "detected_sentiment": [raw_payload.get("detected_sentiment") or "neutral"],
            "duration_seconds": [
                float(raw_payload.get("duration_seconds", 0.0) or 0.0)
            ],
            "wait_time_seconds": [
                float(raw_payload.get("wait_time_seconds", 0.0) or 0.0)
            ],
            "sentiment_score": [float(raw_payload.get("sentiment_score", 0.0) or 0.0)],
        }

        df = pd.DataFrame(data)
        return df[FEATURE_COLS]

    def predict(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict intent label and class probabilities for a
        single interaction payload.
        """
        df_input = self._prepare_payload(raw_payload)

        # Predicción y cálculo de probabilidades
        predicted_label = self.pipeline.predict(df_input)[0]
        probabilities = self.pipeline.predict_proba(df_input)[0]
        classes = self.pipeline.classes_

        confidence_scores = {
            str(cls): float(prob) for cls, prob in zip(classes, probabilities)
        }

        return {
            "predicted_label": str(predicted_label),
            "confidence": float(max(probabilities)),
            "class_probabilities": confidence_scores,
        }


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent
    MODEL_PATH = BASE_DIR / "ml" / "models" / "intent_classifier_2026_05_31.joblib"

    predictor = IntentPredictor(model_path=MODEL_PATH)

    sample_payload = {
        "full_text": (
            "Quiero poner una queja formal por un cobro duplicado en mi tarjeta."
        ),
        "detected_keywords": "queja, cobro duplicado",
        "detected_intents": "reclamo",
        "main_topics": "transacción",
        "channel": "chat",
        "detected_sentiment": "negative",
        "duration_seconds": 240.0,
        "wait_time_seconds": 15.0,
        "sentiment_score": -0.8,
        "has_past_complaint": True,
    }

    result = predictor.predict(sample_payload)
    print("=== TEST INFERENCE RESULT ===")
    print(result)
