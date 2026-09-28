import os
from pathlib import Path
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "intent_training_data.csv"
MODEL_DIR = BASE_DIR / "app" / "ml" / "models"
MODEL_PATH = MODEL_DIR / "intent_classifier.joblib"


def train_intent_model():
    """Train a fast TF-IDF + Logistic Regression model for intent classification."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found at {DATA_PATH}. "
            "Please run app/ml/extract_training_data.py first."
        )

    print(f"Loading training data from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)

    # Filter out missing text or labels
    df = df.dropna(subset=["text", "label"])

    X = df["text"]
    y = df["label"]

    print(f"Dataset shape: {X.shape}")
    print("Class distribution:\n", y.value_counts())

    # Split train/test sets with stratification
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Build lightweight NLP pipeline
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=10000,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    C=1.0,
                    random_state=42,
                ),
            ),
        ]
    )

    print("\nTraining intent classifier...")
    pipeline.fit(X_train, y_train)

    # Evaluate model performance
    y_pred = pipeline.predict(X_test)
    macro_f1 = f1_score(y_test, y_pred, average="macro")

    print("\n--- Evaluation Report ---")
    print(classification_report(y_test, y_pred))
    print(f"Macro F1 Score: {macro_f1:.4f}")

    # Save model artifact
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"\nModel successfully saved to {MODEL_PATH}")


if __name__ == "__main__":
    train_intent_model()