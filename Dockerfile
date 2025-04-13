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

# Copy only dependency files first
COPY pyproject.toml uv.lock ./

# Install pip and uv
RUN pip install --no-cache-dir uv

# Install dependencies
RUN uv pip install --system

# Copy the rest of the application code
COPY . .

# Create cache directory
RUN mkdir -p cache/grid

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["python", "src/main.py"]