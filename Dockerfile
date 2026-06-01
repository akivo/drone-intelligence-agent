FROM python:3.10-slim

WORKDIR /app

# System dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# airsim connects to a host machine running AirSim; agent layer runs here
CMD ["python", "main.py"]
