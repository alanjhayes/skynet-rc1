# Skynet RC1 - Document Intelligence Platform

[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docker.com)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2-green)](https://djangoproject.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)](https://fastapi.tiangolo.com)

Skynet RC1 is an enterprise-grade document intelligence platform that combines **RAG (Retrieval-Augmented Generation)** with **flexible authentication** and **advanced security features**. It allows organizations to upload documents, extract knowledge, and interact with their document collections through an AI-powered chat interface.

## Features

### **Enterprise Authentication**
- **Flexible LDAP/Active Directory Integration** - Optional, configurable via environment variables
- **JWT Token Authentication** - Secure API access with automatic token refresh
- **Role-Based Access Control** - Admin, Staff, User, and Readonly permissions
- **Session Fallback** - Graceful degradation when JWT packages aren't available
- **User Isolation** - Each user gets their own secure document collection

### **Document Processing**
- **Multi-Format Support** - PDF, Word documents, text files, Markdown
- **Intelligent Text Extraction** - Handles complex document layouts
- **Vector Embeddings** - TF-IDF based lightweight embeddings for fast search
- **Chunking & Overlap** - Smart text chunking with configurable overlap
- **Async Processing** - Non-blocking document processing pipeline

### **AI-Powered Chat**
- **RAG Chat Interface** - Ask questions about uploaded documents
- **Context-Aware Responses** - AI understands document context
- **Source Attribution** - Shows which documents were used in responses
- **Session Management** - Persistent chat sessions with history
- **Real-time Processing** - Live chat with typing indicators

### **Security & Compliance**
- **Document-Level Permissions** - Users can only access their own documents
- **Comprehensive Audit Logging** - All document access and user actions logged
- **CSRF Protection** - Protection against cross-site request forgery
- **Secure Headers** - XSS protection and security headers
- **Permission Matrix** - Granular permissions based on user roles

## **Prerequisites**

- **Docker** and **Docker Compose**
- **4GB+ RAM** (recommended for AI models)
- **10GB+ Storage** (for documents and vector databases)

## **Quick Start**

### 1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/skynet-rc1.git
cd skynet-rc1
```

### 2. **Configure Environment**
```bash
# Copy environment configuration from project root
cp .env.example .env

# Edit configuration for your needs  
nano .env
```

The `.env.example` file contains comprehensive configuration options with detailed comments. Here are the key settings:

**Required Settings:**
- `POSTGRES_PASSWORD` - Database password
- `SECRET_KEY` - Django secret key (change in production!)
- `OLLAMA_MODEL` - AI model to download (default: llama3.1:8b)

**Authentication Options:**
- `JWT_ENABLED=true` - Enable JWT token authentication
- `LDAP_ENABLED=false` - Enable Active Directory integration

**Basic Configuration (Local Users + JWT):**
```bash
POSTGRES_PASSWORD=skynet_password
SECRET_KEY=django-insecure-change-this-in-production
OLLAMA_MODEL=llama3.1:8b
JWT_ENABLED=true
LDAP_ENABLED=false
```

**Enterprise Configuration (LDAP + JWT):**
```bash
POSTGRES_PASSWORD=your-secure-password
SECRET_KEY=your-super-secure-django-key
OLLAMA_MODEL=llama3.1:8b
JWT_ENABLED=true
LDAP_ENABLED=true
LDAP_SERVER_URI=ldap://your-ad-server.company.com:389
LDAP_BIND_DN=cn=service-account,ou=service-accounts,dc=company,dc=com
LDAP_BIND_PASSWORD=your-service-account-password
# ... see .env.example for full LDAP configuration
```

**Important:** 
- The `.env` file must be in the **project root directory** (same level as this README.md file)
- The `.env.example` file is now located in the project root with all configuration options
- See the `.env.example` file for complete configuration documentation

### 3. **Start the Platform**

**Recommended (Smart Startup):**
```bash
cd infrastructure
./start.sh
```

**Manual Startup:**
```bash
cd infrastructure
docker-compose up -d
```

**Troubleshooting Port Conflicts:**
If you encounter port binding errors:
```bash
# Stop any running services
docker-compose down

# Check what's using the ports
sudo netstat -tulpn | grep ':8080\|:8000\|:80'

# Start with the smart script
./start.sh
```

### 4. **Access the Platform**
- **Web Interface**: http://localhost
- **API Documentation**: http://localhost/api/docs
- **Admin Interface**: http://localhost/admin

## **Configuration Options**

### Authentication Modes

| Mode | LDAP_ENABLED | JWT_ENABLED | Use Case |
|------|--------------|-------------|----------|
| **Local + JWT** | `false` | `true` | Small teams, development |
| **LDAP + JWT** | `true` | `true` | Enterprise with AD |
| **LDAP + Sessions** | `true` | `false` | Legacy enterprise |
| **Local + Sessions** | `false` | `false` | Minimal setup |

## **Documentation**

- **[Authentication Guide](infrastructure/AUTHENTICATION.md)** - Complete authentication setup

## **Architecture Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   AI Chat       │    │   Document      │
│   (Django)      │    │   (FastAPI)     │    │   (FastAPI)     │
│ • Web Interface │    │ • RAG Chat      │    │ • File Upload   │
│ • Authentication│    │ • Ollama LLM    │    │ • Text Extract  │
│ • Session Mgmt  │    │ • Context Mgmt  │    │ • Embeddings    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   API Gateway   │
                    │   (FastAPI)     │
                    │ • Route Mgmt    │
                    │ • Load Balance  │
                    │ • Rate Limiting │
                    └─────────────────┘
```

## **Services**

| Service | Port | Description |
|---------|------|-------------|
| **nginx** | 80 | Reverse proxy and load balancer |
| **frontend** | 8080 | Django web interface |
| **gateway** | 8001 | FastAPI API gateway |
| **ai-chat** | 8002 | AI chat service with Ollama |
| **document** | 8003 | Document processing service |
| **postgres** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache and sessions |
| **qdrant** | 6333 | Vector database |
| **ollama** | 11434 | AI model server |

## **Security Features**

- **JWT Token Security**: 60-minute access tokens, 7-day refresh tokens with rotation
- **LDAP Integration**: Secure binding with service accounts, group caching
- **Document Isolation**: User-specific Qdrant collections (`user_username_documents`)
- **Audit Trail**: Complete logging of document access and user actions
- **Permission Checks**: Document-level access control with role validation
- **CSRF Protection**: All forms protected against cross-site request forgery

## **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## **License**

This project is licensed under the MIT License.

---

**Built with care for enterprise document intelligence**