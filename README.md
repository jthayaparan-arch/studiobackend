# Ares Studio OS — Backend

FastAPI backend for the Ares Studio OS app.

## Deploy on Render
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`

## Required environment variables
- `MONGO_URL` — your MongoDB connection string
- `DB_NAME` — any name, e.g. `ares_studio`
- `CORS_ORIGINS` — `*` (or your Netlify site URL once you have it)
