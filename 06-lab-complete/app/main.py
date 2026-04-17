import time
import json
import logging
import signal
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit
from .cost_guard import check_budget, get_current_spending
from .history import save_message, get_history
from .llm import ask_llm

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

class AskResponse(BaseModel):
    question: str
    answer: str
    history_count: int
    model: str
    timestamp: str
    usage_cost_usd: float

# ─────────────────────────────────────────────────────────
# Lifespan & Shutdown
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.APP_NAME,
        "env": settings.ENVIRONMENT
    }))
    # Simulate setup
    time.sleep(0.5)
    _is_ready = True
    yield
    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# App Initialize
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(json.dumps({
        "event": "request",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration * 1000, 2)
    }))
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/health", tags=["Ops"])
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 2)
    }

@app.get("/ready", tags=["Ops"])
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="App not ready")
    return {"status": "ready"}

@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask(
    body: AskRequest,
    api_key: str = Depends(verify_api_key)
):
    # 1. Check Rate Limit (Stateless via Redis)
    user_id = api_key[:8]
    check_rate_limit(user_id)
    
    # 2. Check Budget (Stateless via Redis)
    estimated_call_cost = 0.02
    check_budget(user_id, estimated_call_cost)
    
    # 3. Get History
    history = get_history(user_id)
    
    # 4. Process Logic (Pass history if needed, for mock we just count)
    logger.info(json.dumps({
        "event": "agent_call", 
        "user": user_id[:4],
        "history_len": len(history)
    }))
    
    answer = ask_llm(body.question)
    
    # 5. Save to History
    save_message(user_id, "user", body.question)
    save_message(user_id, "assistant", answer)
    
    # 6. Return Response
    return AskResponse(
        question=body.question,
        answer=answer,
        history_count=len(history),
        model=settings.LLM_MODEL,
        timestamp=datetime.now(timezone.utc).isoformat(),
        usage_cost_usd=get_current_spending(user_id)
    )

# ─────────────────────────────────────────────────────────
# Graceful Shutdown Signal
# ─────────────────────────────────────────────────────────
def handle_exit(sig, frame):
    logger.info(json.dumps({"event": "exit_signal_received", "signal": sig}))
    # Uvicorn handles the actual shutdown via lifespan
    
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)
