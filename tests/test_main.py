"""
Tests automatisés validant le comportement de l'API et l'interaction avec Redis.
"""
import hashlib
import pytest
from fastapi.testclient import TestClient

from app.main import app, redis_client
from app.parser import analyze_text


@pytest.fixture(scope="module")
def client():
    """Client de test FastAPI."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_redis():
    """Nettoie les clés de cache de test dans Redis avant chaque test."""
    try:
        redis_client.ping()
        # Supprime uniquement les clés préfixées par cache:phrase:
        keys = redis_client.keys("cache:phrase:*")
        if keys:
            redis_client.delete(*keys)
    except Exception:
        # Si Redis n'est pas démarré (ex. tests unitaires purs), on ignore
        pass
    yield


def test_parser_unit():
    """Test unitaire du moteur d'analyse textuelle."""
    result = analyze_text("Bonjour le monde !")
    assert result["word_count"] == 3
    assert result["char_count"] == 18
    assert result["char_count_no_spaces"] == 15
    assert result["longest_word"] == "Bonjour"
    assert result["vowels_count"] == 6  # o, u, o, e, o, e
    assert result["avg_word_length"] == 4.67


def test_parser_empty():
    """Test unitaire sur texte vide."""
    result = analyze_text("")
    assert result["word_count"] == 0
    assert result["char_count"] == 0
    assert result["longest_word"] == ""


def test_root_endpoint(client):
    """Vérifie la disponibilité et la structure de l'accueil."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "endpoints" in data


def test_healthcheck(client):
    """
    Vérifie l'endpoint /health.
    Doit valider que l'API et Redis sont tous deux opérationnels.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["redis"] == "ok"
    assert "version" in data


def test_analyze_sentence_and_redis_cache(client):
    """
    Test d'intégration complet :
    1. Premier appel : calcul réel, interaction avec Redis (écriture en cache).
    2. Vérification directe dans Redis.
    3. Deuxième appel identique : servi depuis le cache Redis (cached=True).
    """
    phrase = "DevOps transforme la livraison logicielle"
    payload = {"text": phrase}

    # 1er appel : Pas encore en cache
    response1 = client.post("/analyze", json=payload)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["original_text"] == phrase
    assert data1["metrics"]["word_count"] == 5
    assert data1["cached"] is False

    # Vérification directe dans le service Redis
    expected_cache_key = f"cache:phrase:{hashlib.sha256(phrase.encode('utf-8')).hexdigest()}"
    raw_in_redis = redis_client.get(expected_cache_key)
    assert raw_in_redis is not None, "La phrase doit être stockée dans Redis"

    # 2ème appel : Doit provenir du cache Redis
    response2 = client.post("/analyze", json=payload)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["cached"] is True
    assert data2["metrics"]["word_count"] == 5


def test_analyze_empty_payload(client):
    """Vérifie le rejet d'une phrase vide (code 400)."""
    response = client.post("/analyze", json={"text": "   "})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_metrics_prometheus_endpoint(client):
    """
    Vérifie que l'endpoint /metrics expose correctement les métriques
    attendues au format texte Prometheus.
    """
    # Génère du trafic pour alimenter les métriques
    client.get("/health")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    content = response.text

    # Vérification des trois métriques obligatoires du sujet
    assert "http_requests_total" in content
    assert "http_request_duration_seconds" in content
    assert "app_version_info" in content
