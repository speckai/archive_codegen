import asyncio
import os
import re
import traceback
from collections import defaultdict
from typing import Any

import aiohttp
import websockets
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.websockets import WebSocketState
from loguru import logger
from src.manager.container_cache import container_cache
from src.manager.container_manager import ContainerInfo, container_manager
from src.schemas import ContainerRequest

router: APIRouter = APIRouter()

SPECK_SCRIPT_PATH: str = os.path.join(
    os.path.dirname(__file__), "assets", "get_script.js"
)
SPECK_SCRIPT: str = open(SPECK_SCRIPT_PATH, "r").read()
SPECK_ERROR_TEMPLATE_PATH: str = os.path.join(
    os.path.dirname(__file__), "assets", "error_template.html"
)
SPECK_ERROR_TEMPLATE: str = open(SPECK_ERROR_TEMPLATE_PATH, "r").read()


_client_containers: dict[str, tuple[str, str]] = defaultdict(lambda: (None, None))


@router.get("/health")
async def health_check():
    """Health check endpoint that forwards to container."""
    try:
        if not container_manager.is_local:
            await container_manager.ecs.list_clusters()
        return {
            "status": "healthy",
            "mode": "local" if container_manager.is_local else "aws",
            "cluster": container_manager.cluster_name,
            "network": {
                "subnet_ids": container_manager.subnet_ids,
                "security_group_id": container_manager.security_group_id,
            },
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.post("/containers/start")
async def start_container(request: ContainerRequest) -> ContainerInfo:
    """Start a container for a user."""
    try:
        logger.warning(f"Creating container for {request.user_id}/{request.session_id}")
        container: ContainerInfo = await container_manager.start_container(
            request.user_id, request.session_id
        )
        return container
    except Exception as e:
        logger.error(f"Failed to start container: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/containers/stop")
async def stop_container(request: ContainerRequest) -> dict[str, str]:
    """Stop a user's container."""
    try:
        success: bool = await container_manager.kill_container(
            request.user_id, request.session_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Container not found")

        return {"status": "stopped"}
    except Exception as e:
        logger.error(f"Failed to stop container: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/containers/{user_id}/{session_id}")
async def get_session_container_info(user_id: str, session_id: str) -> ContainerInfo:
    """Get information about a user's container."""
    container: ContainerInfo | None = container_cache.get(user_id, session_id)
    if not container:
        container = await container_manager.get_container_info(user_id, session_id)

    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return container


@router.get("/containers/{user_id}/list")
async def list_user_sandboxes(user_id: str) -> dict:
    """Get all sandboxes for a user."""
    sandboxes: dict[str, ContainerInfo] = container_manager.get_user_sandboxes(user_id)
    return {
        "user_id": user_id,
        "sandboxes": {
            session_id: {
                "container_ip": info.container_ip,
                "container_port": info.container_port,
                "status": info.status,
                "created_at": info.created_at,
                "task_id": info.task_id,
            }
            for session_id, info in sandboxes.items()
        },
    }


@router.get("/containers/list")
async def list_containers() -> dict:
    """Get all containers with their status."""
    containers: dict = await container_manager.list_containers()
    return {
        "containers": containers,
        "active_containers": len(containers.get("active_containers", [])),
        "warm_containers": len(containers.get("warm_containers", [])),
    }


@router.post("/containers/set_preview_port")
async def set_preview_port(body: dict[str, str]) -> dict:
    user_id: str = body["user_id"]
    session_id: str = body["session_id"]
    port: str = body["port"]
    success: bool = await container_manager.set_preview_port(
        user_id, session_id, int(port)
    )

    return {"success": success}


@router.get("/dir_cache/list")
async def list_dir_caches() -> dict:
    """List all directory caches."""
    try:
        caches: list[dict] = await container_manager.list_dir_caches()
        return {"caches": caches}
    except Exception as e:
        logger.error(f"Failed to list directory caches: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/dir_cache/delete/{cache_name}")
async def delete_dir_cache(cache_name: str) -> dict:
    """Delete a directory cache."""
    try:
        success: bool = await container_manager.delete_dir_cache(cache_name)
        if not success:
            raise HTTPException(
                status_code=404, detail="Cache not found or could not be deleted"
            )
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete directory cache: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.api_route(
    "/preview/{user_id}/{session_id}",
    methods=["GET", "POST", "PUT", "DELETE"],
)
async def redirect_to_preview(request: Request, user_id: str, session_id: str):
    """Redirect to the version with trailing slash."""
    return Response(
        status_code=307,
        headers={"Location": f"/preview/{user_id}/{session_id}/"},
    )


@router.api_route(
    "/preview/{user_id}/{session_id}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
)
async def forward_to_container(
    request: Request, user_id: str, session_id: str, path: str
):
    container: ContainerInfo | None = container_cache.get(user_id, session_id)

    if not container:
        logger.warning("Getting info")
        container = await container_manager.get_container_info(user_id, session_id)
    else:
        logger.info(f"Container found in cache: {user_id}/{session_id}")

    if not container:
        logger.warning(f"Container not found: {user_id}/{session_id}")
        return Response(
            content=SPECK_ERROR_TEMPLATE.format(error_message="Container not found"),
            status_code=404,
            media_type="text/html",
        )

    if container.status != "RUNNING":
        raise HTTPException(status_code=503, detail="Container not ready")

    target_host: str = (
        "container" if container.container_ip == "localhost" else container.container_ip
    )

    port: int = container.preview_port or 3000

    clean_path: str = path.strip("/")
    target_url: str = f"http://{target_host}:{port}"
    if clean_path:
        # Fix for double preview paths - remove all occurrences of preview/user_id/session_id/
        prefix = f"preview/{user_id}/{session_id}/"
        while clean_path.startswith(prefix):
            clean_path = clean_path[len(prefix) :]
    if clean_path:
        target_url = f"{target_url}/{clean_path}"

    logger.info(
        f"Router A: forwarding to - user_id={user_id}, session_id={session_id}, path={path}, target_url={target_url}"
    )

    body: bytes = await request.body()
    headers: dict[str, str] = dict(request.headers)
    headers.pop("host", None)

    hop_by_hop_headers: list[str] = [
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    ]
    for header in hop_by_hop_headers:
        headers.pop(header.lower(), None)

    # For nextjs
    headers["x-forwarded-host"] = request.headers.get("host", "")
    headers["x-forwarded-proto"] = request.headers.get("x-forwarded-proto", "http")
    headers["x-real-ip"] = request.headers.get("x-real-ip", request.client.host)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=body,
                params=request.query_params,
                timeout=30,
                allow_redirects=True,
                compress=False,
            ) as response:
                content_type: str = response.headers.get("content-type", "")

                response_headers: dict[str, str] = {
                    k: v
                    for k, v in response.headers.items()
                    if k.lower() not in hop_by_hop_headers
                    and k.lower()
                    not in [
                        "content-encoding",
                        "content-length",
                        "x-frame-options",
                    ]
                }

                response_headers["X-Frame-Options"] = "ALLOWALL"
                response_headers["Content-Security-Policy"] = (
                    response_headers.get("Content-Security-Policy", "")
                    + "; frame-ancestors *"
                )

                response_headers["Access-Control-Allow-Origin"] = "*"
                response_headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, OPTIONS, PUT, DELETE"
                )
                response_headers["Access-Control-Allow-Headers"] = (
                    "DNT, User-Agent, X-Requested-With, If-Modified-Since, Cache-Control, Content-Type, Range, Authorization"
                )
                response_headers["Access-Control-Allow-Credentials"] = "true"
                response_headers["Access-Control-Expose-Headers"] = (
                    "Content-Length, Content-Range"
                )

                cookies_to_set: dict[str, str] = {
                    "sandbox_user_id": user_id,
                    "sandbox_session_id": session_id,
                }

                try:
                    # if clean_path.startswith("_next/static/") or clean_path.endswith(
                    #     (
                    #         ".js",
                    #         ".css",
                    #         ".woff",
                    #         ".woff2",
                    #         ".ttf",
                    #         ".png",
                    #         ".jpg",
                    #         ".jpeg",
                    #         ".gif",
                    #         ".ico",
                    #         ".svg",
                    #     )
                    # ):
                    #     content: bytes = await response.read()
                    #     response: Response = Response(
                    #         content=content,
                    #         status_code=response.status,
                    #         headers=response_headers,
                    #         media_type=content_type,
                    #     )

                    #     for cookie_name, cookie_value in cookies_to_set.items():
                    #         response.set_cookie(
                    #             cookie_name,
                    #             cookie_value,
                    #             max_age=3600,
                    #             httponly=False,  # Allow JavaScript access
                    #             samesite="none",  # Allow cross-origin access
                    #             secure=True,  # Required for SameSite=None
                    #         )
                    #     return response

                    # if clean_path.startswith("api/"):
                    #     response: StreamingResponse = StreamingResponse(
                    #         response.content.iter_any(),
                    #         status_code=response.status,
                    #         headers=response_headers,
                    #         media_type=content_type,
                    #     )

                    #     for cookie_name, cookie_value in cookies_to_set.items():
                    #         response.set_cookie(
                    #             cookie_name,
                    #             cookie_value,
                    #             max_age=3600,
                    #             httponly=False,  # Allow JavaScript access
                    #             samesite="none",  # Allow cross-origin access
                    #             secure=True,  # Required for SameSite=None
                    #         )
                    #     return response

                    content: bytes = await response.read()
                    if response.status == 500:
                        logger.error(f"Next.js server 500 error: {content.decode()}")

                    if "text/html" in content_type.lower():
                        logger.info("Injecting script")
                        html_content: str = content.decode("utf-8", errors="replace")
                        file_content: str = f"<script>{SPECK_SCRIPT}</script>"
                        logger.info(f"Script to inject: {file_content}")
                        pattern = re.compile(r"</body>", re.IGNORECASE)
                        html_content, num_subs = pattern.subn(
                            f"{file_content}</body>", html_content, count=1
                        )
                        if num_subs == 0:
                            html_content += file_content

                        modified_content = html_content.encode("utf-8")
                        response_headers["Content-Length"] = str(len(modified_content))
                        if "Content-Encoding" in response_headers:
                            del response_headers["Content-Encoding"]
                        content = modified_content

                    response: Response = Response(
                        content=content,
                        status_code=response.status,
                        headers=response_headers,
                        media_type=content_type,
                    )

                    for cookie_name, cookie_value in cookies_to_set.items():
                        response.set_cookie(
                            cookie_name,
                            cookie_value,
                            max_age=3600,  # 1 hour
                            httponly=False,  # Allow JavaScript access
                            samesite="none",  # Allow cross-origin access
                            secure=True,  # Required for SameSite=None
                        )
                    return response

                except Exception as e:
                    logger.error(f"Error processing response: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail="Error processing response from Next.js server",
                    ) from e

        except aiohttp.ClientError as e:
            logger.error(f"Error forwarding request: {e}")
            if "Cannot connect to host" in str(e):
                error_html = SPECK_ERROR_TEMPLATE.format(error_message="Unauthorized")
                return Response(
                    content=error_html,
                    status_code=404,
                    media_type="text/html",
                )
            raise HTTPException(
                status_code=502,
                detail=f"Error forwarding request: {str(e)}",
            ) from e


