FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends netcat-traditional && rm -rf /var/lib/apt/lists/*

RUN groupadd --system revmine && useradd --system --gid revmine --home-dir /app revmine

COPY --chmod=0444 requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=revmine:revmine --chmod=0444 manage.py .
COPY --chown=revmine:revmine --chmod=0555 analyze_service ./analyze_service
COPY --chown=revmine:revmine --chmod=0555 analytics ./analytics
COPY --chown=revmine:revmine --chmod=0555 kafka_utils ./kafka_utils

# Pre-create media directory owned by the app user so Docker can seed
# the named volume with the correct ownership on first run.
RUN mkdir -p /app/media/datasets && chown -R revmine:revmine /app/media

USER revmine

EXPOSE 8003

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8003"]
