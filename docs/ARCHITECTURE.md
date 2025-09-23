# Skynet RC1 - Simplified Microservices Architecture

## Overview
Skynet RC1 maintains the microservices architecture and Qdrant vector database from the original Skynet, but with significant simplifications to reduce complexity while preserving scalability and maintainability.

## Architecture Principles
- **Simplified Microservices**: Reduced from 8+ services to 4 core services
- **Qdrant Vector Database**: Maintained for superior vector operations
- **Essential Features Only**: Core RAG chat functionality
- **Easy Deployment**: Docker Compose with clear service boundaries
- **No Over-Engineering**: Simplified service discovery and configuration

## System Components

### Core Services (4 Services)

#### 1. Frontend Service (Django)
- **Purpose**: Web UI and user management
- **Port**: 8080
- **Responsibilities**:
  - User authentication and session management
  - Web interface for chat and document management
  - Basic user administration

#### 2. API Gateway Service
- **Purpose**: Central routing and orchestration
- **Port**: 8000
- **Responsibilities**:
  - Route requests to appropriate services
  - Authentication middleware
  - Request/response coordination
  - Load balancing (simplified)

#### 3. Document Processing Service
- **Purpose**: Document handling and vectorization
- **Port**: 8001
- **Responsibilities**:
  - File upload and storage
  - Text extraction (PDF, Word, Text)
  - Text chunking and embedding generation
  - Qdrant collection management

#### 4. AI Chat Service
- **Purpose**: RAG and chat functionality
- **Port**: 8002
- **Responsibilities**:
  - Vector search in Qdrant
  - Context retrieval and ranking
  - Ollama integration for response generation
  - Chat session management

### Infrastructure (Unchanged)
1. **Qdrant Vector Database**: Semantic search and embeddings (Port 6333)
2. **PostgreSQL**: User data and metadata (Port 5432)
3. **Redis**: Session storage and caching (Port 6379)
4. **Ollama**: Local LLM processing (Port 11434)

### Removed Complexity
- ❌ Complex authentication service (merged into frontend)
- ❌ Separate embedding service (merged into document service)
- ❌ Module plugin system
- ❌ Service registry and discovery
- ❌ MinIO object storage (→ local filesystem)
- ❌ Prometheus/Grafana monitoring
- ❌ Advanced RAG strategies (initially)
- ❌ Circuit breakers and retry logic

## Data Flow

```
User → Frontend → API Gateway → Document/AI Services → Qdrant/Ollama
                      ↓
               PostgreSQL + Redis
```

## Service Communication

### Inter-Service Communication
- **HTTP REST APIs**: Simple request/response
- **Direct service calls**: No complex message queuing
- **Shared database**: PostgreSQL for user/session data
- **Shared cache**: Redis for cross-service caching

### API Endpoints
```
Frontend Service:
  GET  /                    # Web interface
  POST /auth/login          # User authentication
  GET  /chat                # Chat interface
  GET  /documents           # Document management

API Gateway:
  POST /api/upload          # → Document Service
  POST /api/chat            # → AI Chat Service
  GET  /api/documents       # → Document Service
  GET  /api/search          # → AI Chat Service

Document Service:
  POST /process             # Document processing
  GET  /documents           # List user documents
  GET  /chunks/{doc_id}     # Get document chunks

AI Chat Service:
  POST /chat                # Generate chat response
  POST /search              # Vector search
  GET  /sessions            # Chat sessions
```

## File Structure
```
skynet-rc1/
├── services/
│   ├── frontend/           # Django web interface
│   ├── gateway/            # API Gateway
│   ├── document/           # Document processing
│   └── ai-chat/            # AI Chat & RAG
├── infrastructure/
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── init-scripts/
├── shared/
│   ├── models/             # Shared data models
│   └── utils/              # Common utilities
└── docs/
```

## Features

### Phase 1 Features (MVP)
- ✅ User authentication (Django built-in)
- ✅ Document upload and processing
- ✅ Vector embeddings and Qdrant storage
- ✅ Basic RAG chat interface
- ✅ Microservices architecture
- ✅ Simple web UI

### Phase 2 Features (Future)
- Advanced RAG strategies
- Response improvement system
- User collections/workspaces
- API rate limiting
- Basic monitoring dashboard

## Deployment Benefits

### Maintained Benefits
- **Scalability**: Each service can scale independently
- **Technology Flexibility**: Services can use different tech stacks
- **Fault Isolation**: Service failures don't cascade
- **Development Speed**: Teams can work on services independently
- **Superior Vector Operations**: Qdrant provides better performance than pgvector

### Simplified Operations
- **Reduced Services**: 4 services instead of 8+
- **Simpler Configuration**: Environment-based setup
- **Direct Communication**: No complex service mesh
- **Faster Deployment**: Fewer moving parts

## Deployment

Single Docker Compose file manages all services with clear dependencies and simplified networking.