@router.websocket("/{full_path:path}")
async def websocket_proxy(websocket: WebSocket, full_path: str):
    client_subprotocols_header: str | None = websocket.headers.get(
        "sec-websocket-protocol"
    )
    if client_subprotocols_header:
        client_subprotocols = [
            token.strip() for token in client_subprotocols_header.split(",")
        ]
    else:
        client_subprotocols = []

    accepted_subprotocol: str | None = (
        client_subprotocols[0] if client_subprotocols else None
    )
    await websocket.accept(subprotocol=accepted_subprotocol)

    user_id: str | None = websocket.cookies.get("sandbox_user_id")
    session_id: str | None = websocket.cookies.get("sandbox_session_id")
    if not user_id or not session_id:
        referrer: str | None = websocket.headers.get("Referer")
        if referrer:
            parts = referrer.split("/preview/")
            if len(parts) > 1:
                path_parts = parts[1].split("/")
                if len(path_parts) >= 2:
                    user_id = path_parts[0]
                    session_id = path_parts[1]

    logger.info(f"WebSocket: user_id={user_id}, session_id={session_id}")
    if not user_id or not session_id:
        await websocket.close(code=1000, reason="Invalid user_id or session_id")
        return

    container: ContainerInfo | None = container_cache.get(user_id, session_id)

    if not container:
        container = await container_manager.get_container_info(user_id, session_id)

    if not container:
        await websocket.close(code=1013)
        return

    if container.status != "RUNNING":
        await websocket.close(code=1013)
        return

    headers: dict[str, str] = {}
    excluded_headers = {
        "upgrade",
        "connection",
        "sec-websocket-key",
        "sec-websocket-version",
        "sec-websocket-extensions",
        "sec-websocket-protocol",
        "host",
        "origin",
    }

    for header_name, header_value in websocket.headers.items():
        header_name_lower = header_name.lower()
        if header_name_lower not in excluded_headers:
            headers[header_name_lower] = header_value

    port: int = container.preview_port or 3000
    container_ip: str = (
        "container" if container.container_ip == "localhost" else container.container_ip
    )

    backend_url = f"ws://{container_ip}:{port}/{full_path.lstrip('/')}"
    if websocket.query_params:
        backend_url += f"?{websocket.query_params}"

    headers: dict[str, str] = {}
    excluded_headers = {
        "upgrade",
        "connection",
        "sec-websocket-key",
        "sec-websocket-version",
        "sec-websocket-extensions",
        "sec-websocket-protocol",
        "host",
        "origin",
    }

    for header_name, header_value in websocket.headers.items():
        header_name_lower = header_name.lower()
        if header_name_lower not in excluded_headers:
            headers[header_name_lower] = header_value

    headers.pop("origin", None)
    headers.pop("host", None)

    origin_header = f"http://localhost:{port}"

    cookies = websocket.cookies
    cookies_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    if cookies_header:
        headers["cookie"] = cookies_header
    websockets_connect_kwargs: dict[str, Any] = {
        "additional_headers": dict(headers),
        "open_timeout": 10,
        "origin": origin_header,
        "compression": None,
    }

    if client_subprotocols:
        websockets_connect_kwargs["subprotocols"] = client_subprotocols

    try:
        async with websockets.connect(
            backend_url,
            **websockets_connect_kwargs,
            max_size=10 * 1024 * 1024,
        ) as backend_ws:

            async def client_to_backend():
                try:
                    while True:
                        message = await websocket.receive()
                        message_type = message.get("type")
                        if message_type == "websocket.receive":
                            if "text" in message:
                                await backend_ws.send(message["text"])
                            elif "bytes" in message:
                                await backend_ws.send(message["bytes"])
                        elif message_type == "websocket.disconnect":
                            await backend_ws.close()
                            break
                except WebSocketDisconnect:
                    await backend_ws.close()
                except Exception as e:
                    logger.error(f"Error from client_to_backend: {str(e)}")
                    logger.error(traceback.format_exc())
                    await backend_ws.close()

            async def backend_to_client():
                try:
                    while True:
                        message = await backend_ws.recv()
                        if isinstance(message, str):
                            await websocket.send_text(message)
                        elif isinstance(message, bytes):
                            await websocket.send_bytes(message)
                except websockets.exceptions.ConnectionClosed:
                    if websocket.application_state != WebSocketState.DISCONNECTED:
                        await websocket.close()
                except Exception as e:
                    logger.error(f"Error from backend_to_client: {e}")
                    if websocket.application_state != WebSocketState.DISCONNECTED:
                        await websocket.close()

            await asyncio.gather(client_to_backend(), backend_to_client())

    except websockets.exceptions.InvalidStatusCode as e:
        logger.error(f"WebSocket connection error: {e}")
        logger.error(traceback.format_exc())
        await websocket.close(code=1011)  # Internal Error
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
        await websocket.close(code=1011)  # Internal Error


