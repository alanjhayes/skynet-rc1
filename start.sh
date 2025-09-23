#!/bin/bash

# Skynet RC1 Startup Script

echo "🚀 Starting Skynet RC1..."
echo "=========================================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Navigate to infrastructure directory
cd infrastructure

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Please edit .env file with your configuration"
fi

# Start services
echo "🏗️  Building and starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."

services=("skynet-rc1-postgres" "skynet-rc1-redis" "skynet-rc1-qdrant" "skynet-rc1-ollama" "skynet-rc1-frontend" "skynet-rc1-gateway" "skynet-rc1-document" "skynet-rc1-ai-chat" "skynet-rc1-nginx")

for service in "${services[@]}"; do
    if docker ps --filter "name=$service" --filter "status=running" | grep -q $service; then
        echo "✅ $service is running"
    else
        echo "❌ $service is not running"
    fi
done

echo ""
echo "🎯 Service URLs:"
echo "=========================================="
echo "Web Interface:     http://localhost"
echo "Frontend Direct:   http://localhost:8080"
echo "API Gateway:       http://localhost:8000"
echo "Document Service:  http://localhost:8001"
echo "AI Chat Service:   http://localhost:8002"
echo "Admin Interface:   http://localhost:8080/admin"
echo ""

echo "📋 Next Steps:"
echo "=========================================="
echo "1. Download Ollama model:"
echo "   docker exec skynet-rc1-ollama ollama pull llama3.1:8b"
echo ""
echo "2. Create admin user:"
echo "   docker exec -it skynet-rc1-frontend python manage.py createsuperuser"
echo ""
echo "3. View logs:"
echo "   docker-compose logs -f"
echo ""

echo "🎉 Skynet RC1 is starting up!"
echo "Visit http://localhost to get started"