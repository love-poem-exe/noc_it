Minimalne pliki do budowania backendu `services/api`.

Jak użyć lokalnie (w katalogu repo):

```bash
# buduj obraz
docker build -t nocit-backend -f services/api/Dockerfile .

# uruchom obraz
docker run -p 8000:8000 nocit-backend
```

Uwaga: projekt nadal trzyma kod FastAPI w repo w katalogu `backend/`.
