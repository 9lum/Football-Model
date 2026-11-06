FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
COPY intelligence/requirements.txt intelligence/requirements.txt
RUN pip install --no-cache-dir -r intelligence/requirements.txt
COPY edge edge
COPY intelligence intelligence
COPY scripts/refresh_odds.py scripts/refresh_game_odds.py scripts/refresh_public_game_odds.py scripts/
CMD ["uvicorn","intelligence.api:app","--host","0.0.0.0","--port","8000"]
