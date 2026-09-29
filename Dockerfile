# ==========================================
# Étape 1 : Builder (Installation des dépendances)
# ==========================================
FROM python:3.11-slim-bookworm AS builder

# Empêcher Python d'écrire des fichiers .pyc et activer le buffer standard
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Création d'un environnement virtuel dédié pour isoler les packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copie et installation des dépendances de production
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================
# Étape 2 : Runner (Image d'exécution finale)
# ==========================================
FROM python:3.11-slim-bookworm AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

# Création d'un utilisateur non-root avec UID/GID explicite
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Récupération de l'environnement virtuel préparé dans l'étape builder
COPY --from=builder /opt/venv /opt/venv

# Copie du code source de l'application
COPY app/ /app/app/

# Attribution stricte des permissions à l'utilisateur non-root
RUN chown -R appuser:appgroup /app

# Bascule vers l'utilisateur non-root pour des raisons de sécurité
USER appuser

# Exposition du port applicatif
EXPOSE 8000

# Vérification de santé (HEALTHCHECK) reflétant l'état réel du service
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Commande de démarrage du serveur ASGI uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
