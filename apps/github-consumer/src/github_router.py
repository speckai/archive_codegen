import hashlib
import json
from typing import Any, Optional

from fastapi import APIRouter, Body, Header
from loguru import logger
from src.modules.account import handle_installation
from src.modules.issues import (
    handle_issue_closed,
    handle_new_issue,
    handle_pr_status_change,
)
from src.modules.locks import is_request_served, set_served_request

router: APIRouter = APIRouter(prefix="/github")


@router.post("/webhook")
async def webhook(
    body: dict[str, Any] = Body(...),
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
) -> dict[str, Any]:
    request_id: str = hashlib.sha256(json.dumps(body).encode()).hexdigest()

    if is_request_served(request_id):
        return {"success": False}

    set_served_request(request_id)

    # if x_github_event == "issue_comment":
    #     return await handle_issue_comment(body)

    if x_github_event == "installation":
        return await handle_installation(body)

    if x_github_event == "issues":
        action = body.get("action")
        if action == "opened":
            return await handle_new_issue(body)
        elif action in ["closed", "deleted", "reopened"]:
            return await handle_issue_closed(body)
        else:
            logger.info(f"Received unexpected issue action: {action}")

    if x_github_event == "pull_request":
        action = body.get("action")
        if action in ["closed", "reopened"]:
            return await handle_pr_status_change(body)

    return {"success": False}
