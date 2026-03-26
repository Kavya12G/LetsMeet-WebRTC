from fastapi import FastAPI
from app.db.session import engine
from app.db.base import Base
from app.api import auth
from app.api import protected
from app.api import ws
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from pathlib import Path
from app.websocket.signaling import router as signaling_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Add this block
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For testing, allow everything
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
# ... rest of your routers

app.include_router(auth.router)

app.include_router(protected.router)

app.include_router(ws.router)

# @app.get("/favicon.ico")
# async def favicon():
#     return FileResponse("favicon.ico")

app.include_router(signaling_router)

@app.get("/")
def home():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)

