# Viral song service

Ссылка на данные: [What Makes a Song Go Viral?](https://www.kaggle.com/datasets/vedauv/what-makes-a-song-go-viral-10000-tracks?resource=download&select=viral_songs.csv)

Отчет к ДЗ: [docs/REPORT.md](docs/REPORT.md).

### 1. Тесты

```bash
uv sync
uv run pytest
```

### 2. Docker Compose

```bash
docker compose up -d --build
curl -X POST localhost:8000/v1/predict -H "Content-Type: application/json" -d @good.json
docker compose exec db psql -U postgres -d viral_song -c "SELECT request_id, score, latency_ms FROM predictions;"
```

### 3. Kind

```bash
docker build -t viral-song-service:1.0 .
kind create cluster --name viral-song
kind load docker-image viral-song-service:1.0 --name viral-song
kubectl apply -f k8s/
kubectl get pods
kubectl port-forward svc/viral-song-service 8080:80
```

В другом терминале:

```bash
 curl ‐X POST localhost:8080/v1/predict ‐H "Content‐Type: application/json" ‐d @good.json
```
