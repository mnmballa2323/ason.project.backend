"""
Unified Gateway Service — Ason Platform Trinity
Entry point for all frontend traffic (Workplace, Console, Insight).
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .routers import workplace, console, insight
from .auth import verify_token
from .middleware import NetworkEgressFilter

app = FastAPI(
    title="Ason Unified Gateway",
    description="API Gateway for Ason-Workplace, Ason-Console, and Ason-Insight",
    version="1.0.0"
)

# Enforce Data Sovereignty
app.add_middleware(NetworkEgressFilter)

# Include Routers
app.include_router(workplace.router, prefix="/workplace", tags=["Workplace"])
app.include_router(console.router, prefix="/console", tags=["Console"])
app.include_router(insight.router, prefix="/insight", tags=["Insight"])

@app.get("/health")
async def health_check():
    return {"status": "active", "service": "Ason Unified Gateway"}

@app.get("/")
async def root():
    return {"message": "Welcome to the Ason Platform Trinity Gateway"}
