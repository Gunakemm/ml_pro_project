from typing import Any

from pydantic import BaseModel, Field


class Features(BaseModel):
    model_config = {'extra': "forbid"}

    track_name: str
    artist: str
    genre: str
    release_year: int | None = Field(ge=2015, le=2025)
    duration_sec: int | None = Field(ge=0, le=600)
    danceability: float | None = Field(ge=0.0, le=1.0)
    energy: float | None = Field(ge=0.0, le=1.0) 
    valence: float | None = Field(ge=0.0, le=1.0) 
    tempo_bpm: float | None = Field(ge=0.0, le=250) 
    acousticness: float | None = Field(ge=0.0, le=1.0) 
    instrumentalness: float | None = Field(ge=0.0, le=1.0) 
    speechiness: float | None = Field(ge=0.0, le=1.0) 
    liveness: float | None = Field(ge=0.0, le=1.0) 
    loudness_db: float | None = Field(le=0.0) 


class Prediction(BaseModel):
    model_version: str
    request_id: str
    features: dict[str, Any]
    score: float
    viral: bool
    latency_ms: float
    status_code: int