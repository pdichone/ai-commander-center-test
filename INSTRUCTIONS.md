# AI Command Center - Deployment Instructions

This guide covers deploying the AI Command Center to Render, including both the FastAPI backend and Streamlit frontend.

## Project Structure

```
ai-command-center/
├── app.py                 # Entry point - re-exports FastAPI app for Render
├── api/
│   └── main.py            # FastAPI application
├── ui/
│   └── streamlit_app.py   # Streamlit frontend
├── config/
│   └── settings.py        # Application settings
├── agents/                # AI agents (manager, research, rag, code review)
├── services/              # Document service, etc.
├── requirements.txt       # Python dependencies
├── render.yaml            # Render blueprint (optional)
└── .env                   # Environment variables (local only)
```

---

## Part 1: Deploy FastAPI Backend

### Step 1: Create a New Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New** → **Web Service**
3. Connect your GitHub repository

### Step 2: Configure the Service

| Setting | Value |
|---------|-------|
| **Name** | `ai-command-center-api` (or your choice) |
| **Runtime** | Python |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app:app --host 0.0.0.0 --port $PORT` |

### Step 3: Add Environment Variables

In the **Environment** tab, add these variables:

| Key | Value | Notes |
|-----|-------|-------|
| `PYTHON_VERSION` | `3.12` | Python version |
| `API_KEY` | `your-secure-api-key` | For authenticating requests |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Your Anthropic API key |
| `OPENAI_API_KEY` | `sk-proj-...` | Your OpenAI API key |
| `TAVILY_API_KEY` | `tvly-...` | For research agent |
| `ENVIRONMENT` | `production` | Sets production mode |

### Step 4: Deploy

Click **Create Web Service** and wait for deployment.

### Step 5: Test the API

Once deployed, test these endpoints:

**Browser (no auth required):**
- `https://your-app.onrender.com/` - Health check
- `https://your-app.onrender.com/health` - Health check
- `https://your-app.onrender.com/docs` - Swagger UI (interactive API docs)
- `https://your-app.onrender.com/redoc` - ReDoc (alternative docs)

**curl (auth required):**

```bash
# Get stats
curl https://your-app.onrender.com/stats \
  -H "Authorization: Bearer your-api-key"

# List documents
curl https://your-app.onrender.com/documents \
  -H "Authorization: Bearer your-api-key"

# Query the AI
curl -X POST https://your-app.onrender.com/query \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What can you help me with?"}'

# Search documents
curl -X POST "https://your-app.onrender.com/documents/search?query=AI&n_results=5" \
  -H "Authorization: Bearer your-api-key"
```

---

## Part 2: Deploy Streamlit Frontend

### Step 1: Create a Second Web Service

1. Go to Render Dashboard → **New** → **Web Service**
2. Connect the **same** GitHub repository

### Step 2: Configure the Service

| Setting | Value |
|---------|-------|
| **Name** | `ai-command-center-ui` |
| **Runtime** | Python |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `streamlit run ui/streamlit_app.py --server.port $PORT --server.address 0.0.0.0` |

### Step 3: Add Environment Variables

| Key | Value | Notes |
|-----|-------|-------|
| `PYTHON_VERSION` | `3.12` | Python version |
| `API_BASE_URL` | `https://your-api.onrender.com` | URL of your FastAPI backend |
| `API_KEY` | `your-secure-api-key` | Same key as the backend |

### Step 4: Deploy

Click **Create Web Service** and wait for deployment.

---

## Part 3: Alternative - Deploy Using render.yaml Blueprint

If you have `render.yaml` in your repo, you can deploy both services at once:

1. Go to Render Dashboard → **New** → **Blueprint**
2. Connect your repository
3. Render will auto-detect `render.yaml` and create both services
4. Set the environment variables marked as `sync: false` manually

---

## API Endpoints Reference

### Public Endpoints (No Auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root health check |
| GET | `/health` | Detailed health check |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc documentation |

### Protected Endpoints (Require `Authorization: Bearer <API_KEY>`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query` | Query the AI agents |
| GET | `/stats` | Get usage statistics |
| POST | `/documents/upload` | Upload a document |
| GET | `/documents` | List all documents |
| DELETE | `/documents/{source}` | Delete a document |
| POST | `/documents/search` | Search documents |

### Request/Response Examples

**POST /query**
```json
// Request
{
  "query": "What is RAG?",
  "context": {"optional": "context data"}
}

// Response
{
  "answer": "RAG stands for Retrieval-Augmented Generation...",
  "metadata": {},
  "success": true
}
```

**GET /stats**
```json
// Response
{
  "manager": {
    "name": "Manager Agent",
    "total_requests": 5,
    "total_cost": 0.15,
    "avg_cost": 0.03
  },
  "specialists": {
    "research_agent": {"name": "Research Agent", "total_requests": 2},
    "rag_agent": {"name": "RAG Agent", "total_requests": 3},
    "code_review_agent": {"name": "Code Review Agent", "total_requests": 0}
  }
}
```

---

## Running Locally

### Run FastAPI Backend

```bash
cd ai-command-center

# Install dependencies
uv pip install -r requirements.txt

# Run the API
uv run uvicorn api.main:app --reload --port 8000
```

API will be available at: http://localhost:8000

### Run Streamlit Frontend

```bash
cd ai-command-center

# Run Streamlit
uv run streamlit run ui/streamlit_app.py
```

Streamlit will be available at: http://localhost:8501

### Local Configuration

Update `.streamlit/secrets.toml` for local development:

```toml
API_BASE_URL = "http://localhost:8000"
API_KEY = "dev-key-change-in-production"
```

---

## Troubleshooting

### Error: "Attribute 'app' not found in module 'app'"

**Cause:** Render is looking for `app` variable in `app.py`, but it wasn't exported.

**Fix:** The `app.py` file should contain:
```python
from api.main import app
__all__ = ["app"]
```

### Error: "401 Unauthorized"

**Cause:** Missing or incorrect API key.

**Fix:** Include the `Authorization` header:
```bash
curl -H "Authorization: Bearer your-api-key" https://your-app.onrender.com/stats
```

### Streamlit Can't Connect to API

**Cause:** `API_BASE_URL` environment variable not set or incorrect.

**Fix:**
1. Check the env var in Render dashboard
2. Make sure it includes `https://` prefix
3. No trailing slash

### Cold Start Delays

**Note:** Free Render instances spin down after inactivity. First request may take 30-60 seconds.

---

## Security Notes

1. **Never commit `.env` to git** - It contains API keys
2. **Use strong API keys in production** - Not the default `dev-key-change-in-production`
3. **Set environment variables in Render dashboard** - Not in code
4. **CORS is configured** - Update `CORS_ORIGINS` in `config/settings.py` if needed

---

## Quick Reference

| Service | Start Command |
|---------|---------------|
| FastAPI | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| Streamlit | `streamlit run ui/streamlit_app.py --server.port $PORT --server.address 0.0.0.0` |

| URL | Purpose |
|-----|---------|
| `/docs` | Interactive API documentation |
| `/health` | Health check endpoint |
| `/query` | Main AI query endpoint |
