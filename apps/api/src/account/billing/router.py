from urllib.parse import quote

import stripe
from fastapi import APIRouter, Depends, HTTPException
from src.account.billing.utils import get_subscription_details, is_user_subscribed
from src.account.security import verify_jwt_token
from src.config import DEV, STRIPE_API_KEY
from src.schemas.account import User

stripe.api_key = STRIPE_API_KEY

router = APIRouter(prefix="/account/billing")

SUBSCRIPTION_LINK = (
    "https://buy.stripe.com/test_cN2bJ349Yerk28U000"
    if DEV
    else "https://buy.stripe.com/6oEcQzaDUeLubcseV3"
)

user_dependency = Depends(verify_jwt_token)


@router.get("/is_subscribed")
async def check_subscription(user: User = user_dependency) -> dict:
    """
    Check if the user is subscribed to the Speck plan.
    """
    try:
        return {
            "is_subscribed": is_user_subscribed(user),
        }
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/details")
async def get_subscription_details_route(
    user: User = user_dependency,
) -> dict:
    subscription: stripe.Subscription | None = get_subscription_details(user)
    encoded_email: str = quote(user.email)

    if not subscription or subscription.status != "active":
        return {
            "subscription_found": False,
            "subscription_link": f"{SUBSCRIPTION_LINK}?prefilled_email={encoded_email}",
        }

    days_subscribed: int = (
        subscription.current_period_start - subscription.created
    ) // (24 * 60 * 60)

    portal_session: stripe.billing_portal.Session = (
        stripe.billing_portal.Session.create(
            customer=subscription.customer,
            return_url="https://app.speck.sh/settings",
        )
    )

    return {
        "subscription_found": True,
        "manage_link": portal_session.url,
        "monthly_amount": subscription.plan.amount / 100,
        "next_billing_date": subscription.current_period_end,
        "days_subscribed": days_subscribed,
        "currency": subscription.currency,
    }


if __name__ == "__main__":
    print(get_subscription_details("123"))