def get_client_ip(request: Request) -> str:
    """Get the real client IP from request headers."""
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.client.host


# IMPORTANT: Keep all direct API endpoints above this line
# The following catch-all route should be LAST as it matches any path
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def forward_static_assets(request: Request, path: str):
    """Forward static asset requests using cookies for routing."""
    user_id: str | None = request.cookies.get("sandbox_user_id")
    session_id: str | None = request.cookies.get("sandbox_session_id")

    client_ip = get_client_ip(request)
    logger.info(
        f"Router: initial cookie values - user_id={user_id}, session_id={session_id}, client_ip={client_ip}"
    )

    if not user_id or not session_id:
        referrer: str | None = request.headers.get("Referer")
        logger.info(f"Router: no cookies found, checking referrer={referrer}")
        if referrer:
            parts = referrer.split("/preview/")
            if len(parts) > 1:
                path_parts = parts[1].split("/")
                if len(path_parts) >= 2:
                    user_id = path_parts[0]
                    session_id = path_parts[1]
                    logger.info(
                        f"Router: extracted from referrer - user_id={user_id}, session_id={session_id}"
                    )

    if not user_id or not session_id:
        user_id, session_id = _client_containers[client_ip]
        logger.info(
            f"Router: using last known container for {client_ip} - user_id={user_id}, session_id={session_id}"
        )

    if user_id and session_id:
        _client_containers[client_ip] = (user_id, session_id)

    logger.info(f"Router: final values - user_id={user_id}, session_id={session_id}")
    if not user_id or not session_id:
        raise HTTPException(status_code=400, detail="No active container found")

    logger.info(
        f"Router B: forwarding to - user_id={user_id}, session_id={session_id}, path={path}"
    )
    return await forward_to_container(request, user_id, session_id, f"{path}")
