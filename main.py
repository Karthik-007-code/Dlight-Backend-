"""
main.py — FastAPI application entrypoint.

Startup:
  - Creates all SQLite tables (if they don't exist)
  - Registers slowapi rate limit middleware
  - Mounts /auth and /v1 routers
  - Attaches CORS middleware
  - Closes the shared httpx client on shutdown
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from database import Base, engine
from middleware.rate_limit import limiter
from routers import auth, flights
from services.aviation import close_client


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: close httpx client
    await close_client()


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Dlight Aviation API",
    description=(
        "A secure backend proxy for the AviationStack `/v1/flights` API.\n\n"
        "**Authentication**: All flight endpoints require a Bearer JWT.\n"
        "Use `/auth/signup` or `/auth/login` to obtain tokens.\n\n"
        "**Rate Limits**: 30 requests/minute per IP · 200 requests/day per user.\n\n"
        "**Caching**: Identical flight queries are cached for 60 seconds."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Rate limiter state ───────────────────────────────────────────────────────

app.state.limiter = limiter

# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Exception Handlers ───────────────────────────────────────────────────────

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"IP rate limit exceeded: {exc.detail}. Try again in a moment.",
        },
        headers={"Retry-After": "60"},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(flights.router)


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """Quick liveness check — no auth required."""
    return {"status": "ok", "service": "Dlight Aviation API"}
