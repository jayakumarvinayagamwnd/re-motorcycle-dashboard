from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.camera import router as camera_router
from .api.gps import router as gps_router
from .api.telemetry import router as telemetry_router
from .api.trip import router as trip_router
from .config.settings import settings
from .database import check_db_health, init_db
from .models.db_check import DBHealthError, DBHealthResponse
from .services.camera_service import start_camera_monitor
from .websocket.dashboard_ws import router as websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_camera_monitor()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry_router, prefix="/api")
app.include_router(gps_router, prefix="/api")
app.include_router(camera_router, prefix="/api")
app.include_router(trip_router, prefix="/api")
app.include_router(websocket_router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} is running"}


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/healthcheck/db",
    tags=["health"],
    response_model=DBHealthResponse,
    responses={
        503: {
            "model": DBHealthError,
            "description": "Database health check failed",
        }
    },
)
def db_health_check() -> DBHealthResponse:
    """Open SQLite, insert a db_check row, verify it, and return health status."""
    try:
        return check_db_health()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content=DBHealthError(
                status="unhealthy",
                database="sqlite",
                error="Database health check failed",
            ).model_dump(),
        )
