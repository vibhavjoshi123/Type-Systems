"""FastAPI application entry point.

Provides REST API endpoints for:
- /api/v1/query: Natural language queries against the hypergraph
- /api/v1/entities: Entity CRUD operations
- /api/v1/hyperedges: Hyperedge CRUD operations
- /api/v1/connectors: Connector management

From ARCHITECTURE_PLAN.md Section 5.1.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.auth import APIKeyMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routes import connectors, entities, hyperedges, query
from src.config import get_settings
from src.typedb.client import TypeDBClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle: connect to TypeDB on startup, disconnect on shutdown."""
    settings = get_settings()
    app.state.settings = settings

    # Initialize TypeDB client
    client = TypeDBClient(settings.typedb)
    await client.connect()
    app.state.db = client

    logger.info(
        "API started (TypeDB connected: %s)", client.is_connected
    )
    yield

    # Shutdown
    await client.disconnect()
    logger.info("API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Hypergraph Context Graph API",
        description=(
            "Enterprise decision context graph using TypeDB hypergraphs. "
            "Supports n-ary relations, s-path traversal, and multi-agent reasoning."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting middleware
    app.add_middleware(RateLimitMiddleware, requests_per_minute=120)

    # API key auth middleware (disabled if no key configured)
    app.add_middleware(APIKeyMiddleware)

    # Register routers
    app.include_router(query.router, prefix="/api/v1", tags=["query"])
    app.include_router(entities.router, prefix="/api/v1", tags=["entities"])
    app.include_router(hyperedges.router, prefix="/api/v1", tags=["hyperedges"])
    app.include_router(connectors.router, prefix="/api/v1", tags=["connectors"])

    @app.get("/health")
    async def health_check() -> dict[str, object]:
        db_connected = getattr(getattr(app.state, "db", None), "is_connected", False)
        return {
            "status": "healthy",
            "version": "0.1.0",
            "typedb_connected": db_connected,
        }

    return app


app = create_app()


def run() -> None:
    """Run the API server (used by hcg-api CLI entry point)."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug,
    )
