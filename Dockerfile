# Stage 1: Builder
FROM python:3.12-slim AS builder

# Install Git (Required by gitpython)
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Install build dependencies
RUN pip install --no-cache-dir build==1.3.0

# Set the working directory
WORKDIR /app

# Copy the project files
COPY pyproject.toml .
COPY src/ ./src/
COPY README.md .
COPY LICENSE .

# Build the wheel
RUN python -m build --wheel --outdir /wheels


# Stage 2: Runtime
FROM python:3.12-slim AS runtime

RUN apt-get update && \
    apt-get install -y \
    git \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libglib2.0-0 \
    libjpeg62-turbo && \
    rm -rf /var/lib/apt/lists/
    
# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Add user's local bin to PATH
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Set the working directory
WORKDIR /home/appuser/app

# Copy the wheel from the builder stage
COPY --from=builder /wheels /wheels

# Copy local dependencies (Coreason Identity)
COPY libs/ /libs/

# Install the application wheel
RUN pip install --no-cache-dir /wheels/*.whl

# Expose port 8001
EXPOSE 8001

# Updated CMD for server mode
CMD ["uvicorn", "coreason_scribe.server:app", "--host", "0.0.0.0", "--port", "8001"]
