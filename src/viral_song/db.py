import psycopg
from psycopg.types.json import Json

from viral_song.config import settings
from viral_song.scheme import Prediction

DDL = """
    CREATE TABLE IF NOT EXISTS predictions (
        request_id                  uuid PRIMARY KEY,
        ts                          timestamptz NOT NULL DEFAULT NOW(),
        model_version               text NOT NULL,
        features                    jsonb NOT NULL,
        score                       double precision NOT NULL,
        latency_ms                  real,
        status_code                 integer
    )
"""

def init() -> None:
    if not settings.database_url:
        return
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(8)")
        conn.execute(DDL)

def save_prediction(prediction: Prediction) -> None:
    if not settings.database_url:
        return
    with psycopg.connect(settings.database_url) as conn:
        query = """
            INSERT INTO predictions (request_id, model_version, features, score, latency_ms, status_code)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        conn.execute(
            query=query, 
            params=(
                prediction.request_id, 
                prediction.model_version,
                Json(prediction.features),
                prediction.score,
                prediction.latency_ms,
                prediction.status_code 
            )
        )