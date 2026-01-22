from fastapi import HTTPException, status, Depends
from .roles import Role
from .middleware import verify_firebase_token


def get_user_role(decoded_token: dict) -> Role:
    """Extract user role from Firebase custom claims, default to STUDENT"""
    role = decoded_token.get("custom_claims", {}).get("role", Role.STUDENT)
    try:
        return Role(role)
    except ValueError:
        return Role.STUDENT


def check_role_access(user_role: Role, min_role: Role) -> bool:
    """Check if user role has sufficient access level"""
    hierarchy = {Role.STUDENT: 1, Role.TEACHER: 2, Role.ADMIN: 3}
    return hierarchy.get(user_role, 1) >= hierarchy[min_role]


def require_role(min_role: Role):
    """Dependency factory for role-based access control"""
    def dependency(decoded_token: dict = Depends(verify_firebase_token)) -> dict:
        user_role = get_user_role(decoded_token)
        if not check_role_access(user_role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return decoded_token
    return dependency


# Pre-defined role dependencies
require_admin = require_role(Role.ADMIN)
require_teacher = require_role(Role.TEACHER)
require_student = require_role(Role.STUDENT)