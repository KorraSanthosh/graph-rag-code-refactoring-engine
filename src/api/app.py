import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.api.routes import router
from src.api.dependencies import get_app_state
from src.api.security import GuardMiddleware

# ─── Logging Configuration ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Application Lifespan ───────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all services once at startup."""
    logger.info("🚀 Graph RAG Refactoring Engine starting up...")
    try:
        state = get_app_state()
        logger.info(f"✅ Services initialized. Model: {state.model}")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    yield
    logger.info("🛑 Shutting down.")


# ─── FastAPI Application ────────────────────────────────────────────────────────
app = FastAPI(
    title="Graph RAG Code Refactoring Engine",
    description="""
## AI-Powered Code Refactoring Using Dependency Graph Context

This API implements a **Graph-RAG pipeline** for intelligent Python code refactoring:

1. **Parse** source code into an AST using Tree-sitter
2. **Build** a dependency graph (functions/classes as nodes, calls as edges)
3. **Retrieve** structural context via BFS traversal
4. **Refactor** using GPT-4o augmented with graph context
5. **Verify** in an isolated Docker sandbox
6. **Evaluate** quality metrics (cyclomatic complexity, maintainability index)
7. **Retry** with error feedback in an agentic loop

### Endpoints
- `POST /api/v1/analyze` — Parse code and extract dependency graph
- `POST /api/v1/refactor` — Full Graph-RAG refactoring pipeline
- `POST /api/v1/refactor/stream` — Same pipeline, streamed as Server-Sent Events
- `POST /api/v1/visualize` — Interactive dependency graph (HTML)
- `GET /api/v1/health` — System health check
    """,
    version="1.0.0",
    contact={"name": "Graph RAG Engine"},
    lifespan=lifespan,
)

# ─── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(GuardMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ─────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")

# ─── Frontend Static Files ──────────────────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/ui", StaticFiles(directory=frontend_dir), name="frontend")

    @app.get("/", include_in_schema=False)
    async def serve_ui():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
