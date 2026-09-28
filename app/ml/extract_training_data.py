from pathlib import Path
import duckdb

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "sample"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "intent_training_data.csv"


def extract_labeled_intent_data():
    """Extract customer text transcripts and assign ground truth intent labels using DuckDB."""
    print("Extracting training dataset with DuckDB...")

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    query = f"""
    SELECT 
        t.customer_text AS text,
        t.detected_accent AS accent,
        CASE 
            WHEN c.complaint_id IS NOT NULL THEN 'dispute_initiate'
            WHEN i.was_escalated = TRUE THEN 'human_handoff'
            ELSE 'account_inquiry'
        END AS label
    FROM read_csv_auto('{DATA_DIR}/call_transcripts_20260101.csv') t
    JOIN read_csv_auto('{DATA_DIR}/call_center_interactions_20260101.csv') i
        ON t.interaction_id = i.interaction_id
    LEFT JOIN read_csv_auto('{DATA_DIR}/complaints_20260101.csv') c
        ON i.interaction_id = c.origin_interaction_id
    WHERE t.customer_text IS NOT NULL AND TRIM(t.customer_text) != ''
    """

    con = duckdb.connect()
    df = con.execute(query).df()

    # Save processed training dataset locally
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Dataset successfully saved to {OUTPUT_FILE}")
    print(f"Total extracted rows: {len(df)}")
    print("\nClass distribution:")
    print(df["label"].value_counts())


if __name__ == "__main__":
    extract_labeled_intent_data()