from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from src.emails.mail import send_waitlist_email
from src.utils.logging import logger
from src.utils.rate_limiter import limiter
from src.waitlist.utils import add_unconfirmed_waitlist, confirm_waitlist

router: APIRouter = APIRouter(prefix="/waitlist")


@router.post("/signup")
@limiter.limit("5/minute")
async def signup(request: Request):
    data: dict = await request.json()
    email: str = data.get("email")
    first_name: str = data.get("first")
    last_name: str = data.get("last")
    company: str = data.get("company")

    if email is None:
        raise HTTPException(status_code=400, detail="Email is required")
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")

    add_unconfirmed_waitlist(email, first_name, last_name, company)
    send_waitlist_email(email, first_name)

    return {"success": True}


@router.post("/confirm")
async def confirm(request: Request):
    data: dict = await request.json()
    email: str = data.get("email")

    if email is None:
        raise HTTPException(status_code=400, detail="Email is required")
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")

    confirm_waitlist(email)

    return {"success": True}


if __name__ == "__main__":
    try:
        add_unconfirmed_waitlist("lukejagg@gmail.com", "Luke", "Jagg", "Speck")
        send_waitlist_email("lukejagg@gmail.com", "Luke")
    except Exception as e:
        logger.warning(e)
    finally:
        confirm_waitlist("luke@tryspeck.com")
