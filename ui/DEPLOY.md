# Deploying Streamlit UI to Render

This guide walks through deploying the Streamlit frontend as a separate Render service.

## Prerequisites

- Your FastAPI backend is already deployed at: `https://ai-commander-center-test.onrender.com`
- You have a Render account

## Deployment Steps

### Option 1: Manual Setup (Recommended for first time)

1. **Go to Render Dashboard**
   - Visit [render.com](https://render.com) and log in
   - Click **"New +"** → **"Web Service"**

2. **Connect Repository**
   - Select your GitHub repo
   - Or use "Public Git repository" if not connected

3. **Configure the Service**

   | Setting | Value |
   |---------|-------|
   | **Name** | `ai-command-center-ui` |
   | **Region** | Oregon (US West) or same as your API |
   | **Branch** | `main` |
   | **Root Directory** | `courses/ai-developer-masterclass/code/week-4/ai-command-center/ui` |
   | **Runtime** | Python 3 |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true` |

4. **Set Environment Variables**

   Click **"Advanced"** → **"Add Environment Variable"**:

   | Key | Value |
   |-----|-------|
   | `API_BASE_URL` | `https://ai-commander-center-test.onrender.com` |
   | `API_KEY` | Your API key (same as backend) |
   | `PYTHON_VERSION` | `3.11` |

5. **Select Instance Type**
   - Free tier works fine for testing
   - Starter ($7/mo) for production use

6. **Click "Create Web Service"**

### Option 2: Using render.yaml Blueprint

If you want to use Infrastructure as Code:

1. Push the `ui/render.yaml` file to your repo
2. Go to Render Dashboard → **"Blueprints"**
3. Connect your repo
4. Render will auto-detect `render.yaml` and create the service

**Note:** You'll still need to manually set `API_KEY` in the dashboard (marked as `sync: false` for security).

## After Deployment

1. **Wait for build** (~2-3 minutes)
2. **Get your URL** - Something like: `https://ai-command-center-ui.onrender.com`
3. **Test the connection** - The sidebar should show "✅ API Connected"

## Troubleshooting

### "API Offline" error
- Check that `API_BASE_URL` is set correctly (no trailing slash)
- Verify your FastAPI backend is running
- Check the API key is correct

### Slow first load
- Free tier services "spin down" after inactivity
- First request takes 30-60 seconds to spin up
- Consider Starter tier for always-on

### Build fails
- Check Python version compatibility
- Verify `requirements.txt` is in the `ui/` folder
- Check Render logs for specific errors

## Local Testing

Before deploying, test locally:

```bash
cd ui/
export API_BASE_URL=https://ai-commander-center-test.onrender.com
export API_KEY=your-api-key
streamlit run streamlit_app.py
```

## Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│   Streamlit UI      │ ──────► │   FastAPI Backend   │
│   (Render Service)  │  HTTPS  │   (Render Service)  │
│                     │         │                     │
│ ai-command-center-  │         │ ai-commander-       │
│ ui.onrender.com     │         │ center-test.        │
│                     │         │ onrender.com        │
└─────────────────────┘         └─────────────────────┘
        │                                │
        │                                │
    User Browser                   OpenAI, Tavily,
                                   ChromaDB, etc.
```

## Costs

| Service | Free Tier | Starter |
|---------|-----------|---------|
| Streamlit UI | ✅ Yes (spins down) | $7/mo |
| FastAPI Backend | ✅ Yes (spins down) | $7/mo |
| **Total** | **$0** | **$14/mo** |
