# Question & Answering ChatBot 
RAG agent for Q&A and summary generation

## System Design

![System Design](assets/system-design.svg)

## Frontend Setup

### Prerequisites
- Node.js (v16 or higher)
- npm or yarn

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

## Backend Setup

### Prerequisites
- Python 3.13+
- Redis server

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate virtual environment:
```bash
python3.13 -m venv venv
source venv/bin/activate  # On Linux/macOS
# venv\Scripts\activate   # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```env
DEBUG=true
APP_NAME="QA Chatbot API"
REDIS_HOST=localhost
REDIS_PORT=6379
ALLOWED_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
```

5. Start Redis server:
```bash
sudo systemctl start redis-server
# Or with Docker: docker run -d -p 6379:6379 redis:7-alpine
```

6. Run the application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
python redis/worker.py  # In separate terminal
```

The API will be available at `http://localhost:8000/docs`

### Features
- Upload documents for RAG-based question answering
- Interactive chat interface
- Document-based query responses
