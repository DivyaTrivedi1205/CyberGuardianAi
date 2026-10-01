import os
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import xgboost as xgb


def parse_arff(file_path):
    print(f"Parsing ARFF file: {file_path}")
    attributes = []
    data_started = False
    data_lines = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.lower().startswith("@relation"):
                continue
            if line_str.lower().startswith("@attribute"):
                # Format: @attribute name type
                parts = line_str.split()
                attr_name = parts[1]
                attributes.append(attr_name)
                continue
            if line_str.lower().startswith("@data"):
                data_started = True
                continue
            if data_started:
                # Comma separated integer values
                vals = [int(v.strip()) for v in line_str.split(",")]
                data_lines.append(vals)

    df = pd.DataFrame(data_lines, columns=attributes)
    print(f"Loaded {df.shape[0]} samples with {df.shape[1]} columns.")
    return df


def train_url_model():
    print("\n--- Training URL Phishing Model ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    arff_path = os.path.abspath(
        os.path.join(
            script_dir,
            "..",
            "datasets",
            "urls",
            "phishing_websites",
            "Training Dataset.arff",
        )
    )
    if not os.path.exists(arff_path):
        raise FileNotFoundError(f"URL dataset not found at {arff_path}")

    df = parse_arff(arff_path)

    # In ARFF, 'Result' column is the target. Values: -1 (phishing), 1 (legitimate)
    # We want Phishing (threat) to be 1, and Legitimate (safe) to be 0 for XGBoost
    # Convert Result: 1 -> 0 (Legitimate), -1 -> 1 (Phishing)
    X = df.drop(columns=["Result"])
    y = df["Result"].map({1: 0, -1: 1})

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"X_train shape: {X_train.shape}, X_test shape: {X_test.shape}")
    print(f"Class distribution: Phishing={sum(y == 1)}, Legitimate={sum(y == 0)}")

    # Train XGBoost model
    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    # Evaluate
    preds = model.fit(X_train, y_train).predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"URL model test accuracy: {acc * 100:.2f}%")
    print(classification_report(y_test, preds, target_names=["Legitimate", "Phishing"]))

    # Save model and feature names
    models_dir = os.path.abspath(os.path.join(script_dir, "..", "models"))
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "url_classifier.pkl")

    # Save both model and the list of features it expects
    model_data = {"model": model, "features": list(X.columns)}
    with open(model_path, "wb") as f:
        pickle.dump(model_data, f)
    print(f"Saved URL model to {model_path}")


def train_message_model():
    print("\n--- Training Message Spam/Phishing Model ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sms_path = os.path.abspath(
        os.path.join(
            script_dir, "..", "datasets", "messages", "smsspam", "SMSSpamCollection"
        )
    )
    if not os.path.exists(sms_path):
        raise FileNotFoundError(f"SMS Spam dataset not found at {sms_path}")

    data = []
    with open(sms_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                label, message = parts
                # ham -> 0 (Legitimate), spam -> 1 (Spam/Phishing)
                label_val = 1 if label.lower() == "spam" else 0
                data.append((message, label_val))

    df = pd.DataFrame(data, columns=["message", "label"])
    print(f"Loaded {df.shape[0]} SMS samples.")

    X_train, X_test, y_train, y_test = train_test_split(
        df["message"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )

    print(f"X_train shape: {X_train.shape}, X_test shape: {X_test.shape}")
    print(
        f"Class distribution: Spam={sum(df['label'] == 1)}, Ham={sum(df['label'] == 0)}"
    )

    # Pipeline with TF-IDF and Logistic Regression
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=5000, ngram_range=(1, 2), stop_words="english"
                ),
            ),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )

    pipeline.fit(X_train, y_train)

    # Evaluate
    preds = pipeline.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Message model test accuracy: {acc * 100:.2f}%")
    print(classification_report(y_test, preds, target_names=["Ham", "Spam"]))

    # Save model
    models_dir = os.path.abspath(os.path.join(script_dir, "..", "models"))
    model_path = os.path.join(models_dir, "message_classifier.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"Saved Message model to {model_path}")


if __name__ == "__main__":
    train_url_model()
    train_message_model()

    # Import and train the deepfake model
    try:
        from services.deepfake_model import train_deepfake_model

        print("\n--- Training Deepfake CNN Classifier ---")
        train_deepfake_model()
    except Exception as e:
        print(f"Error training deepfake model: {e}")
