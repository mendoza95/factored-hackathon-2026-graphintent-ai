import os
import sys
from datetime import datetime
from pathlib import Path

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml.data import FEATURE_COLS, get_or_create_dataset


def build_pipeline() -> Pipeline:
    """Construct the multi-feature ColumnTransformer classification pipeline."""
    text_transformer = TfidfVectorizer(
        ngram_range=(1, 3),
        max_features=5000,
        sublinear_tf=True,
        strip_accents="unicode",
    )

    categorical_cols = ["channel", "detected_sentiment"]
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

    base_clf = LogisticRegression(
        class_weight="balanced", max_iter=1000, random_state=42
    )

    # La calibración por sigmoide normaliza las probabilidades cuando hay desbalance
    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv=3)

    return Pipeline(
        [
            ("preprocessor", preprocessor),
            ("clf", calibrated_clf),
        ]
    )


def train_and_save_model(
    data_dir: Path,
    model_output_path: Path,
    processed_dataset_path: Path,
    start_date: datetime,
    days_back: int = 30,
    force_rebuild_data: bool = False,
):
    """
    Load dataset from Parquet (or rebuild if needed), train the intent classifier,
    print metrics, and serialize the model.
    """
    df = get_or_create_dataset(
        data_dir=data_dir,
        processed_parquet_path=processed_dataset_path,
        force_rebuild=force_rebuild_data,
        start_date=start_date,
        days_back=days_back,
    )

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

    # Detecta si se pasa la bandera --s3 como primer o segundo argumento
    use_s3 = "--s3" in sys.argv
    if use_s3:
        sys.argv.remove("--s3")  # Remueve el flag para leer la fecha limpia

    # Manejo de la fecha introducida desde la terminal (Formato: DD/MM/YYYY)
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        try:
            start_date = datetime.strptime(date_str, "%d/%m/%Y").replace(
                hour=23, minute=59, second=59
            )
        except ValueError:
            print(
                f"Error: Formato de fecha inválido '{date_str}'. \
                  Usa DD/MM/YYYY (ej. 31/05/2026)"
            )
            sys.exit(1)
    else:
        start_date = datetime.now()

    force_rebuild = False  # dejamos en false por defecto
    # Selección del origen de datos
    if use_s3:
        s3_bucket = os.getenv("S3_BUCKET_NAME")
        if not s3_bucket:
            print(
                "Error: Se especificó --s3 pero "
                "no hay variables de entorno de S3 en .env"
            )
            sys.exit(1)
        data_dir = f"s3://{s3_bucket}"
        force_rebuild = True
        print(f"--> [MODO S3] Leyendo desde: {data_dir}")
    else:
        data_dir = BASE_DIR / "data" / "processed"
        print(f"--> [MODO LOCAL] Leyendo desde: {data_dir}")

    date_suffix = start_date.strftime("%Y_%m_%d")
    processed_parquet = (
        BASE_DIR / "data" / "processed" / f"train_dataset_{date_suffix}.parquet"
    )
    model_output = (
        BASE_DIR / "ml" / "models" / f"intent_classifier_{date_suffix}.joblib"
    )

    train_and_save_model(
        data_dir=data_dir,
        processed_dataset_path=processed_parquet,
        model_output_path=model_output,
        start_date=start_date,
        days_back=120,
        force_rebuild_data=force_rebuild,
    )
