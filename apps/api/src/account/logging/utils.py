from src.database import Database


def check_valid_user(email: str) -> bool:
    user = Database.users_collection.find_one({"email": email})
    if user is None:
        return False
    return True
