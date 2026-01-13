FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy project requirements first to leverage Docker cache
COPY pyproject.toml .

# Install debugpy for remote debugging
RUN pip install --no-cache-dir debugpy

# Install project dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir ".[rag]"  # Install with rag dependencies

# Copy the rest of the application
COPY . .

# Expose the application port
EXPOSE 11555

# Command to run the application - use PYTHONPATH to include src directory
CMD ["sh", "-c", "PYTHONPATH=/app/src:$PYTHONPATH python main.py"]