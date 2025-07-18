# app/Dockerfile

FROM python:3.9-slim

WORKDIR /app

# Systemabhängigkeiten + uv installieren
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Projektdateien in Container kopieren
COPY . .

# Python Dependencies installieren mit uv
RUN uv sync

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["uv","run","streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
