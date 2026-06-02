FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# tzdata for IANA zones (Asia/Almaty); gosu drops privileges from entrypoint
RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata gosu \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY tests/ ./tests/
COPY .env.example .
COPY .gitignore .
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN useradd --create-home --uid 1000 app \
 && mkdir -p /data \
 && chown -R app:app /app /data \
 && chmod +x /usr/local/bin/docker-entrypoint.sh

# Stay root for entrypoint; entrypoint chowns /data then drops to `app` via gosu.
EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
