FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# RUN chmod +x wait-for-db.sh

EXPOSE 8000

CMD ["python", "manage.py", "makemigrations", "--noinput"]
CMD ["python", "manage.py", "migrate", "--noinput"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

