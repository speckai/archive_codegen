from datetime import datetime

from src.database import Database


def add_unconfirmed_waitlist(
    email: str, first_name: str, last_name: str, company: str
) -> None:
    Database.waitlists_collection.insert_one(
        {
            "email": email,
            "confirmed": False,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "created_at": datetime.now(),
        }
    )


def confirm_waitlist(email: str) -> None:
    Database.waitlists_collection.update_one(
        {"email": email}, {"$set": {"confirmed": True}}
    )
