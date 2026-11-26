import json
import os
from pathlib import Path

import mlflow
import pandas as pd
import sklearn
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_PATH = Path(os.getenv("DATA_PATH", "datasets/viral_songs.csv"))
MODEL_NAME = os.getenv("MODEL_NAME", "viral_songs")
EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "viral_songs")
C = float(os.getenv("C", "1.0"))
MIN_GAIN = float(os.getenv("GATE_MIN_GAIN", "0.0"))
SEED = 42
SKOPS_TRUSTED = ["numpy.dtype", "sklearn.compose._column_transformer._RemainderColsList"]

NUMERIC = [
    'release_year', 'duration_sec', 'danceability', 'energy', 'valence', 'tempo_bpm', 
    'acousticness', 'instrumentalness', 'speechiness', 'liveness', 'loudness_db'
]
CATEGORICAL = ['track_name', 'artist', 'genre']

def load_and_validate(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = set(NUMERIC + CATEGORICAL + ["track_id", "streams", "viral"]) - set(df.columns)
    if missing:
        raise ValueError(f"в данных нет колонок: {sorted(missing)}")
    if len(df) < 1000:
        raise ValueError(f"слишком мало строк: {len(df)}")
    if not set(df["viral"].unique()) <= {0, 1}:
        raise ValueError(f"неожиданные значения таргета: {df['viral'].unique()[:5]}")
    return df

def build_pipeline(c: float) -> Pipeline:
    preprocess = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler())]), NUMERIC),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL),
    ])
    return Pipeline([("preprocess", preprocess), ("model", LogisticRegression(max_iter=1000, C=c))])

def champion_auc(client: MlflowClient) -> tuple[str | None, float | None]:
    try:
        mv = client.get_model_version_by_alias(MODEL_NAME, "champion")
    except MlflowException:
        return None, None
    return mv.version, client.get_run(mv.run_id).data.metrics.get("roc_auc")

def main() -> dict:
    df = load_and_validate(DATA_PATH)
    features = NUMERIC + CATEGORICAL
    x_train, x_test, y_train, y_test = train_test_split(
        df[features], df['viral'], test_size=0.2, stratify=df['viral'], random_state=SEED
    )

    pipeline = build_pipeline(C).fit(x_train, y_train)
    proba = pipeline.predict_proba(x_test)[:, 1]
    auc = float(roc_auc_score(y_test, proba))
    precision, recall, thresholds = precision_recall_curve(y_test, proba)
    thresholds = float(thresholds[recall[:-1] >= 0.70].max())

    mlflow.set_experiment(EXPERIMENT)
    client = MlflowClient()
    with mlflow.start_run() as run:
        metadata = {"features": features, "threshold": round(thresholds, 4), "n_train": len(x_train),
                    "data_rows": len(df), "sklearn": sklearn.__version__}
        mlflow.log_params({"C": C, "model": "LogisticRegression", "seed": SEED, "data": str(DATA_PATH)})
        mlflow.log_metrics({"roc_auc": auc, "pr_auc": float(average_precision_score(y_test, proba)), "threshold": thresholds})
        mlflow.log_dict(metadata, "metadata.json")
        info = mlflow.sklearn.log_model(pipeline, name="model", registered_model_name=MODEL_NAME,
                                        skops_trusted_types=SKOPS_TRUSTED)
        version = info.registered_model_version

    old_version, old_auc = champion_auc(client)
    promoted = old_auc is None or auc > old_auc + MIN_GAIN
    client.set_registered_model_alias(MODEL_NAME, "challenger", version)
    if promoted:
        client.set_registered_model_alias(MODEL_NAME, "champion", version)

    result = {"run_id": run.info.run_id, "version": version, "roc_auc": round(auc, 4),
              "champion_before": old_version, "champion_auc_before": old_auc, "promoted": promoted}
    print(json.dumps(result, ensure_ascii=False))
    xcom = Path("/airflow/xcom")
    if xcom.is_dir():
        (xcom / "return.json").write_text(json.dumps(result))
    return result

if __name__ == "__main__":
    main()