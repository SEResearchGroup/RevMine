FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system revmine && useradd --system --gid revmine --home-dir /app revmine

COPY --chmod=0444 requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=revmine:revmine --chmod=0444 main.py .
COPY --chown=revmine:revmine --chmod=0555 gateway ./gateway

USER revmine

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
