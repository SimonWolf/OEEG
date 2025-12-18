# app/Dockerfile

FROM python:3.12-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

# Systemabhängigkeiten + uv installieren
RUN apt-get update && apt-get install -y \
    build-essential \
    lsb-release \
    apt-transport-https \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* 

RUN pip install uv

# Projektdateien in Container kopieren
COPY . .

# Python Dependencies installieren mit uv
RUN uv sync

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
RUN uv run CRON_UPDATE.py 
ENTRYPOINT ["uv","run","streamlit", "run", "streamlit_main.py", "--server.port=8501", "--server.address=0.0.0.0"]
