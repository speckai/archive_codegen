from fastapi import APIRouter
from fastapi.requests import Request
from src.account.logging.utils import check_valid_user

router = APIRouter(prefix="/account/logging")


@router.post("/valid-user")
async def valid_user(request: Request):
    data = await request.json()
    email = data.get("email")

    return {"valid": check_valid_user(email)}
