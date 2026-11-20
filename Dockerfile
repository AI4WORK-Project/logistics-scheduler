FROM python:3.10-slim

WORKDIR /app

# Install the logistics package and dependencies
COPY pyproject.toml /app/
RUN pip install /app/

COPY logistics/ /app/logistics/
COPY server.py /app/

# Expose the port of the server
EXPOSE 5000

# Run the server
CMD ["python", "server.py"]
