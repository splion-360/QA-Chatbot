# QA Chatbot Backend

FastAPI backend for the QA Chatbot with RAG capabilities, Redis message queuing, and async processing.

## Features

- 🚀 **FastAPI** with async endpoints
- 📦 **Redis + RQ** for message queuing
- 🧪 **Pytest** with comprehensive test coverage
- 🎯 **Ruff + Black** for code quality
- 📊 **Pydantic** for data validation
- 🐍 **Python 3.13+** support

## Quick Start

### 1. Prerequisites

- Python 3.13+
- Redis server (for message queuing)

### 2. Setup Virtual Environment

```bash
cd backend

# Create virtual environment
python3.13 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Or install with development dependencies
pip install -e ".[dev]"
```

### 4. Environment Configuration

Create a `.env` file in the backend directory:

```env
# API Configuration
DEBUG=true
APP_NAME="QA Chatbot API"
APP_VERSION="0.1.0"

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# CORS Configuration
ALLOWED_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
```

### 5. Start Redis Server

```bash
# Install Redis (Ubuntu/Debian)
sudo apt update && sudo apt install redis-server

# Start Redis
sudo systemctl start redis-server

# Or run Redis in Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### 6. Run the Application

```bash
# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start RQ worker (in a separate terminal)
python redis/worker.py
```

### 7. Access the API

- **API Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/chat/health

## Development

### Code Quality

```bash
# Format code with Black
black .

# Lint code with Ruff
ruff check .

# Fix auto-fixable issues
ruff check . --fix

# Type checking (optional)
mypy app redis tests
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov=redis

# Run specific test file
pytest tests/test_chat.py

# Run with verbose output
pytest -v
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## API Endpoints

### Chat Endpoints

- `POST /api/v1/chat/message` - Send a message to the chatbot
- `GET /api/v1/chat/health` - Health check endpoint

### Example Usage

```python
import httpx

# Send a message
response = httpx.post(
    "http://localhost:8000/api/v1/chat/message",
    json={"message": "Hello, how are you?"}
)

print(response.json())
```

## Message Queue

The application uses Redis and RQ for asynchronous message processing.

### Queue Operations

```python
from redis.queue import enqueue_chat_message, get_job_result

# Enqueue a message
job_id = enqueue_chat_message("Hello world", user_id="user123")

# Check job status
result = get_job_result(job_id)
print(result)
```

### Worker Management

```bash
# Start a worker
python redis/worker.py

# Monitor queue (install rq-dashboard)
pip install rq-dashboard
rq-dashboard
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       └── chat.py      # Chat endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Configuration settings
│   └── models/
│       ├── __init__.py
│       └── chat.py          # Pydantic models
├── redis/
│   ├── __init__.py
│   ├── queue.py             # Queue operations
│   └── worker.py            # RQ worker
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration
│   └── test_chat.py         # Test cases
├── requirements.txt         # Dependencies
├── pyproject.toml          # Tool configuration
└── README.md               # This file
```

## Configuration

The application uses Pydantic Settings for configuration management. Settings can be configured via:

1. Environment variables
2. `.env` file
3. Default values in `app/core/config.py`

## Deployment

### Docker (Optional)

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations

- Use a production WSGI server (e.g., Gunicorn with Uvicorn workers)
- Set up proper logging
- Configure Redis persistence
- Set up monitoring and health checks
- Use environment-specific configuration

## Contributing

1. Follow the code style enforced by Ruff and Black
2. Write tests for new features
3. Update documentation as needed
4. Run the test suite before submitting changes

## License

This project is part of the QA Chatbot application.