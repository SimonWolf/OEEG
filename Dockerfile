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
    cron \
    && rm -rf /var/lib/apt/lists/* 

RUN pip install uv

# Projektdateien in Container kopieren
COPY . .

# Python Dependencies installieren mit uv
RUN uv sync

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
# Document persistent data path (mounted in deploy workflow)
VOLUME ["/data/delta-table"]

# Configure cron to run nightly update at 02:00
RUN touch /var/log/cron.log \
    && echo 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' > /etc/cron.d/oeeg \
    && echo 'SHELL=/bin/sh' >> /etc/cron.d/oeeg \
    && echo '0 2 * * * root cd / && uv run CRON_UPDATE.py >> /var/log/cron.log 2>&1' >> /etc/cron.d/oeeg \
    && chmod 0644 /etc/cron.d/oeeg

# Run data update at container start so writes go to the mounted volume,
# then launch the Streamlit app. Continue even if update fails.
ENTRYPOINT ["sh","-c","cron && (uv run CRON_UPDATE.py || true); exec uv run streamlit run streamlit_main.py --server.port=8501 --server.address=0.0.0.0"]
