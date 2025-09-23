# 🚀 Skynet RC1 Quick Start

## One-Line Startup
```bash
cd ~/skynet-rc1 && ./start.sh
```

## Manual Setup

### 1. Start Services
```bash
cd ~/skynet-rc1/infrastructure
docker-compose up -d
```

### 2. Download AI Model
```bash
docker exec skynet-rc1-ollama ollama pull llama3.1:8b
```

### 3. Create Admin User
```bash
docker exec -it skynet-rc1-frontend python manage.py createsuperuser
```

### 4. Access Application
- **Web Interface**: http://localhost
- **Admin Panel**: http://localhost:8080/admin

## Architecture Summary

```
Frontend (Django) → API Gateway (FastAPI) → {Document Service, AI Chat Service}
       ↓                    ↓                            ↓
   PostgreSQL           Qdrant Vector DB            Ollama LLM
       ↓                    ↓                            ↓
     Redis Cache          + Nginx Proxy              
```

## Key Features
- ✅ **4 Microservices** (simplified from 8+)
- ✅ **Qdrant Vector Database** for superior search
- ✅ **Lightning Fast TF-IDF Embeddings** (no PyTorch!)
- ✅ **Document Processing** (PDF, Word, Text)
- ✅ **RAG Chat Interface** with context
- ✅ **User Authentication**
- ✅ **Complete Docker Deployment**

## Troubleshooting

**Services won't start:**
```bash
docker-compose logs -f
```

**Check service health:**
```bash
docker ps
```

**Reset everything:**
```bash
docker-compose down -v
docker-compose up -d
```

## What's Different from Original Skynet
- **Simplified**: 4 services instead of 8+
- **Maintained**: Microservices + Qdrant architecture  
- **Removed**: Complex auth, monitoring, module system
- **Easy**: Single docker-compose deployment