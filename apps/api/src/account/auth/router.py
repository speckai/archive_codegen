from fastapi import APIRouter
from gotrue.types import User, UserResponse
from src.config import SUPABASE_KEY, SUPABASE_URL
from src.database import Database
from supabase import AsyncClient, create_client

router = APIRouter(prefix="/account/auth")


def _get_existing_user(email: str) -> User | None:
    user_id: str | None = Database.get_user_id_from_email(email)
    supabase: AsyncClient = create_client(SUPABASE_URL, SUPABASE_KEY)
    if user_id:
        user_response: UserResponse = supabase.auth.admin.get_user_by_id(user_id)
        return user_response.user

    user_list: list[User] = supabase.auth.admin.list_users()
    return next((user for user in user_list if user.email == email), None)


@router.get("/exists")
async def check_account_exists(email: str) -> dict[str, str | bool]:  # TODO: REDO THIS
    try:
        user: User | None = _get_existing_user(email)

        if not user:
            return {"exists": False}

        if "email" not in user.app_metadata.get("providers", []):
            return {"exists": "oauth"}

        email_verified = user.user_metadata.get("email_verified", False)

        return {"exists": True} if email_verified else {"exists": "unverified"}

    except Exception as e:
        print(f"Error checking account: {str(e)}")
        return {"error": "Unable to check account status"}
