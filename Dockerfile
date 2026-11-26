FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/AI4WORK-Project/logistics-scheduler" \
      org.opencontainers.image.description="Human-Aware Task Planner – Logistics Yard Management" \
      org.opencontainers.image.licenses="EPL-2.0"

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update \ 
  && apt-get -y install --no-install-recommends netcat-openbsd \
  && apt-get autoremove -y \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*
ENV DEBIAN_FRONTEND=dialog

WORKDIR /app

# Install the dependencies first, so that changing only the code does not
# reinstall them
COPY pyproject.toml /app/
RUN pip install /app/

# Install the logistics package
COPY LICENSE NOTICE /app/
COPY logistics/ /app/logistics/
RUN pip install --no-deps /app/
COPY server.py service.py kafka_worker.py kafka_client.py /app/

# Expose the port of the server
EXPOSE 5000

# Report the container as unhealthy if the server stops answering
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=4)"

# Run the server, with the Kafka consumer if KAFKA_BOOTSTRAP_SERVER is set
CMD ["python", "server.py"]
