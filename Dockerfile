# ==========================================
# Stage 1: Build Frontend (Vite + React)
# ==========================================
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend

# Copy package files first for better caching
COPY frontend/package*.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Run Backend (FastAPI)
# ==========================================
FROM python:3.11-slim

WORKDIR /app

# Install dependencies (requirements.txt is at root level)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend assets to the static directory
# main.py expects static files in ./static relative to itself
COPY --from=frontend-build /app/frontend/dist /app/static

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
# We use python main.py to leverage the port configuration logic in the script
CMD ["python", "main.py"]
