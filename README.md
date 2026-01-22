# DevOps Copilot - Automated Incident Management & Workflow Orchestration

![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)
![Celery](https://img.shields.io/badge/Celery-5.3-red.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![Redis](https://img.shields.io/badge/Redis-7-red.svg)

An intelligent DevOps assistant that automates incident response, postmortem generation, and knowledge base management through orchestrated workflows powered by AI.

## 📋 Table of Contents

- [Overview](#overview)
- [Problems Solved](#problems-solved)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Workflows](#workflows)
- [Development](#development)
- [Contributing](#contributing  )

---

## 🎯 Overview

DevOps Copilot is an AI-powered incident management system that automates  incident lifecycle—from initial response to postmortem documentation. Built with modern async workflows using Celery, it integrates with GitHub, ChromaDB for semantic search, and uses Claude AI for intelligent analysis and documentation generation.

### Built With

- **Backend**: Python 3.11, FastAPI (REST API)
- **Task Queue**: Celery with Redis broker
- **Databases**: PostgreSQL (relational), ChromaDB (vector embeddings)
- **AI/LLM**: Anthropic Claude API
- **Orchestration**: Docker Compose
- **Integrations**: GitHub API, Jinja2 templating

---

## 🔧 Problems Solved

### 1. **Manual Incident Response Overhead** ❌ → ✅
**Problem**: DevOps engineers spend valuable time during incidents performing repetitive tasks: analyzing logs, searching for runbooks, creating tracking issues, and sending notifications.

**Solution**: Automated incident response workflow that executes all these steps in parallel/sequence, reducing response time from hours to minutes.

### 2. **Inconsistent Postmortem Documentation** ❌ → ✅
**Problem**: Postmortem quality varies significantly; engineers delay or skip documentation due to time constraints, losing valuable lessons learned.

**Solution**: Automated postmortem generation using AI to analyze incidents and generate structured documentation with consistent quality, automatically indexed for future reference.



**Solution**: Real-time workflow tracking with step-by-step progress monitoring, retry mechanisms with exponential backoff, and comprehensive logging with correlation IDs.

### 5. **Race Conditions in Sync Operations** ❌ → ✅
**Problem**: Multiple concurrent knowledge base syncs can corrupt indexes or waste resources processing the same files.

**Solution**: Distributed locking mechanism (Redis-based) ensures only one sync operation runs at a time, with clear conflict messaging (HTTP 409).

---

## ✨ Key Features

### 🚨 Incident Response Automation
- **Automatic Workflow Trigger**: Creates workflows when incidents are reported
- **Log Analysis**: Asynchronous log parsing and error extraction
- **GitHub Integration**: Auto-creates tracking issues with incident details
- **Retry Logic**: Exponential backoff (1s, 2s, 4s) with max 3 retries per ste

### 📄 Postmortem Publishing
- **AI-Powered Generation**: Uses Claude to create incident summaries, timelines, root cause analysis
- **Template Rendering**: Jinja2 templates for consistent documentation format
- **Parallel Processing**: Creates GitHub issues and ChromaDB embeddings simultaneously
- **Stakeholder Notifications**: Automatic distribution to configured recipients
- **Searchable Archives**: All postmortems indexed for future incident reference


### 🔄 Workflow Orchestration
- **Celery Chains**: Sequential task execution with result passing
- **Celery Groups**: Parallel task execution for independent operations
- **Celery Chords**: Wait for parallel tasks before proceeding (embeddings → ChromaDB)
- **State Persistence**: Workflows survive system restarts (database-backed)
- **Progress Tracking**: Real-time status via REST API with cache layer (Redis)

### 🎯 Developer Experience
- **OpenAPI Documentation**: Auto-generated interactive API docs at `/docs`
- **Health Checks**: Service readiness endpoints for all components
- **Structured Logging**: JSON logs with correlation IDs for request tracing
- **Docker Compose**: One-command local development environment


---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│                     (Web UI, CLI, API clients)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Port 8000)                │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │   Incident   │  │  Postmortem  │  │   KB Sync Routes    │  │
│  │   Routes     │  │    Routes    │  │                     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬──────────┘  │
│         │                  │                      │              │
│  ┌──────▼──────────────────▼──────────────────────▼──────────┐ │
│  │           Workflow Service & Cache Layer                   │ │
│  └──────┬──────────────────┬──────────────────────┬──────────┘ │
└─────────┼──────────────────┼──────────────────────┼────────────┘
          │                  │                      │
          ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Celery Task Queue                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐ │
│  │ Incident Tasks  │ │ Postmortem Tasks│ │   │ │
│  │ • create_record │ │ • generate_sections│ •  │ │
│  │ • analyze_logs  │ │ • render_template │ │ •  │ │
│  │ • search_runbooks│ │ • embed_chromadb │ │ •  │
│  │ • create_issue  │ │ • notify_stakeholders│ •  │
│  │ • send_notify   │ │                  │ │ •  │
│  └─────────────────┘ └─────────────────┘ └──────────────────┘ │
└────────┬──────────────────┬──────────────────────┬─────────────┘
         │                  │                      │
         ▼                  ▼                      ▼
┌────────────────┐  ┌──────────────┐  ┌──────────────────────────┐
│   PostgreSQL   │  │    Redis     │  │       ChromaDB           │
│  (Workflows,   │  │ (Broker +    │  │  (Vector Embeddings)     │
│   Incidents)   │  │  Cache +     │  │  • Runbooks Collection   │
│                │  │  Locks)      │  │  • Postmortems Collection│
└────────────────┘  └──────────────┘  └──────────────────────────┘

         External Integrations
         ┌──────────────┐  ┌──────────────┐
         │  GitHub API  │  │  Claude API  │
         │ (Issues)     │  │ (AI Analysis)│
         └──────────────┘  └──────────────┘
```

### Workflow Execution Flow

**Incident Response Workflow**:
```
1. POST /api/workflows/incident/{id}
   ↓
2. Create Workflow DB record
   ↓
3. Celery Chain:
   create_incident_record → analyze_logs_async → search_related_runbooks
   → create_github_issue → send_notification
   ↓
4. Each step updates workflow state in DB + Redis cache
   ↓
5. GET /api/workflows/{workflow_id} returns progress
```

**KB Sync Workflow**:
```
1. POST /api/workflows/kb-sync (acquires distributed lock)
   ↓
2. Celery Chain:
   scan_runbooks_dir → extract_and_process_changes
   ↓
3. Parallel Group (for each changed file):
   regenerate_embeddings_1 │ regenerate_embeddings_2 │ ... │ regenerate_embeddings_N
   ↓
4. Chord Callback (waits for all embeddings):
   prepare_chromadb_update → invalidate_cache
   ↓
5. Lock automatically released (timeout: 10 minutes)
```

---

## 📁 Directory Structure

```
ia-dev-final-project/
├── backend/                      # Main application code
│   ├── api/                      # FastAPI routes
│   │   └── routes/
│   │       └── workflows.py      # Workflow API endpoints
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── base.py              # Base model class
│   │   ├── workflow.py          # Workflow & WorkflowStep models
│   │   ├── incident.py          # Incident model
│   │   └── cluster.py           # ClusterConfig model
│   ├── services/                # Business logic layer
│   │   ├── workflow_service.py  # Workflow CRUD operations
│   │   ├── workflow_cache.py    # Redis caching & locking
│   │   ├── sync_service.py      # KB sync change detection
│   │   ├── embedding_service.py # ChromaDB operations
│   │   └── notification_service.py # Webhook notifications
│   ├── workflows/               # Celery workflow compositions
│   │   ├── incident_response.py # Incident workflow chain
│   │   ├── postmortem_publish.py# Postmortem workflow chain
│   │   
│   │   └── tasks/               # Individual Celery tasks
│   │       ├── incident_tasks.py
│   │       ├── postmortem_tasks.py
│   │       └── kb_sync_tasks.py
│   ├── integrations/            # External API clients
│   │   ├── github_client.py     # GitHub API wrapper
│   │   └── claude_client.py     # Anthropic Claude client
│   ├── utils/                   # Utility functions
│   │   ├── logging.py           # Structured logging
│   │   ├── retry.py             # Retry decorator
│   │   ├── file_scanner.py      # Directory scanning
│   │   └── log_parser.py        # Log analysis
│   ├── config/                  # Configuration
│   │   └── celery_config.py     # Celery settings
│   ├── templates/               # Jinja2 templates
│   │   └── postmortem.md.j2     # Postmortem template
│   ├── alembic/                 # Database migrations
│   │   └── versions/            # Migration scripts
│   ├── celery_app.py            # Celery application setup
│   ├── database.py              # Database connection
│   ├── main.py                  # FastAPI application
│   └── alembic.ini              # Alembic configuration
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── contract/                # Contract tests
├── docker-compose.yml           # Docker Compose configuration
├── Dockerfile.backend           # Backend service Dockerfile
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
├── Test-evidences.docx          # Test evidences
├── logs-examples/               # Log examples for testing
└── README.md                    # This file
```

---

## 📋 Prerequisites

### Required Software

- **Docker**: 20.10+ and Docker Compose 2.0+
- **Python**: 3.11+ (for local development)
- **Git**: For version control



### External Services

- **Anthropic API Key**: For Claude AI integration
  - Sign up at https://console.anthropic.com/
  - Get API key from dashboard

- **GitHub Personal Access Token**: For issue creation
  - Settings → Developer settings → Personal access tokens
  - Scopes needed: `repo` (full control of private repositories)

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ia-dev-final-project.git
cd ia-dev-final-project
```

### 2. Configure Environment Variables

Edit docker-compose.yml and fill in the environment variables:
GITHUB_TOKEN=YOUR_GITHUB_TOKEN
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
GITHUB_REPO=YOUR_GITHUB_REPO
GITHUB_ENABLED=True

The rest of the environment variables are optional and are already set to default values.

### 3. Build and Run the Application

```bash
docker-compose up --build
```

### 4. Access the Application

Once the containers are up and running, you can access the application at:

- **API Documentation**: http://localhost:8000/docs
- **Celery Dashboard**: http://localhost:5555

### 5. Stop the Application

To stop the application, run:

```bash
docker-compose down
```

### 6. Install Dependencies (Local Development)

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

---

## ⚙️ Configuration

### Database Configuration

PostgreSQL is configured via `DATABASE_URL` environment variable:

```env
DATABASE_URL=postgresql://user:password@host:port/database_name
```

### Celery Configuration

Celery settings in `backend/config/celery_config.py`:

```python
broker_url = "redis://redis:6379/1"
result_backend = "redis://redis:6379/2"
task_serializer = "json"
result_serializer = "json"
task_acks_late = True
worker_prefetch_multiplier = 1
```

### ChromaDB Configuration

Vector database connection settings:

```env
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
```

Collections created automatically:
- `runbooks` - Runbook documentation embeddings
- `postmortems` - Postmortem document embeddings

---

## 🐳 Deployment

### Docker Compose (Recommended for Development)

#### Start All Services

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** (port 5432) - Main database
- **Redis** (port 6379) - Message broker & cache
- **ChromaDB** (port 8001) - Vector database
- **FastAPI Backend** (port 8000) - REST API
- **Celery Worker** - Background task processor
- **PgAdmin** (port 5050) - Database admin UI

#### Verify Services

```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Test API
curl http://localhost:8000/docs
```

#### Run Database Migrations

```bash
# Migrations run automatically on backend startup
# To run manually:
docker-compose exec backend alembic upgrade head
```

#### Stop Services

```bash
docker-compose down
# To remove volumes (data):
docker-compose down -v
```

### Kubernetes Deployment (Local with Kind)



#### 1. Build and Load Docker Images

```bash
# Build backend image
docker build -t devops-copilot-backend:latest -f Dockerfile.backend .

```

---

## 💻 Usage

### API Documentation

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Quick Start Examples

#### 1. Trigger Incident Response Workflow

```bash
curl -X POST "http://localhost:8000/api/workflows/incident/123e4567-e89b-12d3-a456-426614174000" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Service Down",
    "description": "500 errors on /api/chat endpoint",
    "severity": "critical",
    "log_file_path": "/logs/api-2024-01-06.log",
    "triggered_by": "alerting-system"
  }'

# Response:
{
  "workflow_id": "abc123...",
  "type": "INCIDENT_RESPONSE",
  "status": "PENDING",
  "created_at": "2024-01-06T18:30:00Z",
  "message": "Incident response workflow triggered successfully"
}
```

#### 2. Check Workflow Status

```bash
curl "http://localhost:8000/api/workflows/abc123..."

# Response:
{
  "workflow_id": "abc123...",
  "type": "INCIDENT_RESPONSE",
  "status": "RUNNING",
  "progress": "3/5 steps completed",
  "current_step": "create_github_issue",
  "steps": [
    {"name": "create_incident_record", "status": "completed", "order": 1},
    {"name": "analyze_logs_async", "status": "completed", "order": 2},
    {"name": "search_related_runbooks", "status": "completed", "order": 3},
    {"name": "create_github_issue", "status": "running", "order": 4},
    {"name": "send_notification", "status": "pending", "order": 5}
  ]
}
```

#### 3. Trigger Postmortem Generation

```bash
curl -X POST "http://localhost:8000/api/workflows/postmortem/123e4567-e89b-12d3-a456-426614174000"

# Response:
{
  "workflow_id": "def456...",
  "type": "POSTMORTEM_PUBLISH",
  "status": "PENDING",
  "created_at": "2024-01-06T19:00:00Z",
  "message": "Postmortem publish workflow triggered successfully"
}
```


### Using PgAdmin

Access database admin UI:
1. Navigate to http://localhost:5050
2. Login: `admin@admin.com` / `admin123`
3. Add server:
   - Host: `postgres`
   - Port: `5432`
   - Database: `devops_copilot`
   - Username: `user`
   - Password: `pass`

---

## 📚 API Documentation

### Workflow Endpoints

#### `POST /api/workflows/incident/{incident_id}`
Trigger incident response workflow

**Request Body**:
```json
{
  "title": "string",
  "description": "string",
  "severity": "low|medium|high|critical",
  "log_file_path": "string (optional)",
  "triggered_by": "string (optional)"
}
```

**Response**: `202 Accepted` - WorkflowResponse

---

#### `POST /api/workflows/postmortem/{incident_id}`
Trigger postmortem generation workflow

**Response**: `202 Accepted` - WorkflowResponse

---

#### `POST /api/workflows/kb-sync`
Trigger knowledge base synchronization

**Request Body**:
```json
{
  "runbooks_dir": "string",
  "triggered_by": "string (optional)"
}
```

**Response**:
- `202 Accepted` - WorkflowResponse
- `409 Conflict` - If sync already running

---

#### `GET /api/workflows/{workflow_id}`
Get workflow status and progress

**Response**: `200 OK` - WorkflowStatusResponse

---

## 🔄 Workflows

### Incident Response Workflow

**Trigger**: Incident creation via API

**Steps**:
1. **create_incident_record** (0 retries) - Creates database record
2. **analyze_logs_async** (3 retries) - Parses logs for errors
3. **search_related_runbooks** (3 retries) - Semantic search for relevant docs
4. **create_github_issue** (3 retries) - Creates tracking issue


**Composition**: Celery `chain` (sequential execution)

**Retry Strategy**: Exponential backoff with jitter (1s, 2s, 4s)

---

### Postmortem Publishing Workflow

**Trigger**: Manual request for resolved incident

**Steps**:
1. **generate_postmortem_sections** (3 retries) - Claude AI analysis
2. **render_jinja_template** (0 retries) - Renders markdown document
3. **Parallel Execution** (Celery `group`):
   - **create_github_issue** (3 retries)
   - **embed_in_chromadb** (3 retries)


**Composition**: Celery `chain` with `chord` for parallel steps



---

## 🛠️ Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run migrations
cd backend
alembic upgrade head

# Start FastAPI dev server
uvicorn backend.main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A backend.celery_app:app worker --loglevel=info
```

### Code Quality Tools

```bash
# Linting
ruff check .

# Type checking
mypy backend/

# Code formatting
black backend/

# Security scanning
bandit -r backend/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```


---

## 🧪 Testing

### Run All Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Contract tests
pytest tests/contract/ -v

# Coverage report
pytest --cov=backend --cov-report=html
```
### Test Specific Workflows

```bash
# Test incident workflow
pytest tests/integration/test_incident_workflow.py -v

# Test KB sync
pytest tests/integration/test_kb_sync_workflow.py -v
```

---


## 🐛 Troubleshooting

### Common Issues

#### 1. Celery Worker Not Processing Tasks

**Symptoms**: Workflows stuck in `PENDING` status

**Solutions**:
```bash
# Check worker logs
docker-compose logs celery-worker

# Verify Redis connection
docker-compose exec redis redis-cli ping

# Restart worker
docker-compose restart celery-worker
```

#### 2. Database Connection Errors

**Symptoms**: `SQLSTATE[08006] could not connect to server`

**Solutions**:
```bash
# Check PostgreSQL health
docker-compose ps postgres

# View database logs
docker-compose logs postgres

# Verify connection string in .env
echo $DATABASE_URL
```

#### 3. ChromaDB Embedding Failures

**Symptoms**: `Failed to embed document` errors

**Solutions**:
```bash
# Check ChromaDB service
curl http://localhost:8001/api/v1/heartbeat

# Verify ChromaDB logs
docker-compose logs chromadb

# Reset ChromaDB (WARNING: deletes all data)
docker-compose exec chromadb curl -X POST http://localhost:8000/api/v1/reset
```

#### 4. GitHub API Rate Limiting

**Symptoms**: `403 Forbidden` on GitHub issue creation

**Solutions**:
```bash
# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit

# Disable GitHub integration temporarily
export GITHUB_ENABLED=false
```

#### 5. KB Sync Lock Timeout

**Symptoms**: `KB sync workflow is already running` persists

**Solutions**:
```bash
# Check Redis lock
docker-compose exec redis redis-cli GET "lock:kb_sync"

# Manually release lock (emergency only)
docker-compose exec redis redis-cli DEL "lock:kb_sync"
```

### Debug Mode

Enable debug logging:

```env
# In .env
LOG_LEVEL=DEBUG
CELERY_LOG_LEVEL=DEBUG
```

### Logs Location

```bash
# View all logs
docker-compose logs -f

# Backend logs
docker-compose logs -f backend

# Worker logs
docker-compose logs -f celery-worker
```

---

## 🤝 Contributing

Contributions are welcome! 




---

## 📞 Support

For issues, questions, or contributions:

- **GitHub Issues**: https://github.com/YOUR_USERNAME/ia-dev-final-project/issues
- **Documentation**: See `/docs` directory for detailed guides


---

## 🙏 Acknowledgments


- **Celery** - Distributed task queue
- **Anthropic Claude** - AI-powered analysis and generation
- **ChromaDB** - Vector database for embeddings
- **DataTalks.Club** - AI & Dev Tools Bootcamp

