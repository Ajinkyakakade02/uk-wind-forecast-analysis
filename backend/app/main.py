"""
Wind Intelligence — FastAPI application entry point.

Sets up the FastAPI app, CORS middleware, and includes API routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="Wind Intelligence API",
    description=(
        "Analyses UK national wind generation forecast accuracy "
        "using Elexon FUELHH and WINDFOR datasets. "
        "Built as a Full-Stack Engineer hiring challenge."
    ),
    version="0.1.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",  # IP dev server
        "http://localhost:3000",  # Alternative dev port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}
