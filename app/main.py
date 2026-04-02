# app/main.py
import os
import time
import sys
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Database imports
from .database import Base, engine
from app.models import user, mood, task  # SQLAlchemy models

# -----------------------------
# Initialize FastAPI app
# -----------------------------
app = FastAPI(
    title="Moodaak API",
    description="Backend for MoodakLyom App - Phase 1",
    version="1.0.0"
)

# -----------------------------
# Middleware: Logging requests
# -----------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    try:
        print(f"[REQ] {request.method} {request.url.path}", flush=True)
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        print(f"[RES] {request.method} {request.url.path} -> {response.status_code} ({duration:.1f}ms)", flush=True)
        return response
    except Exception as exc:
        duration = (time.time() - start) * 1000
        print(f"[EXC] {request.method} {request.url.path} after {duration:.1f}ms", flush=True)
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": {"code": "SERVER_ERROR", "message": "Unexpected error"}}
        )

# -----------------------------
# CORS Middleware
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # change later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Initialize Database
# -----------------------------
Base.metadata.create_all(bind=engine)

# -----------------------------
# Include Routes
# -----------------------------
from app.routes import user as user_routes
app.include_router(user_routes.router, prefix="/user", tags=["User"])

# -----------------------------
# Health Check
# -----------------------------
@app.get("/")
def root():
    return {"message": "Moodak lyom Backend Phase 1 is running successfully!"}