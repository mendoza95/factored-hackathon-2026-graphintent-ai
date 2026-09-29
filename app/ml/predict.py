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
                "Ensure app/ml/train.py has been executed."
            )
        self.pipeline = joblib.load(self.model_path)

    def _prepare_payload(self, raw_payload: Dict[str, Any]) -> pd.DataFrame:
        """
        Process incoming raw dictionary payload into a structured
        single-row DataFrame matching training features.
        """
        full_text = str(raw_payload.get("full_text", ""))
        keywords = str(raw_payload.get("detected_keywords", ""))
        intents = str(raw_payload.get("detected_intents", ""))
        topics = str(raw_payload.get("main_topics", ""))

        # If metadata fields are missing, rich_text safely defaults to full_text
        rich_text = (
            f"{full_text} {keywords} {intents} {topics}".strip()
            if any([keywords, intents, topics])
            else full_text
        )

        data = {
            "rich_text": [rich_text],
            "channel": [raw_payload.get("channel", "unknown")],
            "detected_sentiment": [raw_payload.get("detected_sentiment", "neutral")],
            "duration_seconds": [raw_payload.get("duration_seconds", 0.0)],
            "wait_time_seconds": [raw_payload.get("wait_time_seconds", 0.0)],
            "sentiment_score": [raw_payload.get("sentiment_score", 0.0)],
            "has_past_complaint": [bool(raw_payload.get("has_past_complaint", False))],
        }

        return pd.DataFrame(data)[FEATURE_COLS]

    def predict(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict intent label and class probabilities for a
        single interaction payload.
        """
        df_input = self._prepare_payload(raw_payload)

        # Get class prediction and probability array
        predicted_label = self.pipeline.predict(df_input)[0]
        probabilities = self.pipeline.predict_proba(df_input)[0]
        classes = self.pipeline.classes_

        confidence_scores = {
            cls: float(prob) for cls, prob in zip(classes, probabilities)
        }

        return {
            "predicted_intent": predicted_label,
            "confidence": float(max(probabilities)),
            "class_probabilities": confidence_scores,
        }


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent
    MODEL_PATH = BASE_DIR / "ml" / "models" / "intent_classifier.joblib"

    # Initialize predictor
    predictor = IntentPredictor(model_path=MODEL_PATH)

    # Test sample payload
    sample_payload = {
        "full_text": "Quiero poner una queja formal por un cobro "
        "duplicado en mi tarjeta.",
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
