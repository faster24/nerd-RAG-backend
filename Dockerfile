# Stage 1: Builder
FROM python:3.10-slim as builder

WORKDIR /app

# Install build-time system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment for isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
# Optimization: Install CPU-only PyTorch first to avoid massive CUDA downloads
RUN pip install --upgrade pip && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install redis==5.0.1 && \
    pip install -r requirements.txt

# Stage 2: Runtime (Final Image)
FROM python:3.10-slim

WORKDIR /app

# Install only necessary runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the application code
COPY . .

# Ensure the app can read the Firebase credentials
RUN chmod 644 firebase_credential.json

EXPOSE 8000

# Use the virtual environment's uvicorn to run the app
CMD ["uvicorn", "manage:app", "--host", "0.0.0.0", "--port", "8000"]