import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from src.manager.container_manager import container_manager
from src.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    await container_manager.initialize_clients()
    await container_manager.watchdog.start()
    yield
    # Shutdown
    await container_manager.cleanup_clients()
    await container_manager.watchdog.stop()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)


# Get network configuration from environment
subnet_ids: list[str] = os.getenv("SUBNET_IDS", "").split(",")
security_group_id: str = os.getenv("SECURITY_GROUP_ID", "")
cluster_name: str = os.getenv("CLUSTER_NAME", "sandbox-cluster")
is_local: bool = os.getenv("IS_LOCAL", "true").lower() == "true"
efs_filesystem_id: str = os.getenv("EFS_FILESYSTEM_ID", "")

container_manager.configure_networking(
    subnet_ids=subnet_ids,
    security_group_id=security_group_id,
    efs_filesystem_id=efs_filesystem_id,
)
container_manager.cluster_name = cluster_name
container_manager.is_local = is_local

app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint that redirects to health check."""
    return RedirectResponse(url="/health")
