FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for Pillow and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy all application files first
COPY . .

# Install pip and uv
RUN pip install --no-cache-dir uv

# Install dependencies
RUN uv pip install --no-cache .

# Create cache directory
RUN mkdir -p cache/grid

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["python", "src/main.py"]