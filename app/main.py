"""
API FastAPI pour l'analyse de phrases avec cache Redis et métriques Prometheus.
"""
import hashlib
import json
import os
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
import redis
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from app.parser import analyze_text

# Configuration via variables d'environnement
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
COMMIT_SHA = os.getenv("COMMIT_SHA", "dev-local")

app = FastAPI(
    title="Sentence Analyzer API",
    description="API simple d'analyse de texte avec cache Redis et métriques Prometheus",
    version=APP_VERSION,
)

# Initialisation du client Redis
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    socket_timeout=2.0,
    socket_connect_timeout=2.0,
)

# --- Métriques Prometheus ---
# 1. Compteur de requêtes avec labels endpoint et code statut
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Nombre total de requetes HTTP recues",
    ["endpoint", "code"],
)

# 2. Histogramme de latence pour calcul des percentiles p95 / p99
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Duree de traitement des requetes HTTP en secondes",
    ["endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0],
)

# 3. Jauge exposant la version et le commit SHA déployé
APP_VERSION_INFO = Gauge(
    "app_version_info",
    "Version et commit SHA actuellement deployes",
    ["version", "commit_sha"],
)
APP_VERSION_INFO.labels(version=APP_VERSION, commit_sha=COMMIT_SHA).set(1)


# Middleware pour mesurer automatiquement la latence et compter les requêtes
@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    endpoint = request.url.path

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
    except Exception as exc:
        status_code = "500"
        # Enregistrement de la latence même en cas d'erreur
        duration = time.perf_counter() - start_time
        HTTP_REQUESTS_TOTAL.labels(endpoint=endpoint, code=status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(endpoint=endpoint).observe(duration)
        raise exc

    duration = time.perf_counter() - start_time
    HTTP_REQUESTS_TOTAL.labels(endpoint=endpoint, code=status_code).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(endpoint=endpoint).observe(duration)

    return response


# --- Modèles Pydantic ---
class TextPayload(BaseModel):
    text: str = Field(..., description="Phrase ou texte a analyser", min_length=1)


# --- Endpoints ---
@app.get("/")
def read_root():
    """Accueil et documentation rapide de l'API."""
    return {
        "service": "Sentence Analyzer API",
        "version": APP_VERSION,
        "commit_sha": COMMIT_SHA,
        "status": "running",
        "endpoints": {
            "/health": "Verification de l'etat de sante (API + Redis)",
            "/analyze": "Analyse d'une phrase (POST JSON avec {\"text\": \"...\"})",
            "/metrics": "Metriques au format texte Prometheus",
        },
    }


@app.get("/health")
def healthcheck():
    """
    Endpoint de santé vérifiant réellement la disponibilité du service
    et de sa dépendance Redis.
    """
    redis_status = "ok"
    try:
        redis_client.ping()
    except Exception as exc:
        redis_status = f"unreachable: {str(exc)}"
        # Si Redis n'est pas joignable, on renvoie une 503 Service Unavailable
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "redis": redis_status,
                "version": APP_VERSION,
                "commit_sha": COMMIT_SHA,
            },
        )

    return {
        "status": "healthy",
        "redis": redis_status,
        "version": APP_VERSION,
        "commit_sha": COMMIT_SHA,
    }


@app.post("/analyze")
def analyze(payload: TextPayload):
    """
    Analyse la phrase transmise.
    Vérifie d'abord si le résultat est déjà en cache Redis.
    Sinon, calcule l'analyse et la stocke avec un TTL de 1 heure.
    """
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Le texte a analyser ne peut pas etre vide.")

    # Création d'une clé de cache unique basée sur le hash SHA256 du texte
    cache_key = f"cache:phrase:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

    # Vérification dans Redis
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            result = json.loads(cached_data)
            result["cached"] = True
            return result
    except Exception:
        # Si Redis a un souci temporaire, on ne bloque pas l'utilisateur
        pass

    # Calcul de l'analyse textuelle
    analysis_stats = analyze_text(text)
    response_data = {
        "original_text": text,
        "metrics": analysis_stats,
        "cached": False,
    }

    # Sauvegarde dans Redis avec expiration (TTL = 3600 secondes)
    try:
        redis_client.setex(cache_key, 3600, json.dumps(response_data))
    except Exception:
        pass

    return response_data


@app.get("/metrics")
def get_metrics():
    """
    Endpoint de métriques au format texte brut Prometheus.
    """
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
