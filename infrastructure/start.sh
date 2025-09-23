#!/bin/bash

# Skynet RC1 - Smart Startup Script
# This script handles port conflicts and ensures clean startup

set -e

echo "🚀 Skynet RC1 - Smart Startup Script"
echo "======================================"

# Function to check if a port is in use
check_port() {
    local port=$1
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to check if Docker Compose services are running
check_services_running() {
    if docker-compose ps --services --filter "status=running" 2>/dev/null | grep -q .; then
        return 0  # Services are running
    else
        return 1  # No services running
    fi
}

# Check if services are already running
if check_services_running; then
    echo "ℹ️  Services are already running. Current status:"
    docker-compose ps
    echo ""
    echo "🌐 Access URLs:"
    echo "   • Web Interface: http://localhost"
    echo "   • API Gateway: http://localhost:8000"
    echo "   • Frontend: http://localhost:8080"
    echo "   • Document Service: http://localhost:8001"
    echo "   • AI Chat Service: http://localhost:8002"
    echo ""
    echo "💡 To restart services, run: docker-compose restart"
    echo "💡 To stop services, run: docker-compose down"
    exit 0
fi

# Check for port conflicts
echo "🔍 Checking for port conflicts..."
ports_to_check=(80 5432 6333 6334 6379 8000 8001 8002 8080 11434)
conflicts=()

for port in "${ports_to_check[@]}"; do
    if check_port $port; then
        # Check if it's our own Docker container using the port
        if docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -q ":$port->"; then
            echo "⚠️  Port $port is used by existing Skynet RC1 container"
            conflicts+=($port)
        else
            echo "❌ Port $port is in use by another process"
            conflicts+=($port)
        fi
    fi
done

if [ ${#conflicts[@]} -gt 0 ]; then
    echo ""
    echo "🛑 Port conflicts detected on ports: ${conflicts[*]}"
    echo ""
    echo "🔧 To resolve this issue:"
    echo "   1. Stop conflicting services:"
    echo "      docker-compose down"
    echo ""
    echo "   2. Check what's using the ports:"
    echo "      sudo netstat -tulpn | grep ':<PORT>'"
    echo ""
    echo "   3. Kill conflicting processes if needed"
    echo ""
    echo "   4. Re-run this script"
    exit 1
fi

echo "✅ No port conflicts detected"
echo ""

# Start services
echo "🚀 Starting Skynet RC1 services..."
docker-compose up -d

# Wait a moment for services to start
echo "⏳ Waiting for services to initialize..."
sleep 5

# Show status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🎉 Skynet RC1 is starting up!"
echo ""
echo "🌐 Access URLs:"
echo "   • Web Interface: http://localhost"
echo "   • API Gateway: http://localhost:8000"
echo "   • Frontend: http://localhost:8080"
echo "   • Document Service: http://localhost:8001"
echo "   • AI Chat Service: http://localhost:8002"
echo ""
echo "📝 Logs: docker-compose logs -f"
echo "🛑 Stop: docker-compose down"