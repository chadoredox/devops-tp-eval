# Sentence Analyzer API

API REST développée avec **FastAPI** permettant d'analyser des phrases et d'extraire des métriques textuelles (comptage de mots, voyelles, consonnes, mot le plus long).

L'application intègre un **cache Redis** pour accélérer les requêtes récurrentes et expose des métriques au format **Prometheus** pour le monitoring.

---

## 1. Architecture

- **`api`** : Service web FastAPI exposé sur le port `8000`.
- **`redis`** : Base de données en mémoire (port `6379`) servant de cache applicatif avec TTL de 1 heure.
- **`prometheus`** : Serveur de métriques (port `9090`) qui scrape `/metrics` toutes les 5 secondes et évalue les règles d'alerte.

---

## 2. Lancement en Local

### Option A : Avec Docker Compose

Construit les images et démarre l'ensemble de la stack (API, Redis et Prometheus) en une seule commande :

```bash
docker compose up --build -d
```

Vérifier l'état des services et des healthchecks :
```bash
docker compose ps
```

Consulter les logs de l'API :
```bash
docker compose logs -f api
```

Arrêter les services :
```bash
docker compose down
```



## 3. Endpoints de l'API

### Accueil (`GET /`)
```bash
curl -s http://localhost:8000/
```

### Vérification de santé (`GET /health`)
Vérifie la disponibilité de l'API ainsi que la connectivité avec Redis :
```bash
curl -s http://localhost:8000/health
```

### Analyse de phrase (`POST /analyze`)
```bash
curl -s -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"DevOps ameliore la livraison logicielle\"}"
```
- **Premier appel** : la phrase est analysée et enregistrée dans le cache Redis (`"cached": false`).
- **Appels suivants identiques** : le résultat est directement renvoyé depuis Redis (`"cached": true`).

### Métriques Prometheus (`GET /metrics`)
Expose les métriques applicatives au format texte Prometheus :
```bash
curl -s http://localhost:8000/metrics
```
L'interface web de Prometheus est accessible sur `http://localhost:9090` (et les alertes sur `http://localhost:9090/alerts`).

---

## 4. Tests et Qualité de Code

### Lancer les tests unitaires et d'intégration :
```bash
pytest -v --cov=app --cov-report=term-missing
```

### Linter Python (Flake8) :
```bash
flake8 app/ tests/ --count --max-line-length=120 --statistics
```

### Linter YAML (yamllint) :
```bash
yamllint -c .yamllint.yml .github/ docker-compose.yml alerts/
```
