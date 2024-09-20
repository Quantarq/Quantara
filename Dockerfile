# Use the Python 3.11 slim base image
FROM python:3.11-slim

# Environment settings
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Create app directory
RUN mkdir /app
WORKDIR /app

# Add system-level dependencies (including gcc and npm)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev gcc g++ make libffi-dev build-essential \
       curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements.txt to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies from requirements.txt and cache the layer
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the application code
ADD . /app

# Install StarknetKit via npm with legacy-peer-deps flag
RUN npm install @argent/get-starknet --legacy-peer-deps --save

# Expose port 8000 for FastAPI
EXPOSE 8000

# Entry point script
ENTRYPOINT ["bash", "/app/entrypoint.sh"]