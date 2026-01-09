"""Authentication router."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    """Current user information."""

    email: str
    name: str
    picture: str | None = None
    is_admin: bool = False


@router.post("/login", response_model=TokenResponse)
async def login() -> TokenResponse:
    """Login with Google OIDC.

    TODO: Implement Google OIDC authentication.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google OIDC authentication not yet implemented",
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user() -> UserInfo:
    """Get current authenticated user.

    TODO: Implement after auth is set up.
    """
    # Placeholder for development
    return UserInfo(
        email="dev@example.com",
        name="Development User",
        is_admin=True,
    )


@router.post("/logout")
async def logout() -> dict[str, str]:
    """Logout current user."""
    return {"message": "Logged out successfully"}
