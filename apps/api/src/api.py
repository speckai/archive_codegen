import asyncio
import base64
import datetime
import os
import traceback
from contextlib import asynccontextmanager, suppress
from hashlib import sha256
from typing import Any

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, RedirectResponse
from src.account.auth.router import router as account_auth_router
from src.account.billing.router import router as billing_router
from src.account.billing.utils import is_user_subscribed
from src.account.logging.router import router as account_logging_router
from src.account.security import verify_jwt_token
from src.analytics.router import router as analytics_router
from src.client_scripts.router import router as client_scripts_router
from src.config import DEV, IS_DOCKER, USING_NGINX
from src.github.router import router as github_router
from src.preview_manager import PreviewManager
from src.redis_manager import RedisManager
from src.repos.router import router as repos_router
from src.schemas.account import User
from src.socket_manager import initialize_socket
from src.task_manager import TaskManager
from src.utils.dev_utils import (
    run_local_git_consumer,
    run_redis,
    stop_redis,
)
from src.utils.logging import logger
from src.utils.rate_limiter import limiter
from src.waitlist.router import router as waitlist_router

kwargs: dict[str, Any] = {}
if not DEV:
    kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DEV and not IS_DOCKER:
        await run_redis()
        await run_local_git_consumer()
    try:
        yield
    finally:
        if DEV and not IS_DOCKER:
            await stop_redis()


app: FastAPI = FastAPI(title="Speck API", version="0.0.1", lifespan=lifespan, **kwargs)
if DEV and not USING_NGINX:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(account_auth_router)
app.include_router(analytics_router)
app.include_router(waitlist_router)

app.include_router(billing_router)
app.include_router(account_logging_router)
app.include_router(github_router)
app.include_router(repos_router)
app.include_router(client_scripts_router)
sio: socketio.AsyncServer = initialize_socket(app)


user_socket_map: dict[str, User] = {}  # socket_id -> user
disconnect_timers: dict[str, asyncio.Task] = {}


@app.get("/")
async def root():
    return RedirectResponse(url="https://speck.sh")


async def is_user_connected(user: User, new_socket_id: str = None) -> bool:
    assigned_worker: str | None = await RedisManager.get_worker_for_user(user.id)
    if assigned_worker and assigned_worker != RedisManager.worker_id:
        return False

    if any(
        socket_user.id == user.id
        for socket_id, socket_user in user_socket_map.items()
        if socket_id != new_socket_id
    ):
        return True

    return False


@sio.on("connect")
async def connect(socket_id: str, env: dict[str, str], auth_data: dict[str, str]):
    token: str | None = auth_data.get("HTTP_AUTHORIZATION")
    is_preview: bool = auth_data.get("is_preview", False)

    if is_preview:
        logger.info(f"[PREVIEW] Preview connection: {socket_id}")
        return

    if not token:
        logger.warning(f"[UNAUTHORIZED] Unauthorized connection: {socket_id}")
        await sio.emit("unauthorized", to=socket_id)
        await sio.disconnect(socket_id)
        return

    try:
        user: User = verify_jwt_token(token)
        with logger.contextualize(email=user.email, name=user.name, id=user.id):
            if not is_user_subscribed(user):
                logger.warning(f"[UNAUTHORIZED] User not subscribed: {user.email}")
                await sio.emit("unauthorized", to=socket_id)
                await sio.disconnect(socket_id)
                return

            assigned_worker: str | None = await RedisManager.get_worker_for_user(
                user.id
            )
            if isinstance(assigned_worker, bytes):
                assigned_worker = assigned_worker.decode("utf-8")
            current_worker: str = RedisManager.worker_id

            if assigned_worker and (
                assigned_worker != current_worker
                and not (  # if we're switching to or from dev-prod
                    current_worker.startswith("dev-worker")
                    or assigned_worker.startswith("dev-worker")
                )
            ):
                logger.info(
                    f"User {user.email} should connect to worker {assigned_worker}. Current worker: {current_worker}"
                )
                await sio.emit(
                    "worker_redirect", {"worker_id": assigned_worker}, to=socket_id
                )
                await sio.disconnect(socket_id)
                return

            user_socket_map[socket_id] = user

    except Exception as e:
        logger.warning(e)
        logger.warning(traceback.format_exc())
        await sio.emit("unauthorized", to=socket_id)
        await sio.disconnect(socket_id)
        return


async def _check_and_disconnect_socket(
    socket_id: str, existing_socket_id: str, task_id: str
):
    """Check if socket is still connected after delay and disconnect if needed."""
    logger.info(
        f"Checking if socket is still connected - comparing {socket_id} and {existing_socket_id}"
    )
    await asyncio.sleep(1)

    with suppress(KeyError):
        if task_id in sio.rooms(existing_socket_id):
            logger.info(
                f"Socket is still connected, not initializing, disconnecting {existing_socket_id}"
            )
            await sio.emit(
                "task_data",
                {
                    "message_type": "force_reconnected",
                    "data": {},
                    "repo_id": "",
                },
                to=socket_id,
                ignore_queue=True,
            )
            await sio.emit(
                "task_data",
                {
                    "message_type": "already_connected",
                    "data": {},
                    "repo_id": "",
                },
                to=existing_socket_id,
                ignore_queue=True,
            )
            await sio.disconnect(existing_socket_id)


