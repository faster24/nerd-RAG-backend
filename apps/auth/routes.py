from fastapi import APIRouter, HTTPException, status, Request, Depends
from apps.auth.service import auth_service
from apps.users.schemas import (
    UserCreate,
    UserLogin,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    MessageResponse,
)
from apps.users.models import User
from core.middleware import verify_firebase_token
from core.auth_dependencies import get_user_role, require_admin, require_teacher, require_student
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(user_data: UserCreate):
    try:
        result = await auth_service.register_user(user_data)
        user = User.from_firebase_user(result["firebase_user"])

        return LoginResponse(
            user=user,
            tokens={
                "id_token": result["tokens"]["idToken"],
                "refresh_token": result["tokens"]["refreshToken"],
                "expires_in": result["tokens"].get("expiresIn", 3600),
                "token_type": "Bearer",
            },
        )
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/login", response_model=LoginResponse)
async def login(user_data: UserLogin):
    try:
        result = await auth_service.login_user(user_data)
        user = User.from_firebase_user(result["firebase_user"])

        return LoginResponse(
            user=user,
            tokens={
                "id_token": result["tokens"]["idToken"],
                "refresh_token": result["tokens"]["refreshToken"],
                "access_token": result["tokens"].get("accessToken"),
                "expires_in": result["tokens"].get("expiresIn", 3600),
                "token_type": "Bearer",
            },
        )
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}",
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(refresh_request: RefreshTokenRequest):
    try:
        result = await auth_service.refresh_tokens(refresh_request.refresh_token)

        return RefreshTokenResponse(
            id_token=result["id_token"],
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=result.get("expires_in", 3600),
        )
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}",
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, user_data: dict = Depends(verify_firebase_token)):
    try:
        await auth_service.logout_user(user_data["uid"])

        return MessageResponse(message="Logged out successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}",
        )


@router.post("/password-reset", response_model=MessageResponse)
async def request_password_reset(reset_request: PasswordResetRequest):
    try:
        await auth_service.send_password_reset(reset_request.email)

        return MessageResponse(
            message="Password reset email sent if account exists"
        )
    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset request failed: {str(e)}",
        )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(reset_confirm: PasswordResetConfirm):
    try:
        await auth_service.confirm_password_reset(
            reset_confirm.oob_code, reset_confirm.new_password
        )

        return MessageResponse(message="Password reset successfully")
    except Exception as e:
        logger.error(f"Password reset confirmation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password reset confirmation failed: {str(e)}",
        )


@router.get("/me")
async def get_current_user(decoded_token: dict = Depends(verify_firebase_token)):
    user = await auth_service.get_user_by_uid(decoded_token["uid"])
    role = get_user_role(decoded_token)
    return User.from_firebase_user(user, role=role)


@router.get("/admin/dashboard", dependencies=[Depends(require_admin)])
async def admin_dashboard():
    return {"message": "Welcome to admin dashboard"}


@router.get("/teacher/dashboard", dependencies=[Depends(require_teacher)])
async def teacher_dashboard():
    return {"message": "Welcome to teacher dashboard"}


@router.get("/student/dashboard", dependencies=[Depends(require_student)])
async def student_dashboard():
    return {"message": "Welcome to student dashboard"}


@router.post("/admin/set-role", dependencies=[Depends(require_admin)])
async def set_user_role_endpoint(data: dict):
    try:
        await auth_service.set_user_role(data["uid"], data["role"])
        return {"message": f"Role updated to {data['role']}"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to set role: {str(e)}",
        )