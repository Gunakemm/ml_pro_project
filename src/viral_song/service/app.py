import logging
import time
import uuid
from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from viral_song import db
from viral_song.config import settings
from viral_song.scheme import Features, Prediction

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("viral_song")

@asynccontextmanager
async def lifespan(app: FastAPI):
    bundle = joblib.load(settings.model_path)
    app.state.pipeline = bundle["pipeline"]
    app.state.meta = bundle["metadata"]
    app.state.version = bundle["metadata"]["model_version"]

    db.init()
    yield
    app.state.pipeline = None

app = FastAPI(title="viral-song-service", version="1.0", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok", "model_version": getattr(app.state, "version", "unknown")}


@app.get("/ready")
def ready():
    if getattr(app.state, "pipeline", None) is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ready"}

@app.post("/v1/predict")
def predict(x: Features, bg: BackgroundTasks) -> Prediction:
    t0 = time.perf_counter()
    request_id = str(uuid.uuid4())
    payload = x.model_dump()

    frame = pd.DataFrame([payload]).reindex(columns=app.state.meta["features"])
    score = float(app.state.pipeline.predict_proba(frame)[0, 1])
    viral = score >= app.state.meta["threshold"]

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    status_code = 200
    log.info("Single query latency_ms = %s", latency_ms)

    prediction = Prediction(
        model_version=app.state.version,
        request_id=request_id,
        features=payload,
        score=score,
        viral=viral,
        latency_ms=latency_ms,
        status_code=status_code
    )
    bg.add_task(db.save_prediction, prediction)
    return prediction

@app.exception_handler(RequestValidationError)
async def validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
    body = getattr(exc, "body", {})
    body = body if isinstance(body, dict) else {}

    log.warning("Validation error on %s %s: body=%s, errors=%s",
                request.method, request.url.path, body, exc.errors())

    request_id=str(uuid.uuid4())

    prediction = Prediction(
        request_id=request_id, 
        model_version=app.state.version,
        features=body,
        score=0.0,
        viral=None,
        latency_ms=None,
        status_code=422
        )

    bg = BackgroundTasks()
    bg.add_task(db.save_prediction, prediction)

    return JSONResponse(
        status_code=422,
        content={
            "request_id": request_id,
            "model_version": app.state.version,
            "detail": exc.errors()
        },
        background=bg
    )
