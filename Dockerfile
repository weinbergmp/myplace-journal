FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

RUN chmod +x start.sh

ENV FLASK_APP=wsgi.py
# DATABASE_URL is set via fly.toml [env] to use the persistent volume
ENV DATABASE_URL=sqlite:////data/journal.db

EXPOSE 8080

CMD ["./start.sh"]
