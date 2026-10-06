FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update \ 
  && apt-get -y install --no-install-recommends netcat-openbsd \
  && apt-get autoremove -y \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*
ENV DEBIAN_FRONTEND=dialog

WORKDIR /app

COPY pyproject.toml /app/
COPY logistics/ /app/logistics/
COPY server.py /app/
COPY kafka_client.py /app/

# Install the logistics package and dependencies
RUN pip install /app/

# Expose the port of the server
EXPOSE 5000

# Run the server
CMD ["python", "server.py"]
