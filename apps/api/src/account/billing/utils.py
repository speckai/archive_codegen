import time

import stripe
from src.database import Database, MongoUser
from src.schemas.account import User
from src.utils.logging import logger


def _get_customer_from_email(email: str) -> str | None:
    """
    Get the Stripe customer ID from the email.
    :param email: The db query email to get the customer ID from.
    :return: The Stripe customer ID.
    """
    assert email is not None and email != ""
    customers: stripe.Customer = stripe.Customer.list(email=email)

    if not customers.data:
        logger.warning(f"No Stripe customer found with email: {email}")
        return None

    return customers.data[0].id


def _get_customer_id(user: User) -> str | None:
    """
    Get the Stripe customer ID from the user.
    :param user: The user to get the customer ID from.
    :return: The Stripe customer ID.
    """
    mongo_user: MongoUser = MongoUser.from_user(user)
    if mongo_user.stripe_customer_id is None:
        mongo_user.stripe_customer_id = _get_customer_from_email(mongo_user.email)
        if mongo_user.stripe_customer_id is None:
            return None
        Database.update_user_property(
            mongo_user.id, "stripe_customer_id", mongo_user.stripe_customer_id
        )

    return mongo_user.stripe_customer_id


def get_subscription_details(user: User) -> stripe.Subscription | None:
    """
    Get the subscription details from the user.
    :param user: The user to get the subscription details from.
    :return: The subscription details.
    """
    customer_id: str | None = _get_customer_id(user)
    if customer_id is None:
        return None
    subscriptions: stripe.Subscription = stripe.Subscription.list(customer=customer_id)

    return subscriptions.data[0] if subscriptions.data else None


cached_is_subscribed: dict[str, tuple[bool, float]] = {}


def is_user_subscribed(user: User) -> bool:
    """
    Check if the user is subscribed.
    :param user: The user to check if they are subscribed.
    :return: True if the user is subscribed, False otherwise.
    """
    logger.info(f"Checking if user `{user.email}` is subscribed")
    if user.email.endswith("@speck.sh"):
        return True

    if user.id in cached_is_subscribed:
        cached_result, cached_time = cached_is_subscribed[user.id]
        if time.time() - cached_time < 600:
            return cached_result

    subscription: stripe.Subscription | None = get_subscription_details(user)
    is_subscribed: bool = (
        False if subscription is None else subscription.status == "active"
    )
    cached_is_subscribed[user.id] = (is_subscribed, time.time())
    return is_subscribed
