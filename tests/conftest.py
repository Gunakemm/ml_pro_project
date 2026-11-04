import pytest
from fastapi.testclient import TestClient

from viral_song.service.app import app

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture()
def good_row():
    return {
        "track_name": "Track_00001",
        "artist": "Artist_3228",
        "genre": "Pop",
        "release_year": 2017,
        "duration_sec": 180,
        "danceability": 0.45,
        "energy": 0.754,
        "valence": 0.5,
        "tempo_bpm": 120.0,
        "acousticness": 0.309,
        "instrumentalness": 0.52,
        "speechiness": 0.145,
        "liveness": 0.234,
        "loudness_db": -8.95
    }