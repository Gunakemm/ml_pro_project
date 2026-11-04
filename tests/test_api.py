def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert "model_version" in r.json()

def test_ready(client):
    assert client.get("/ready").status_code == 200

def test_bad_release_year_is_422(client, good_row):
    r = client.post("/v1/predict", json={**good_row, "release_year": 1974})
    assert r.status_code == 422

def test_missing_field_is_422(client, good_row):
    row = dict(good_row)
    del row["tempo_bpm"]
    assert client.post("/v1/predict",json=row).status_code == 422

def test_extra_field_is_422(client, good_row):
    r = client.post("/v1/predict", json={**good_row, "unknown_feature": 0.0})
    assert r.status_code == 422