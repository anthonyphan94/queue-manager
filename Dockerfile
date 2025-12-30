# ========================================
# Stage 1: Build React Frontend
# ========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files first for better caching
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source and build
COPY frontend/ ./
RUN npm run build

# ========================================
# Stage 2: Production Python Image
# ========================================
# Stage 2: Production
FROM python:3.11-slim

WORKDIR /app

# 1. Copy nội dung Backend ra root của /app
COPY backend/ . 

# 2. Copy NỘI DUNG của thư mục dist (sau khi build) vào /app/static
# Lưu ý dấu / ở sau dist/ và static/ để copy nội dung, không copy cả folder
COPY --from=frontend-builder /app/frontend/dist/ ./static/

# 3. Cài đặt dependency và chạy app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
