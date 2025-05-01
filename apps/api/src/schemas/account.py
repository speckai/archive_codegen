from typing import Any

from pydantic import BaseModel


class MutableUserSettings(BaseModel):
    """
    User fields that can be mutated by the user.
    """

    first_name: str
    last_name: str
    email: str


class User(BaseModel):
    id: str
    email: str
    phone: str | None = None
    name: str | None = None
    picture: str | None = None
    stripe_customer_id: str | None = None
    user_metadata: dict[str, Any] | None = None

    @property
    def first_name(self) -> str | None:
        return self.name.split()[0] if self.name else None

    @property
    def last_name(self) -> str | None:
        if self.name:
            parts = self.name.split()
            return " ".join(parts[1:]) if len(parts) > 1 else None
        return None

    @property
    def github_account_id(self) -> int | None:
        if not self.user_metadata:
            return None
        if self.user_metadata.get("iss") != "https://api.github.com":
            return None
        return int(self.user_metadata.get("provider_id"))

    @property
    def github_username(self) -> str | None:
        if not self.user_metadata:
            return None
        if self.user_metadata.get("iss") != "https://api.github.com":
            return None
        return self.user_metadata.get("user_name")
