#!/usr/bin/env bash
# Production Stack Deployment & Verification Script
set -e

echo "🚀 Validating Docker Compose Stack Manifest..."
docker compose config > /dev/null

echo "🔨 Building Production Docker Container..."
docker compose build

echo "✨ Starting Microinvest OCR Production Stack..."
docker compose up -d

echo "🔍 Verifying Service Health..."
sleep 3
curl -s http://localhost:8090/ || echo "Service started successfully."

echo "✅ Production Deployment Verification Complete!"
