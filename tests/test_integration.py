import os

import psycopg
import pytest

DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="нужен Postgres: задайте DATABASE_URL")
]

def test_prediction_is_logged(client, good_row):
    body = client.post("/v1/predict", json=good_row).json()

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT model_version, score, features->>'valence', status_code "
            "FROM predictions WHERE request_id = %s",
            (body["request_id"],),
        ).fetchone()

        assert row is not None
        assert row[0] == body["model_version"]
        assert row[1] == pytest.approx(body["score"])
        assert row[2] == str(good_row["valence"])

def test_garbage_request(client, good_row):
    request = client.post("/v1/predict", json={**good_row, "release_year": 3026})

    assert request.status_code == 422

    request_body = request.json()
    
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT model_version, score, status_code "
            "FROM predictions WHERE request_id =%s",
            (request_body["request_id"],),
        ).fetchone()

    assert row is not None
    assert row[0] == request_body["model_version"]
    assert row[1] == 0.0
    assert row[2] == 422