FROM python:3.11-slim

WORKDIR /app

# Copy backend sources from this context's `app/` folder
COPY app/ ./backend/

# Install runtime requirements (requirements.txt present in this context)
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/backend
EXPOSE 8000

# Run uvicorn; uses `app.main:app` as entrypoint inside backend package
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
