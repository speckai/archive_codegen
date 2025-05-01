from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.config import SUPABASE_JWT_SECRET
from src.schemas.account import User


def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials | str = Depends(HTTPBearer()),
) -> User:
    token = (
        credentials.credentials
        if isinstance(credentials, HTTPAuthorizationCredentials)
        else credentials
    )
    try:
        payload: dict[str, Any] = jwt.decode(
            token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
        )
        user_metadata: dict[str, Any] = payload.get("user_metadata", {})
        name: str | None = user_metadata.get("full_name")
        if name:
            name = (
                name.replace('"', "").replace("'", "").replace("“", "").replace("”", "")
            )

        user: User = User(
            id=payload["sub"],
            email=payload["email"],
            phone=payload.get("phone"),
            name=name,
            picture=user_metadata.get("picture"),
            user_metadata=user_metadata,
        )
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
