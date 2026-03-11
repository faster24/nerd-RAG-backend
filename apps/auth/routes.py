import logging

from fastapi import APIRouter, HTTPException, status, Request, Depends

from apps.auth.service import auth_service
from apps.users.models import User
from apps.users.schemas import (
    UserCreate,
    UserLogin,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    MessageResponse,
    SetRoleRequest, UserResponse,
)
from core.auth_dependencies import get_user_role, require_admin, require_teacher
from core.middleware import verify_firebase_token
from core.roles import Role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password. Returns user data and authentication tokens.",
)
async def register(user_data: UserCreate):
    try:
        result = await auth_service.register_user(user_data)
        firebase_user = result["firebase_user"]

        return LoginResponse(
            user=UserResponse(
                uid=firebase_user.uid,
                email=firebase_user.email,
                email_verified=firebase_user.email_verified,
                display_name=firebase_user.display_name,
                photo_url=firebase_user.photo_url,
                provider_id=firebase_user.provider_id,
                created_at=str(firebase_user.user_metadata.creation_timestamp),
                role=None,
            ),
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
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate user",
    description="Login with email and password. Returns user data and authentication tokens.",
)
async def login(user_data: UserLogin):
    try:
        result = await auth_service.login_user(user_data)
        firebase_user = result["firebase_user"]

        return LoginResponse(
            user=UserResponse(
                uid=firebase_user.uid,
                email=firebase_user.email,
                email_verified=firebase_user.email_verified,
                display_name=firebase_user.display_name,
                photo_url=firebase_user.photo_url,
                provider_id=firebase_user.provider_id,
                created_at=str(firebase_user.user_metadata.creation_timestamp),
                role=None,
            ),
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
            detail=str(e),
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh authentication tokens",
    description="Exchange refresh token for new access and ID tokens.",
)
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
            detail=str(e),
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Revoke refresh tokens and log out the current user.",
)
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


@router.post(
    "/password-reset",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Send password reset email to the specified email address.",
)
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


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Confirm password reset",
    description="Confirm password reset using the reset code and set new password.",
)
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


@router.get(
    "/me",
    response_model=User,
    summary="Get current user profile",
    description="Retrieve the current authenticated user's profile information including role.",
)
async def get_current_user(decoded_token: dict = Depends(verify_firebase_token)):
    user = await auth_service.get_user_by_uid(decoded_token["uid"])
    role = get_user_role(decoded_token)
    return User.from_firebase_user(user, role=role)


@router.get(
    "/admin/dashboard",
    summary="Admin dashboard",
    description="Access admin-only dashboard. Requires admin role.",
)
async def admin_dashboard(decoded_token: dict = Depends(require_admin)):
    return {"message": "Welcome to admin dashboard"}


@router.get(
    "/teacher/dashboard",
    summary="Teacher dashboard",
    description="Access teacher dashboard. Requires teacher or admin role.",
)
async def teacher_dashboard(decoded_token: dict = Depends(require_teacher)):
    return {"message": "Welcome to teacher dashboard"}


@router.get(
    "/student/dashboard",
    summary="Student dashboard",
    description="Access student dashboard. Requires any authenticated role.",
)
async def student_dashboard(decoded_token: dict = Depends(verify_firebase_token)):
    return {"message": "Welcome to student dashboard"}


@router.put(
    "/users/{uid}/role",
    response_model=MessageResponse,
    summary="Update user role",
    description="Update the role of a specific user. Requires admin privileges.",
)
async def update_user_role(uid: str, role_data: SetRoleRequest, decoded_token: dict = Depends(require_admin)):
    try:
        if role_data.role not in [r.value for r in Role]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be one of: student, teacher, admin",
            )
        await auth_service.set_user_role(uid, role_data.role)
        return MessageResponse(message=f"Role updated to {role_data.role}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Role update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {str(e)}",
        )