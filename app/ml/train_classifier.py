from pathlib import Path

import joblib
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml.data import FEATURE_COLS, load_and_prepare_data


def build_pipeline() -> Pipeline:
    """Construct the multi-feature ColumnTransformer classification pipeline."""
    text_transformer = TfidfVectorizer(
        ngram_range=(1, 3),
        max_features=5000,
        sublinear_tf=True,
        strip_accents="unicode",
    )

    categorical_cols = ["channel", "detected_sentiment", "has_past_complaint"]
    categorical_transformer = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    numeric_cols = [
        "duration_seconds",
        "wait_time_seconds",
        "sentiment_score",
    ]
    numeric_transformer = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("text", text_transformer, "rich_text"),
            ("cat", categorical_transformer, categorical_cols),
            ("num", numeric_transformer, numeric_cols),
        ]
    )

    return Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "clf",
                LogisticRegression(
                    class_weight="balanced", max_iter=1000, random_state=42
                ),
            ),
        ]
    )


def train_and_save_model(data_dir: Path, model_output_path: Path):
    """
    Load dataset, train the intent classifier, print metrics,
    and serialize the model.
    """
    print(f"Loading data from {data_dir}...")
    df = load_and_prepare_data(data_dir)

    X = df[FEATURE_COLS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_pipeline()

    print("Training multi-feature model...")
    pipeline.fit(X_train, y_train)

    print("\n=== CLASSIFICATION REPORT ===")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))

    model_output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_output_path)
    print(f"\nModel artifact successfully saved to: {model_output_path}")


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent
    train_and_save_model(
        data_dir=BASE_DIR / "data" / "sample",
        model_output_path=BASE_DIR / "ml" / "models" / "intent_classifier.joblib",
    )
