FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV directly from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy all application files
COPY . .

# Install dependencies
RUN uv pip install --system .

# Create cache directory
RUN mkdir -p cache/grid

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["python", "src/main.py"]