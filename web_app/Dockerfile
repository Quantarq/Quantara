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

# Install Poetry
RUN pip install poetry

# Copy necessary files
COPY ./pyproject.toml /app
ADD . /app

# Install Python dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Install StarknetKit via npm
RUN npm install @argent/get-starknet --save

# Expose port 8000 for FastAPI
EXPOSE 8000

# Entry point script
ENTRYPOINT ["bash", "/app/entrypoint.sh"]