@sio.on("initialize")
async def initialize(socket_id: str, data: dict[str, str]):
    is_preview: bool = data.get("is_preview", False)
    task_id: str | None = data.get("task_id")

    if is_preview:
        logger.info(f"[PREVIEW] Preview connection: {socket_id}")
        await PreviewManager.user_connect(task_id, socket_id)
        return

    user: User = user_socket_map.get(socket_id)
    assert user is not None, "User not found in socket map"

    assigned_worker: str | None = await RedisManager.get_worker_for_user(user.id)
    if isinstance(assigned_worker, bytes):
        assigned_worker = assigned_worker.decode("utf-8")

    await sio.enter_room(socket_id, task_id)
    if (
        await is_user_connected(user)
        and TaskManager.get_task_from_id(task_id)
        and (existing_socket_id := TaskManager.get_task_from_id(task_id).user_socket_id)
    ):
        asyncio.create_task(
            _check_and_disconnect_socket(socket_id, existing_socket_id, task_id)
        )

    if not assigned_worker:
        await RedisManager.set_worker_for_user(user.id)

    with logger.contextualize(email=user.email, name=user.name, id=user.id):
        if not task_id:
            raise ValueError("Task id not found in request")

        try:
            await TaskManager.user_connect(user, task_id, socket_id)
        except Exception as e:
            await sio.emit(
                "task_data",
                {
                    "type": "error",
                    "data": {"message": str(e)},
                    "repo_id": "",
                },
                to=socket_id,
            )
            await sio.disconnect(socket_id)
            logger.error(e)
            logger.error(traceback.format_exc())


@sio.on("disconnect")
async def disconnect(socket_id: str):
    did_disconnect_preview: bool = False
    if socket_id in PreviewManager.socket_map:
        did_disconnect_preview = await PreviewManager.user_disconnect(socket_id)
        if did_disconnect_preview:
            return

    if socket_id in user_socket_map:
        user: User = user_socket_map[socket_id]
        with logger.contextualize(email=user.email, name=user.name, id=user.id):
            for room in sio.rooms(socket_id):
                TaskManager.socket_disconnect(socket_id)
                await sio.leave_room(socket_id, room)

            logger.info(f"Disconnected: {socket_id} - {user.email}")
            user_socket_map.pop(socket_id, None)
    else:
        logger.info(f"Disconnected unknown user: {socket_id}")


@sio.on("user_message")
async def handle_user_message(socket_id, *args, **kwargs):
    user: User = user_socket_map.get(socket_id)
    assert user is not None, "User not found in socket map"

    with logger.contextualize(email=user.email, name=user.name, id=user.id):
        logger.info(f"Got message from {user.email}")
        data: dict[str, str] = args[0]
        await TaskManager.handle_user_message(user, data, sio)


@sio.on("submit_recording")
async def submit_recording(socket_id: str, data: dict[str, str]):
    user: User = user_socket_map.get(socket_id)
    assert user is not None, "User not found in socket map"
    await TaskManager.handle_submitted_recording(user, data)


@sio.on("submit_report")
async def submit_report(socket_id: str, data: dict[str, str]):
    user: User = user_socket_map.get(socket_id)
    assert user is not None, "User not found in socket map"
    await TaskManager.handle_submitted_report(user, data)


@sio.on("start_task")
async def start_task(socket_id: str, data: dict[str, str]):
    logger.info(f"Starting task: {data}")
    user: User = user_socket_map.get(socket_id)
    task_id: str = data["task_id"]
    assert user is not None, "User not found in socket map"
    await TaskManager.create_task(user, task_id, socket_id)


@sio.on("restart_task")
async def restart_task(socket_id: str, data: dict[str, str]):
    user: User = user_socket_map.get(socket_id)
    task_id: str = data["task_id"]
    assert user is not None, "User not found in socket map"
    await TaskManager.restart_task(task_id)


@sio.on("stop_task")
async def stop_task(socket_id: str, data: dict[str, str]):
    user: User = user_socket_map.get(socket_id)
    assert user is not None, "User not found in socket map"
    await TaskManager.stop_task(user)


@sio.on("soft_close_task")
async def soft_close_task(socket_id: str, data: dict[str, str]):
    """When we want the task to continue without the user connected"""
    user: User = user_socket_map.get(socket_id)
    assert user is not None, "User not found in socket map"
    await TaskManager.soft_close_task(user, data["task_id"])
    await sio.disconnect(socket_id)


@app.get("/rate_limit")
@limiter.limit("2/minute", error_message="Rate limit exceeded")
async def rate_limit(request: Request):
    return JSONResponse({"message": "Not rate limited"})


def header_matches_env_var(header_value: str | None) -> bool:
    """Validates the Azure health check request by comparing the header with WEBSITE_AUTH_ENCRYPTION_KEY."""
    if not header_value:
        return False
    env_var = os.getenv("WEBSITE_AUTH_ENCRYPTION_KEY")
    if not env_var:
        return True  # If env var isn't set, we're not in Azure, so allow the check
    hashed_value = base64.b64encode(sha256(env_var.encode("utf-8")).digest()).decode(
        "utf-8"
    )
    return hashed_value == header_value


@app.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint for Azure App Service.
    - Must return 200-299 status code when healthy
    - Validates Azure internal token when present
    - Checks critical dependencies
    """
    auth_header = request.headers.get("x-ms-auth-internal-token")
    if auth_header and not header_matches_env_var(auth_header):
        return JSONResponse(status_code=401, content={"status": "unauthorized"})

    return JSONResponse(
        {
            "status": "healthy",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )


if __name__ == "__main__":
    import tracemalloc

    import uvicorn

    try:
        tracemalloc.start()
        uvicorn.run(
            "src.api:app",
            host="0.0.0.0",
            port=8080,
            reload=True,
            lifespan="on",
            workers=1,
        )
    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
    finally:
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")
        logger.warning("[ Top 10 ]")
        for stat in top_stats[:10]:
            logger.warning(stat)
