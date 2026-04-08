from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import auth, protected, ws
from app.websocket.signaling import router as signaling_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import setup_logging, logger

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LetsMeet-WebRTC server")
    yield
    logger.info("Server shutting down")


app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(protected.router)
app.include_router(ws.router)
app.include_router(signaling_router)


@app.get("/")
def home():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)
