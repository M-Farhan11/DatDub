"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api import health

app = FastAPI(title="AI Hackathon Bootstrap")

app.include_router(health.router)
