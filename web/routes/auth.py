from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/api/v1/system/auth", tags=["Auth"])


class AuthStatusResponse(BaseModel):
    authenticated: bool
    providers: list[Any]
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str | None = None
    password: str | None = None


@router.get("/status", response_model=AuthStatusResponse)
def auth_status():
    # TODO: reflect provider auth states (tokens live in config/db only)
    return AuthStatusResponse(authenticated=False, providers=[])


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    try:
        from core.hook_manager import hook_manager

        plugin_auth = hook_manager.apply_filters(
            "AUTHENTICATE_USER",
            None,
            username=payload.username,
            password=payload.password,
            payload=payload.model_dump(),
        )
        if (
            plugin_auth is not None
            and isinstance(plugin_auth, dict)
            and plugin_auth.get("authenticated") is True
        ):
            # Plugin successfully authenticated
            import uuid

            from core.security import generate_auth_token

            csrf_token = str(uuid.uuid4())
            token = generate_auth_token(
                payload.username or plugin_auth.get("user", "unknown"), csrf_token
            )

            response.set_cookie(
                "echo_auth", token, httponly=True, secure=False, samesite="strict"
            )
            response.set_cookie(
                "echo_csrf", csrf_token, httponly=False, secure=False, samesite="strict"
            )
            return plugin_auth
    except Exception as e:
        import logging

        logging.getLogger("auth").error(f"Error in AUTHENTICATE_USER hook: {e}")

    try:
        from core.security import generate_auth_token, verify_user_credentials

        verify_user_credentials(payload.username, payload.password)

        import uuid

        csrf_token = str(uuid.uuid4())
        token = generate_auth_token(payload.username, csrf_token)

        response.set_cookie(
            "echo_auth", token, httponly=True, secure=False, samesite="strict"
        )
        response.set_cookie(
            "echo_csrf", csrf_token, httponly=False, secure=False, samesite="strict"
        )
        return {"authenticated": True, "user": payload.username}
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")
